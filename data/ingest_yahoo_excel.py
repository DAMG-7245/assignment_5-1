import pandas as pd
import io
import os
import boto3
import snowflake.connector
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# --- Snowflake service (inline version) ---
class SnowflakeService:
    def __init__(self):
        self.connection = snowflake.connector.connect(
            account=os.getenv("SNOWFLAKE_ACCOUNT"),
            user=os.getenv("SNOWFLAKE_USER"),
            password=os.getenv("SNOWFLAKE_PASSWORD"),
            database=os.getenv("SNOWFLAKE_DATABASE"),
            schema=os.getenv("SNOWFLAKE_SCHEMA"),
            warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
            role=os.getenv("SNOWFLAKE_ROLE")
        )

    def execute_query(self, query: str):
        try:
            cur = self.connection.cursor()
            cur.execute(query)
            cur.close()
        except Exception as e:
            print(f"❌ Snowflake query failed: {e}")
            raise

    def __del__(self):
        if hasattr(self, 'connection'):
            self.connection.close()

# --- Helper functions ---
def normalize_trillion(value: str) -> float:
    """將 2.69T → 2.69"""
    if isinstance(value, str) and value.endswith("T"):
        return float(value[:-1])
    try:
        return float(value)
    except:
        return None

def download_file_from_s3(bucket_name: str, key: str, output_stream):
    """從 S3 將檔案以 in-memory stream 下載"""
    s3 = boto3.client("s3")
    s3.download_fileobj(bucket_name, key, output_stream)

def create_table_if_not_exists(sf: SnowflakeService):
    create_sql = """
    CREATE OR REPLACE TABLE RAW.NVIDIA_VALUATION_METRICS (
        QUARTER_LABEL VARCHAR,
        DATE DATE,
        MARKET_CAP FLOAT,
        ENTERPRISE_VALUE FLOAT,
        TRAILING_PE FLOAT,
        FORWARD_PE FLOAT,
        PEG_RATIO FLOAT,
        PRICE_TO_SALES FLOAT,
        PRICE_TO_BOOK FLOAT,
        ENTERPRISE_TO_REVENUE FLOAT,
        ENTERPRISE_TO_EBITDA FLOAT
    );
    """
    sf.execute_query(create_sql)
    print("✅ Created table RAW.NVIDIA_VALUATION_METRICS")

def ingest_excel_from_s3(sf: SnowflakeService, bucket: str, key: str):
    excel_stream = io.BytesIO()
    download_file_from_s3(bucket, key, excel_stream)
    excel_stream.seek(0)

    df = pd.read_excel(excel_stream)

    df.columns = [
        "quarter_label", "market_cap", "enterprise_value", "trailing_pe", "forward_pe",
        "peg_ratio", "price_to_sales", "price_to_book",
        "enterprise_to_revenue", "enterprise_to_ebitda"
    ]

    df["market_cap"] = df["market_cap"].apply(normalize_trillion)
    df["enterprise_value"] = df["enterprise_value"].apply(normalize_trillion)
    df["date"] = df["quarter_label"].apply(lambda q: pd.Period(q, freq="Q").end_time.date())

    for row in df.itertuples(index=False):
        sf.execute_query(f"""
            INSERT INTO RAW.NVIDIA_VALUATION_METRICS (
                QUARTER_LABEL, DATE,
                MARKET_CAP, ENTERPRISE_VALUE, TRAILING_PE, FORWARD_PE,
                PEG_RATIO, PRICE_TO_SALES, PRICE_TO_BOOK,
                ENTERPRISE_TO_REVENUE, ENTERPRISE_TO_EBITDA
            ) VALUES (
                '{row.quarter_label}', '{row.date}',
                {row.market_cap or 'NULL'}, {row.enterprise_value or 'NULL'}, {row.trailing_pe or 'NULL'}, {row.forward_pe or 'NULL'},
                {row.peg_ratio or 'NULL'}, {row.price_to_sales or 'NULL'}, {row.price_to_book or 'NULL'},
                {row.enterprise_to_revenue or 'NULL'}, {row.enterprise_to_ebitda or 'NULL'}
            )
        """)
    print(f"✅ Ingested {len(df)} rows into Snowflake.")

# --- Entry point ---
if __name__ == "__main__":
    bucket = os.getenv("S3_BUCKET_NAME")
    key = "Nvidia_ValuationMeasures.xlsx"
    sf = SnowflakeService()

    create_table_if_not_exists(sf)
    ingest_excel_from_s3(sf, bucket, key)
