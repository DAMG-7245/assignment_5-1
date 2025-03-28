import os
import io
import boto3
import pandas as pd
from typing import Dict
import logging

from core.config import settings

logger = logging.getLogger(__name__)

class S3Service:
    def __init__(self):
        """初始化S3客户端"""
        self.s3_client = boto3.client(
            "s3",
            region_name=settings.S3_REGION,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", ""),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "")
        )
        self.bucket = settings.S3_BUCKET

    def get_quarterly_report_mapping(self) -> Dict[str, str]:
        """
        从S3拉取Excel并返回 { quarter_label: PDF URL } 字典。
        如果出现错误，则抛出异常。
        """
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket, 
                Key=settings.S3_REPORTS_PATH
            )
        except Exception as e:
            logger.error(f"Failed to get object from S3: {e}")
            raise RuntimeError(f"从S3获取对象失败: {e}")

        excel_bytes = response["Body"].read()

        try:
            df = pd.read_excel(io.BytesIO(excel_bytes))
        except Exception as e:
            logger.error(f"Failed to read Excel file: {e}")
            raise RuntimeError(f"读取Excel文件失败: {e}")

        # 检查必要的列是否存在
        required_columns = {"quarter_label", "url"}
        if not required_columns.issubset(df.columns):
            missing = required_columns - set(df.columns)
            logger.error(f"Excel file missing required columns: {missing}")
            raise ValueError(f"Excel文件缺少必需的列: {missing}")

        # 构造字典，转换成字符串并去除空格
        mapping = df.set_index("quarter_label")["url"].apply(lambda x: str(x).strip()).to_dict()

        return mapping

    def get_presigned_url(self, pdf_key: str, expires_in: int = 3600) -> str:
        """
        生成一个预签名URL，用于外部服务访问S3上指定pdf_key的对象。
        
        参数：
          - pdf_key: S3对象的Key（例如 "data/nvidia_2024Q1.pdf"）
          - expires_in: URL过期时间（单位秒），默认1小时

        返回：
          - 预签名URL字符串，如果失败则返回空字符串。
        """
        try:
            url = self.s3_client.generate_presigned_url(
                ClientMethod='get_object',
                Params={'Bucket': self.bucket, 'Key': pdf_key},
                ExpiresIn=expires_in
            )
            return url
        except Exception as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            return ""
            
    def download_file(self, key: str) -> bytes:
        """
        从S3下载文件并返回字节内容
        
        参数：
          - key: S3对象的Key
          
        返回：
          - 文件的字节内容
        """
        try:
            response = self.s3_client.get_object(Bucket=self.bucket, Key=key)
            return response["Body"].read()
        except Exception as e:
            logger.error(f"Failed to download file from S3: {e}")
            raise RuntimeError(f"从S3下载文件失败: {e}")