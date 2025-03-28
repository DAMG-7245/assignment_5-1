
import yfinance as yf
import boto3
from dotenv import load_dotenv
import os
import pandas as pd

# Load environment variables from .env file
load_dotenv()

# Retrieve AWS credentials and bucket name from environment variables
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

def upload_to_s3(dataframe, s3_key):
    
    # Convert DataFrame to CSV in memory
    csv_data = dataframe.to_csv(index=True)

    # Initialize S3 client with credentials from environment variables
    s3 = boto3.client(
        's3',
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION
    )

    try:
        # Upload directly from memory
        s3.put_object(Bucket=S3_BUCKET_NAME, Key=s3_key, Body=csv_data)
        #print(f"Uploaded to S3")
    except Exception as e:
        print(f"Upload error: {str(e)}")

def append_dataframes_predefined_columns(dfs, predefined_columns):
    # Align each DataFrame to predefined columns (fill missing with NaN)
    dfs = [df.reindex(columns=predefined_columns) for df in dfs]
    
    # Concatenate aligned DataFrames
    combined_df = pd.concat(dfs, axis=0)
    return combined_df


# Create a Ticker object for NVIDIA and fetch financial statements
nvda = yf.Ticker("NVDA")
income_statement = nvda.financials
balance_sheet = nvda.balance_sheet
cash_flow = nvda.cashflow

# Function to update column names for financial years
def update_column_names(df):
    new_columns = [f"FY{col.year}" for col in df.columns]
    df.columns = new_columns
    return df

income_statement = update_column_names(income_statement)
balance_sheet = update_column_names(balance_sheet)
cash_flow = update_column_names(cash_flow)

# Get all unique columns across all financial statements and sort them chronologically
all_columns = set(income_statement.columns) | set(balance_sheet.columns) | set(cash_flow.columns)
predefined_columns = sorted(all_columns, key=lambda x: int(x[2:]), reverse=True)  # Sorts as FY2023, FY2022, FY2021...

# Append using predefined column order
all_financials = append_dataframes_predefined_columns(
    [income_statement, balance_sheet, cash_flow],
    predefined_columns
)

# Save appended DataFrame to S3 bucket
upload_to_s3(all_financials, "NVDA_financials.csv")