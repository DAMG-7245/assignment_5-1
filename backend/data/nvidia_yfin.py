
# #import yfinance as yf
# import boto3
# from dotenv import load_dotenv
# import os
# import pandas as pd
# from yahoo_fin import stock_info

# # # Load environment variables from .env file
# load_dotenv()

# # Retrieve AWS credentials and bucket name from environment variables
# AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
# AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
# AWS_REGION = os.getenv("AWS_REGION")
# S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

# def upload_to_s3(dataframe, s3_key):
    
#     # Convert DataFrame to CSV in memory
#     csv_data = dataframe.to_csv(index=True)

#     # Initialize S3 client with credentials from environment variables
#     s3 = boto3.client(
#         's3',
#         aws_access_key_id=AWS_ACCESS_KEY_ID,
#         aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
#         region_name=AWS_REGION
#     )

#     try:
#         # Upload directly from memory
#         s3.put_object(Bucket=S3_BUCKET_NAME, Key=s3_key, Body=csv_data)
#         #print(f"Uploaded to S3")
#     except Exception as e:
#         print(f"Upload error: {str(e)}")


# data = stock_info.get_stats_valuation("NVDA")
# transpose_data = data.T
# print(transpose_data)

# # # Save appended DataFrame to S3 bucket
# # upload_to_s3(, "Nvidia_ValuationMeasures.csv")

import pandas as pd
from io import StringIO
import boto3
import os
from yahoo_fin import stock_info
from dotenv import load_dotenv

load_dotenv()

# Fetch valuation metrics
data = stock_info.get_stats_valuation("NVDA")

# Rename the columns
data.rename(columns={
    "Unnamed: 0": "Quarter",
    "Current": "2025q2",
    "1/31/2025": "2025q1",
    "10/31/2024": "2024q4",
    "7/31/2024": "2024q3",
    "4/30/2024": "2024q2",
    "1/31/2024": "2024q1"
}, inplace=True)

data = data.reset_index(drop=True)  # Reset the index and drop the old one
data["Quarter"] = data["Quarter"].astype(str).str.replace(r'^\d+\.?\s*', '', regex=True)
print(data)


# transpose_data = data.T
# df = pd.DataFrame(transpose_data)
# df.reset_index(drop=True, inplace=True)
# df.drop(index=0, inplace=True)  # Now this removes the first row

# print(df.head())  # View the first few rows
# print(df.index)   # Check the index structure
# print(df.columns) # Check column names

#print(df)
# # Load environment variables from .env file
# load_dotenv()

# # Retrieve AWS credentials and bucket name from environment variables
# AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
# AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
# AWS_REGION = os.getenv("AWS_REGION")
# S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

# def upload_to_s3(dataframe, s3_key):
    
#     # Convert DataFrame to CSV in memory
#     csv_data = dataframe.to_csv(index=True)

#     # Initialize S3 client with credentials from environment variables
#     s3 = boto3.client(
#         's3',
#         aws_access_key_id=AWS_ACCESS_KEY_ID,
#         aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
#         region_name=AWS_REGION
#     )

#     try:
#         # Upload directly from memory
#         s3.put_object(Bucket=S3_BUCKET_NAME, Key=s3_key, Body=csv_data)
#         #print(f"Uploaded to S3")
#     except Exception as e:
#         print(f"Upload error: {str(e)}")

# upload_to_s3(df, "Nvidia_valuation.csv")