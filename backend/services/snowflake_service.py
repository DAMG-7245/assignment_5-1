import pandas as pd
import snowflake.connector
from typing import List, Dict, Any, Optional
import logging
import matplotlib.pyplot as plt
import io
import base64
from backend.services.yahoo_finance_service import get_nvda_valuation_row


from backend.core.models import TimeRange, NvidiaValuationMetric
from backend.core.config import settings


logger = logging.getLogger(__name__)

class SnowflakeService:
    def __init__(self):
        """Initialize the Snowflake connection"""
        self.connection = snowflake.connector.connect(
            account=settings.SNOWFLAKE_ACCOUNT,
            user=settings.SNOWFLAKE_USER,
            password=settings.SNOWFLAKE_PASSWORD,
            database=settings.SNOWFLAKE_DATABASE,
            schema=settings.SNOWFLAKE_SCHEMA,
            warehouse=settings.SNOWFLAKE_WAREHOUSE,
            role=settings.SNOWFLAKE_ROLE
        )
        
    def __del__(self):
        """Close connection when the object is destroyed"""
        if hasattr(self, 'connection'):
            self.connection.close()
        """
    def execute_query(self, query: str) -> pd.DataFrame:
    "Execute SQL query and return results as pandas DataFrame"
        try:
            cur = self.connection.cursor()
            cur.execute(query)
            result = cur.fetch_pandas_all()
            cur.close()
            return result
        except Exception as e:
            logger.error(f"Error executing Snowflake query: {e}")
            raise
        """
    def execute_query(self, query: str) -> pd.DataFrame:
        """執行 SQL 並用 fetchall 回傳 pandas DataFrame（不依賴 fetch_pandas_all）"""
        try:
            cur = self.connection.cursor()
            cur.execute(query)

            columns = [col[0] for col in cur.description]
            rows = cur.fetchall()
            cur.close()

            return pd.DataFrame(rows, columns=columns)

        except Exception as e:
            logger.error(f"Error executing Snowflake query: {e}")
            raise

    def get_valuation_metrics(self, time_range: TimeRange) -> List[NvidiaValuationMetric]:
        """Get NVIDIA valuation metrics for the specified time range"""
        start_year, start_q = self._parse_quarter_label(time_range.start_quarter)
        end_year, end_q = self._parse_quarter_label(time_range.end_quarter)
        
        query = f"""
        SELECT 
            YEAR, 
            QUARTER, 
            QUARTER_LABEL,
            MARKET_CAP, 
            ENTERPRISE_VALUE, 
            TRAILING_PE, 
            FORWARD_PE, 
            PRICE_TO_SALES, 
            PRICE_TO_BOOK, 
            ENTERPRISE_TO_REVENUE, 
            ENTERPRISE_TO_EBITDA
        FROM NVIDIA_VALUATION_METRICS
        WHERE (YEAR > {start_year} OR (YEAR = {start_year} AND QUARTER >= {start_q}))
            AND (YEAR < {end_year} OR (YEAR = {end_year} AND QUARTER <= {end_q}))
        ORDER BY YEAR, QUARTER
        """
        
        df = self.execute_query(query)
        
        if df.empty:
            return []
            
        # Convert DataFrame to list of NvidiaValuationMetric objects
        return [
            NvidiaValuationMetric(
                year=row.YEAR,
                quarter=row.QUARTER,
                quarter_label=row.QUARTER_LABEL,
                market_cap=row.MARKET_CAP,
                enterprise_value=row.ENTERPRISE_VALUE,
                trailing_pe=row.TRAILING_PE,
                forward_pe=row.FORWARD_PE,
                price_to_sales=row.PRICE_TO_SALES,
                price_to_book=row.PRICE_TO_BOOK,
                enterprise_to_revenue=row.ENTERPRISE_TO_REVENUE,
                enterprise_to_ebitda=row.ENTERPRISE_TO_EBITDA
            )
            for _, row in df.iterrows()
        ]
    
    def generate_metrics_charts(self, time_range: TimeRange) -> Dict[str, str]:
        """Generate charts for NVIDIA valuation metrics"""
        metrics_data = self.get_valuation_metrics(time_range)
        
        if not metrics_data:
            return {}
            
        # Convert to DataFrame for easier plotting
        df = pd.DataFrame([metric.dict() for metric in metrics_data])
        
        charts = {}
        
        # Chart 1: Market Cap and Enterprise Value
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.bar(df['quarter_label'], df['market_cap'] / 1e9, width=0.4, align='edge', label='Market Cap')
        ax.bar(df['quarter_label'], df['enterprise_value'] / 1e9, width=-0.4, align='edge', label='Enterprise Value')
        ax.set_title('NVIDIA Market Cap vs Enterprise Value')
        ax.set_xlabel('Quarter')
        ax.set_ylabel('Value (Billions USD)')
        ax.legend()
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # Convert to base64 string
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        charts['market_valuation'] = base64.b64encode(buffer.read()).decode('utf-8')
        plt.close()
        
        # Chart 2: P/E Ratios
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(df['quarter_label'], df['trailing_pe'], marker='o', label='Trailing P/E')
        ax.plot(df['quarter_label'], df['forward_pe'], marker='s', label='Forward P/E')
        ax.set_title('NVIDIA P/E Ratios')
        ax.set_xlabel('Quarter')
        ax.set_ylabel('P/E Ratio')
        ax.legend()
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # Convert to base64 string
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        charts['pe_ratios'] = base64.b64encode(buffer.read()).decode('utf-8')
        plt.close()
        
        # Chart 3: Price to Sales and Price to Book
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(df['quarter_label'], df['price_to_sales'], marker='o', label='Price to Sales')
        ax.plot(df['quarter_label'], df['price_to_book'], marker='s', label='Price to Book')
        ax.set_title('NVIDIA Price Ratios')
        ax.set_xlabel('Quarter')
        ax.set_ylabel('Ratio')
        ax.legend()
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # Convert to base64 string
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        charts['price_ratios'] = base64.b64encode(buffer.read()).decode('utf-8')
        plt.close()
        
        return charts
    
    def _parse_quarter_label(self, quarter_label: str) -> tuple:
        """Parse quarter label in format YYYYqQ to year and quarter number"""
        parts = quarter_label.lower().split('q')
        return int(parts[0]), int(parts[1])
        def insert_valuation_metric(self, data: dict):
            """將單筆 NVIDIA 估值資料寫入 Snowflake"""
        query = f"""
        INSERT INTO RAW.NVIDIA_VALUATION_METRICS (
            YEAR, QUARTER, QUARTER_LABEL, DATE,
            MARKET_CAP, ENTERPRISE_VALUE, TRAILING_PE, FORWARD_PE,
            PEG_RATIO, PRICE_TO_SALES, PRICE_TO_BOOK,
            ENTERPRISE_TO_REVENUE, ENTERPRISE_TO_EBITDA
        ) VALUES (
            {data.get('year')}, 
            {data.get('quarter')}, 
            '{data.get('quarter_label')}', 
            '{data.get('date')}',
            {data.get('market_cap') or 'NULL'}, 
            {data.get('enterprise_value') or 'NULL'}, 
            {data.get('trailing_pe') or 'NULL'}, 
            {data.get('forward_pe') or 'NULL'},
            {data.get('peg_ratio') or 'NULL'}, 
            {data.get('price_to_sales') or 'NULL'}, 
            {data.get('price_to_book') or 'NULL'},
            {data.get('enterprise_to_revenue') or 'NULL'}, 
            {data.get('enterprise_to_ebitda') or 'NULL'}
        )
        """
        self.execute_query(query)



data = get_nvda_valuation_row()
df = pd.DataFrame([data])

service = SnowflakeService()
for row in df.itertuples(index=False):
    service.execute_query(
        f"""
        INSERT INTO RAW.NVIDIA_VALUATION_METRICS (
            YEAR, QUARTER, QUARTER_LABEL, DATE,
            MARKET_CAP, ENTERPRISE_VALUE, TRAILING_PE, FORWARD_PE,
            PEG_RATIO, PRICE_TO_SALES, PRICE_TO_BOOK,
            ENTERPRISE_TO_REVENUE, ENTERPRISE_TO_EBITDA
        )
        VALUES (
            {row.year}, {row.quarter}, '{row.quarter_label}', '{row.date}',
            {row.market_cap or 'NULL'}, {row.enterprise_value or 'NULL'}, {row.trailing_pe or 'NULL'}, {row.forward_pe or 'NULL'},
            {row.peg_ratio or 'NULL'}, {row.price_to_sales or 'NULL'}, {row.price_to_book or 'NULL'},
            {row.enterprise_to_revenue or 'NULL'}, {row.enterprise_to_ebitda or 'NULL'}
        )
        """
    )
