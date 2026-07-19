# $ python process_pdf.py s3://temporal-dev/files/Moemn_Adel_Hassan.pdf



import os
import sys
import tempfile
import logging
from pathlib import Path

import boto3
import pymupdf4llm
from dotenv import load_dotenv

load_dotenv()

AWS_ACCESS_KEY_ID = os.environ["AWS_ACCESS_KEY_ID"]
AWS_SECRET_ACCESS_KEY = os.environ["AWS_SECRET_ACCESS_KEY"]
AWS_REGION = os.environ["AWS_REGION"]
AWS_S3_ENDPOINT_URL = os.environ["AWS_S3_ENDPOINT_URL"]
S3_BUCKET = os.environ["S3_BUCKET"]
TEMP_DIR = os.environ["TEMP_DIR"]

os.makedirs(TEMP_DIR, exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)




# s3 helper
def get_s3_client():
    return boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION,
        endpoint_url=AWS_S3_ENDPOINT_URL
    )


def parse_s3_path(s3_path: str):
    #s3://temporal-dev/your-folder/your-file.pdf
    s3_path_no_schema = s3_path.replace("s3://", "")
    bucket, _ ,key = s3_path_no_schema.partition("/")
    return bucket,key

# step 1 download pdf from s3
def download_pdf(s3_path:str) ->str:
    bucket,key = parse_s3_path(s3_path)
    filename = Path(key).name
    local_path =str(Path(TEMP_DIR) / filename)

    log.info(f"Downloading : s3://{bucket}/{key} to {local_path}")

    s3_client = get_s3_client()
    s3_client.download_file(bucket, key, local_path)

    log.info(f"completed Downloaded: {local_path}")

    return local_path


# step 2 extract text from pdf
def extract_to_markdown(local_pdf_path:str)->str:
    log.info(f"Extracting text from {local_pdf_path}")
    markdown_text = pymupdf4llm.to_markdown(local_pdf_path)

    log.info(f"Completed extracting text from {local_pdf_path}")
    return markdown_text

#step 3 upload markdown to s3
def upload_markdown(markdown_text:str, original_S3_path:str)->str:
    bucket, key = parse_s3_path(original_S3_path)

    # Modify the key to have a .md extension
    md_key = key.replace(".pdf", ".md")
    log.info(f"Uploading markdown to s3://{bucket}/{md_key}")

    s3_client = get_s3_client()
    s3_client.put_object(Bucket=bucket, Key=md_key, Body=markdown_text.encode("utf-8"),ContentType="text/markdown")
    output_path = f"s3://{bucket}/{md_key}"
    log.info(f"Completed uploading markdown to s3://{bucket}/{md_key}")
    return output_path

#main function to process pdf
def process_pdf(s3_path:str)->str:
    log.info(f"Starting PDF processing for {s3_path}")

    local_pdf_path = download_pdf(s3_path)
    markdown_text = extract_to_markdown(local_pdf_path)
    output_s3_path = upload_markdown(markdown_text, s3_path)

    os.remove(local_pdf_path)  # Clean up the local PDF file after processing
    log.info(f"Completed PDF processing for {s3_path}")
    return output_s3_path


if __name__ == "__main__":
    output_s3_path = process_pdf(sys.argv[1])
    print(f"Markdown uploaded to: {output_s3_path}")