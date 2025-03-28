import requests
import logging
import io
import PyPDF2
from typing import List

logger = logging.getLogger(__name__)

class PDFParserService:
    def __init__(self):
        """初始化PDF解析服务"""
        pass
        
    def parse_pdf_from_url(self, url: str) -> str:
        """
        使用PyPDF2从URL解析PDF
        
        参数:
            url: PDF文件的URL
            
        返回:
            解析出的文本内容
        """
        try:
            logger.info(f"开始从URL下载PDF: {url}")
            
            # 下载PDF文件
            response = requests.get(url, stream=True)
            if response.status_code != 200:
                logger.error(f"下载PDF失败: HTTP {response.status_code}")
                raise Exception(f"下载PDF失败: HTTP {response.status_code}")
            
            # 使用内存IO存储PDF内容
            pdf_content = io.BytesIO(response.content)
            
            logger.info("PDF下载成功，开始解析...")
            
            # 使用PyPDF2解析
            try:
                reader = PyPDF2.PdfReader(pdf_content)
                num_pages = len(reader.pages)
                
                logger.info(f"PDF共有{num_pages}页")
                
                # 提取所有页面的文本
                text = ""
                for i in range(num_pages):
                    try:
                        page = reader.pages[i]
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n\n"
                        logger.debug(f"成功解析第{i+1}页，提取了{len(page_text) if page_text else 0}个字符")
                    except Exception as e:
                        logger.warning(f"解析第{i+1}页时出错: {e}")
                        # 继续处理下一页
                
                if not text.strip():
                    logger.warning("PDF解析成功但未提取到文本内容，PDF可能是扫描版或有保护")
                
                logger.info(f"PDF解析成功，总共提取了{len(text)}个字符")
                return text
                
            except PyPDF2.errors.PdfReadError as e:
                logger.error(f"PyPDF2解析PDF失败: {e}")
                # 尝试备用解析方法
                return self._fallback_parse_pdf(url)
            
        except Exception as e:
            logger.error(f"从URL解析PDF失败: {e}")
            raise Exception(f"从URL解析PDF失败: {e}")
    
    def _fallback_parse_pdf(self, url: str) -> str:
        """备用PDF解析方法，当PyPDF2失败时使用"""
        try:
            logger.info("尝试使用pdfplumber作为备用解析方法")
            
            # 尝试使用pdfplumber
            try:
                import pdfplumber
                import io
                
                # 下载PDF
                response = requests.get(url)
                response.raise_for_status()
                
                # 使用pdfplumber解析
                with pdfplumber.open(io.BytesIO(response.content)) as pdf:
                    text = ""
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n\n"
                
                logger.info(f"pdfplumber解析成功，提取了{len(text)}个字符")
                return text
                
            except ImportError:
                logger.warning("pdfplumber未安装，尝试使用pdfminer")
                
                # 尝试使用pdfminer
                try:
                    from pdfminer.high_level import extract_text as pdfminer_extract_text
                    
                    # 下载PDF
                    response = requests.get(url)
                    response.raise_for_status()
                    
                    # 使用pdfminer解析
                    text = pdfminer_extract_text(io.BytesIO(response.content))
                    
                    logger.info(f"pdfminer解析成功，提取了{len(text)}个字符")
                    return text
                    
                except ImportError:
                    logger.error("无法导入任何备用PDF解析库")
                    raise Exception("无法解析PDF，所有可用的解析方法都失败了")
                    
        except Exception as e:
            logger.error(f"备用PDF解析也失败: {e}")
            raise Exception(f"无法解析PDF: {e}")
    
    def chunk_text(self, text: str, max_chunk_size: int = 1000, overlap: int = 100) -> List[str]:
        """
        将文本分割成重叠的块
        
        参数:
            text: 要分割的文本
            max_chunk_size: 每个块的最大大小
            overlap: 相邻块之间的重叠大小
            
        返回:
            分割后的文本块列表
        """
        if not text:
            return []
            
        # 先按段落分割
        paragraphs = text.split("\n\n")
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            # 如果段落本身超过最大块大小，需要进一步分割
            if len(paragraph) > max_chunk_size:
                # 先添加当前块（如果非空）
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = ""
                
                # 分割长段落
                words = paragraph.split()
                temp_chunk = ""
                
                for word in words:
                    if len(temp_chunk) + len(word) + 1 <= max_chunk_size:
                        if temp_chunk:
                            temp_chunk += " " + word
                        else:
                            temp_chunk = word
                    else:
                        chunks.append(temp_chunk)
                        # 保留部分重叠
                        overlap_words = temp_chunk.split()[-overlap:]
                        temp_chunk = " ".join(overlap_words) + " " + word
                
                if temp_chunk:
                    chunks.append(temp_chunk)
                
            # 如果当前块加上段落超过最大大小，则先添加当前块
            elif len(current_chunk) + len(paragraph) + 2 > max_chunk_size:
                if current_chunk:
                    chunks.append(current_chunk)
                    # 使用重叠
                    last_sentences = current_chunk.split(". ")[-3:]  # 取最后几个句子作为重叠
                    current_chunk = ". ".join(last_sentences) + ". " if len(last_sentences) > 1 else ""
                    current_chunk += paragraph
                else:
                    current_chunk = paragraph
            else:
                # 添加段落到当前块
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph
        
        # 添加最后一个块
        if current_chunk:
            chunks.append(current_chunk)
        
        logger.info(f"将{len(text)}个字符的文本分割成{len(chunks)}个块")
        return chunks