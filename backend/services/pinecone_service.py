import pandas as pd
import io
import tempfile
import os
import logging
from typing import List, Dict, Any, Optional
from pinecone import Pinecone, ServerlessSpec
# 改用HuggingFace嵌入代替VertexAI嵌入，更容易设置
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter

from core.config import settings
from core.models import TimeRange, PineconeMetadata
from services.s3_service import S3Service
from services.pdf_parser_service import PDFParserService

logger = logging.getLogger(__name__)

class PineconeService:
    def __init__(self):
        """初始化Pinecone客户端和嵌入模型"""
        # 初始化Pinecone
        self.pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        
        # 使用HuggingFace嵌入模型替代VertexAI嵌入
        # 'sentence-transformers/all-MiniLM-L6-v2'是一个小型但效果好的多语言模型
        self.embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        
        # 初始化S3服务
        self.s3_service = S3Service()
        
        # 初始化PDF解析服务
        self.pdf_parser = PDFParserService()
        
        # 连接到索引（如果不存在则创建）
        self._connect_to_index()
        
    def _connect_to_index(self):
        """连接到Pinecone索引或者创建（如果不存在）"""
        try:
            # 检查索引是否存在
            existing_indexes = self.pc.list_indexes()
            existing_index_names = [idx.name for idx in existing_indexes.indexes] if hasattr(existing_indexes, 'indexes') else []
            
            if settings.PINECONE_INDEX_NAME not in existing_index_names:
                # 创建索引并启用元数据过滤
                self.pc.create_index(
                    name=settings.PINECONE_INDEX_NAME,
                    dimension=384,  # all-MiniLM-L6-v2模型的维度是384
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud="aws",
                        region=settings.PINECONE_ENVIRONMENT
                    )
                )
            
            # 连接到索引
            self.index = self.pc.Index(settings.PINECONE_INDEX_NAME)
            logger.info(f"成功连接到Pinecone索引: {settings.PINECONE_INDEX_NAME}")
        except Exception as e:
            logger.error(f"连接到Pinecone索引时出错: {e}")
            raise
    
    def load_and_index_reports(self):
        """从S3加载NVIDIA报告并索引到Pinecone"""
        try:
            # 获取报告映射
            report_mapping = self.s3_service.get_quarterly_report_mapping()
            
            # 初始化批量上传的向量列表
            all_vectors = []
            
            # 处理每个报告
            for quarter_label, url in report_mapping.items():
                logger.info(f"正在处理 {quarter_label} 的报告")
                year, quarter = self._parse_quarter_label(quarter_label)
                
                try:
                    # 使用Jina解析PDF
                    pdf_text = self.pdf_parser.parse_pdf_from_url(url)
                    
                    # 分割文本
                    text_splitter = RecursiveCharacterTextSplitter(
                        chunk_size=1000,
                        chunk_overlap=100
                    )
                    
                    # 先按段落分割
                    text_chunks = self.pdf_parser.chunk_text(pdf_text)
                    
                    # 为每个分块创建元数据
                    documents = []
                    for i, chunk in enumerate(text_chunks):
                        metadata = {
                            "year": year,
                            "quarter": quarter,
                            "quarter_label": quarter_label,
                            "source": url,
                            "page": i,  # 使用块索引作为"页码"
                            "text": chunk  # 在元数据中存储文本，以便检索
                        }
                        # 创建包含内容和元数据的文档
                        documents.append({
                            "page_content": chunk,
                            "metadata": metadata
                        })
                    
                    # 获取嵌入
                    chunk_texts = [doc["page_content"] for doc in documents]
                    embeddings = self.embeddings.embed_documents(chunk_texts)
                    
                    # 准备向量上传
                    for i, (doc, embedding) in enumerate(zip(documents, embeddings)):
                        vector = {
                            "id": f"{quarter_label}_{i}",
                            "values": embedding,
                            "metadata": doc["metadata"]
                        }
                        all_vectors.append(vector)
                        
                        # 批量上传，每100个向量一批
                        if len(all_vectors) >= 100:
                            self.index.upsert(vectors=all_vectors)
                            all_vectors = []
                            logger.info(f"已上传100个向量")
                
                except Exception as e:
                    logger.error(f"处理 {quarter_label} 报告时出错: {e}")
                    continue
            
            # 上传剩余的向量
            if all_vectors:
                self.index.upsert(vectors=all_vectors)
                logger.info(f"已上传剩余的 {len(all_vectors)} 个向量")
                
            logger.info(f"成功索引 {len(report_mapping)} 份NVIDIA报告")
            
        except Exception as e:
            logger.error(f"索引NVIDIA报告时出错: {e}")
            raise
    
    def hybrid_search(self, query: str, time_range: Optional[TimeRange] = None, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        执行基于时间范围元数据过滤的混合搜索
        
        参数:
            query: 搜索查询
            time_range: 可选的时间范围过滤
            top_k: 返回结果数量
            
        返回:
            包含内容和元数据的搜索结果列表
        """
        # 生成查询的嵌入
        query_embedding = self.embeddings.embed_query(query)
        
        # 如果提供了时间范围，设置元数据过滤
        filter_dict = None
        if time_range:
            start_year, start_q = self._parse_quarter_label(time_range.start_quarter)
            end_year, end_q = self._parse_quarter_label(time_range.end_quarter)
            
            # 构建过滤器
            filter_dict = self._construct_time_filter(start_year, start_q, end_year, end_q)
        
        # 执行搜索
        results = self.index.query(
            vector=query_embedding,
            filter=filter_dict,
            top_k=top_k,
            include_metadata=True
        )
        
        # 格式化结果
        formatted_results = []
        for match in results.get('matches', []):
            # 尝试获取文本内容，可能来自不同字段
            content = ""
            metadata = match.get("metadata", {})
            if "text" in metadata:
                content = metadata["text"]
            
            formatted_results.append({
                "content": content,
                "score": match.get("score", 0),
                "metadata": metadata
            })
            
        return formatted_results
    
    def _construct_time_filter(self, start_year: int, start_q: int, end_year: int, end_q: int) -> Dict[str, Any]:
        """
        构建时间范围的元数据过滤器
        
        过滤器应该包括季度：
        (year > start_year OR (year = start_year AND quarter >= start_q))
        AND (year < end_year OR (year = end_year AND quarter <= end_q))
        """
        return {
            "$and": [
                {
                    "$or": [
                        {"year": {"$gt": start_year}},
                        {
                            "$and": [
                                {"year": start_year},
                                {"quarter": {"$gte": start_q}}
                            ]
                        }
                    ]
                },
                {
                    "$or": [
                        {"year": {"$lt": end_year}},
                        {
                            "$and": [
                                {"year": end_year},
                                {"quarter": {"$lte": end_q}}
                            ]
                        }
                    ]
                }
            ]
        }
    
    def _parse_quarter_label(self, quarter_label: str) -> tuple:
        """解析格式为YYYYqQ的季度标签为年份和季度编号"""
        parts = quarter_label.lower().split('q')
        return int(parts[0]), int(parts[1])