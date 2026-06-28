from dataclasses import dataclass
from dotenv import load_dotenv
import boto3
import os

load_dotenv()


AWS_ACCESS_KEY_ID = os.environ["AWS_ACCESS_KEY_ID"]
AWS_SECRET_ACCESS_KEY = os.environ["AWS_SECRET_ACCESS_KEY"]
AWS_REGION = os.environ["AWS_REGION"]
AWS_S3_ENDPOINT_URL = os.environ["AWS_S3_ENDPOINT_URL"]
S3_BUCKET = os.environ["S3_BUCKET"]
TEMP_DIR = os.environ["TEMP_DIR"]

os.makedirs(TEMP_DIR, exist_ok=True)





#Input and Output data classes
@dataclass
class Download_input:
    s3_path: str

@dataclass
class Download_output:
    local_path: str

@dataclass
class Extract_input:
    local_pdf_path: str

@dataclass
class Extract_output:
    markdown_text: str

@dataclass
class UploadInput:
    markdown_text: str
    original_S3_path: str

@dataclass
class UploadOutput:
    output_path: str



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
