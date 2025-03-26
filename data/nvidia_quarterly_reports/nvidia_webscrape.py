from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import os
import boto3
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
from botocore.exceptions import NoCredentialsError
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Retrieve environment variables
S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME')
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')  # Default to us-east-1 if not provided

# Function for extracting links and saving them locally as an Excel file
def extract_10k_and_10q_links_to_file():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    url = "https://investor.nvidia.com/financial-info/quarterly-results/default.aspx"
    driver.get(url)
    
    try:
        wait = WebDriverWait(driver, 20)
        wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
        
        year_dropdown_id = "_ctrl0_ctl75_selectEvergreenFinancialAccordionYear"
        year_dropdown = wait.until(EC.presence_of_element_located((By.ID, year_dropdown_id)))
        select = Select(year_dropdown)
        
        years = [option.text for option in select.options if option.text.isdigit() and 2021 <= int(option.text) <= 2025]
        
        all_links = []
        
        for year in years:
            select.select_by_visible_text(year)
            time.sleep(1.5)
            
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            spans = soup.find_all('span', class_='evergreen-link-text evergreen-financial-accordion-link-text')
            for span in spans:
                span_text = span.text.strip()
                if span_text in ["10-K", "10-Q"]:
                    parent = span.find_parent('a')
                    if parent:
                        href = parent['href']
                        if href.startswith(f"https://s201.q4cdn.com/141608511/files/doc_financials/"):
                            quarter_match = href.split('/')[-2]
                            year_quarter_full = f"{year.lower()}{quarter_match.lower()}"
                            year_quarter_trimmed = year_quarter_full[:6]
                            all_links.append([year_quarter_trimmed, href])
        
        # Save links locally as an Excel file
        df = pd.DataFrame(all_links, columns=["Year_Quarter", "Link"])
        local_file_path = "/tmp/nvidia_reports.xlsx"
        df.to_excel(local_file_path, index=False)
        print(f"Links saved locally at {local_file_path}")
    
    except Exception as e:
        print(f"An error occurred: {e}")
    
    finally:
        driver.quit()

# Function for uploading the Excel file to S3
def upload_to_s3():
    local_file_path = "/tmp/nvidia_reports.xlsx"
    s3_key_name = "nvidia_reports.xlsx"
    
    s3 = boto3.client(
        's3',
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION,
    )
    try:
        with open(local_file_path, 'rb') as file_data:
            s3.put_object(Bucket=S3_BUCKET_NAME, Key=s3_key_name, Body=file_data)
        print(f"Excel file uploaded to S3 bucket {S3_BUCKET_NAME} as {s3_key_name}")
    except NoCredentialsError:
        print("Credentials not available.")

# Default arguments for the Airflow DAG
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Define the Airflow DAG
with DAG(
    dag_id='nvidia_10k_10q_extraction_and_upload',
    default_args=default_args,
    description='Extract NVIDIA 10-K and 10-Q links and upload them to S3',
    schedule_interval=timedelta(days=7),
    start_date=datetime(2025, 3, 1),
    catchup=False,
) as dag:

    # Task 1: Extract links and save them locally
    extract_task = PythonOperator(
        task_id='extract_links',
        python_callable=extract_10k_and_10q_links_to_file,
    )

    # Task 2: Upload saved Excel file to S3
    upload_task = PythonOperator(
        task_id='upload_to_s3',
        python_callable=upload_to_s3,
    )

    # Set task dependencies: extract_task must complete before upload_task starts
    extract_task >> upload_task
