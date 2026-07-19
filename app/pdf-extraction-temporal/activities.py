
import os
import logging
from pathlib import Path
from dataclasses import dataclass
from helpers import Download_input, Download_output, Extract_input, Extract_output, UploadInput, UploadOutput
import boto3
import pymupdf4llm
from dotenv import load_dotenv
from temporalio import activity

from helpers import (TEMP_DIR,get_s3_client, parse_s3_path,
                     Download_input, Download_output,
                     Extract_input, Extract_output,
                     UploadInput, UploadOutput)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

load_dotenv()

# step 1 download pdf from s3
@activity.defn
async def download_pdf(params: Download_input) -> Download_output:
    bucket,key =  parse_s3_path(params.s3_path)
    filename = Path(key).name
    local_path =str(Path(TEMP_DIR) / filename)

    activity.logger.info(f"Downloading : s3://{bucket}/{key} to {local_path}")

    s3_client = get_s3_client()
    s3_client.download_file(bucket, key, local_path)

    activity.logger.info(f"completed Downloaded: {local_path}")

    return Download_output(local_path=local_path)

@activity.defn
# step 2 extract text from pdf
async def extract_to_markdown(params: Extract_input) -> Extract_output:
    local_pdf_path = params.local_pdf_path
    activity.logger.info(f"Extracting text from {local_pdf_path}")
    markdown_text = pymupdf4llm.to_markdown(local_pdf_path)

    activity.logger.info(f"Completed extracting text from {local_pdf_path}")
    return Extract_output(markdown_text=markdown_text)


#step 3 upload markdown to s3
@activity.defn
async def upload_markdown(params: UploadInput) -> UploadOutput:
    markdown_text = params.markdown_text
    original_S3_path = params.original_S3_path
    bucket, key = parse_s3_path(original_S3_path)

    # Modify the key to have a .md extension
    md_key = key.replace(".pdf", ".md")
    activity.logger.info(f"Uploading markdown to s3://{bucket}/{md_key}")

    s3_client = get_s3_client()
    s3_client.put_object(Bucket=bucket, Key=md_key, Body=markdown_text.encode("utf-8"),ContentType="text/markdown")
    output_path = f"s3://{bucket}/{md_key}"
    activity.logger.info(f"Completed uploading markdown to s3://{bucket}/{md_key}")
    return UploadOutput(output_path=output_path)
