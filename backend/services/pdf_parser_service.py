import os
import json
import base64
import requests
import logging
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class PDFParserService:
    """PDF解析服务，支持使用Jina API解析PDF"""
    
    def __init__(self):
        """初始化PDF解析服务"""
        self.jina_auth_token = os.getenv("JINA_AUTH_TOKEN", "")
        if not self.jina_auth_token:
            logger.warning("JINA_AUTH_TOKEN 环境变量未设置，Jina PDF解析功能将不可用")
    
    def parse_pdf_from_url(self, pdf_url: str) -> str:
        """
        从URL解析PDF文档
        
        参数：
          - pdf_url: PDF文档的URL
          
        返回：
          - 解析出的文本内容
        """
        try:
            # 使用requests下载PDF
            response = requests.get(pdf_url, timeout=30)
            response.raise_for_status()
            pdf_bytes = response.content
            
            # 使用Jina解析PDF
            return self.parse_pdf_bytes(pdf_bytes)
        except Exception as e:
            logger.error(f"从URL解析PDF失败: {e}")
            raise RuntimeError(f"从URL解析PDF失败: {e}")
    
    def parse_pdf_bytes(self, pdf_bytes: bytes) -> str:
        """
        解析PDF字节内容
        
        参数：
          - pdf_bytes: PDF文档的字节内容
          
        返回：
          - 解析出的文本内容
        """
        if not self.jina_auth_token:
            raise ValueError("JINA_AUTH_TOKEN未设置，无法使用Jina解析PDF")
        
        try:
            # 将PDF编码为base64
            encoded_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
            
            # 调用Jina API
            url = 'https://r.jina.ai/'
            headers = {
                'Authorization': f'Bearer {self.jina_auth_token}',
                'X-Return-Format': 'markdown',  # 使用Markdown格式
                'Content-Type': 'application/json'
            }
            data = {
                'url': 'https://example.com',  # 这个URL不重要，只是一个占位符
                'pdf': encoded_pdf
            }
            
            logger.info("正在调用Jina API解析PDF...")
            resp = requests.post(url, headers=headers, json=data, timeout=60)
            resp.raise_for_status()
            
            logger.info("Jina API解析PDF成功")
            return resp.text
        except Exception as e:
            logger.error(f"Jina解析PDF失败: {e}")
            raise RuntimeError(f"Jina解析PDF失败: {e}")
    
    def chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 100) -> list:
        """
        将文本分割成块
        
        参数：
          - text: 要分割的文本
          - chunk_size: 每个块的最大字符数
          - overlap: 块之间的重叠字符数
          
        返回：
          - 文本块列表
        """
        if not text:
            return []
        
        chunks = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            # 计算当前块的结束位置
            end = min(start + chunk_size, text_length)
            
            # 如果不是最后一个块且没有到达文本末尾，尝试在句子或段落边界处分割
            if end < text_length:
                # 尝试在段落分隔符处分割
                paragraph_end = text.rfind("\n\n", start, end)
                if paragraph_end != -1 and paragraph_end > start + chunk_size / 2:
                    end = paragraph_end + 2  # 包含换行符
                else:
                    # 尝试在句子分隔符处分割
                    sentence_end = text.rfind(". ", start, end)
                    if sentence_end != -1 and sentence_end > start + chunk_size / 2:
                        end = sentence_end + 2  # 包含句号和空格
            
            # 添加当前块
            chunks.append(text[start:end])
            
            # 更新起始位置，考虑重叠
            start = max(start, end - overlap)
        
        return chunks