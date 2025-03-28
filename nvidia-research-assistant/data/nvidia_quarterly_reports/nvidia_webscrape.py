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
from io import BytesIO
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


def extract_10k_and_10q_links():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument(
        'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    )

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    url = "https://investor.nvidia.com/financial-info/quarterly-results/default.aspx"
    driver.get(url)

    all_links = []

    try:
        wait = WebDriverWait(driver, 20)
        wait.until(lambda d: d.execute_script("return document.readyState") == "complete")

        year_dropdown_id = "_ctrl0_ctl75_selectEvergreenFinancialAccordionYear"
        year_dropdown = wait.until(EC.presence_of_element_located((By.ID, year_dropdown_id)))
        select = Select(year_dropdown)

        years = [option.text for option in select.options if option.text.isdigit() and 2021 <= int(option.text) <= 2025]

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

    except Exception:
        pass

    finally:
        driver.quit()

    return all_links


def upload_to_s3(data):
    s3_key_name = "nvidia_reports.xlsx"

    try:
        # Create an Excel file in memory using BytesIO
        df = pd.DataFrame(data, columns=["Year_Quarter", "Link"])
        excel_buffer = BytesIO()

        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)

        excel_buffer.seek(0)  # Reset buffer position

        # Upload directly to S3 from memory
        s3 = boto3.client(
            's3',
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION,
        )

        s3.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=s3_key_name,
            Body=excel_buffer.read(),
            ContentType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )

        return True

    except NoCredentialsError:
        pass
    except Exception:
        pass

    return False


if __name__ == "__main__":
    links_data = extract_10k_and_10q_links()

    if links_data:
        upload_to_s3(links_data)
