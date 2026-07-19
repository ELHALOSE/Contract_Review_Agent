import os
import math
import tempfile
from dataclasses import dataclass
import boto3
import fitz
import pymupdf4llm
from dotenv import load_dotenv
from temporalio import activity
from openai import OpenAI 
from pathlib import Path


load_dotenv()



# ── Dataclasses ───────────────────────────────────────────────────────────────

@dataclass
class ExtractPDFInput:
    s3_path: str
    batch_size: int = 2

@dataclass
class ExtractPDFOutput:
    s3_path: str
    markdown_text: str
    page_count: int

@dataclass
class CallLLMInput:
    prompt: str

@dataclass
class CallLLMOutput:
    content: str


# ── S3 helper ────────────────────────────────────────────────────────────────

def get_s3_client():
    return boto3.client(
        "s3",
        aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
        region_name=os.environ["AWS_REGION"],
        endpoint_url=os.environ["AWS_S3_ENDPOINT_URL"],
    )

def parse_s3_path(s3_path: str):
    s3_path_no_scheme = s3_path.replace("s3://", "")
    bucket, _, key =  s3_path_no_scheme.partition("/")
    return bucket, key




#activity 1 extract pdf from s3
@activity.defn
async def extract_pdf(params:ExtractPDFInput)->ExtractPDFOutput:
    activity.logger.info(f"starting extract pdf from {params.s3_path}")
    
    activity.heartbeat({
        "stage":"downloading",
        "s3_path":params.s3_path,
        "page_done":0,
        "chars_extracted":0
    })
    
    client = get_s3_client()
    bucket,key = parse_s3_path(params.s3_path)
    filename = Path(key).name

    temp_dir = Path(os.environ["TEMP_DIR"])

    print("TEMP_DIR =", temp_dir)
    print("Exists =", temp_dir.exists())
    print("Writable =", os.access(temp_dir, os.W_OK))
    print("Owner UID =", os.stat(temp_dir).st_uid)
    print("Current UID =", os.getuid())

    local_path = temp_dir / filename
    print("LOCAL_PATH =", local_path)


    client.download_file(
        Bucket=bucket,
        Key=key,
        Filename=str(local_path)
    )

    doc = fitz.open(local_path)

    total_pages = doc.page_count
    activity.logger.info(f"Download {total_pages}-page pdf :{params.s3_path}")

    all_text_chunks =[]
    total_char_num = 0
    num_batchs = math.ceil(total_pages / params.batch_size)
    for i in range(num_batchs):

        start_page = i * params.batch_size
        end_page = min(start_page + params.batch_size, total_pages)

        batch_md = pymupdf4llm.to_markdown(
            local_path,
            pages = list(range(start_page, end_page))
            )

        all_text_chunks.append(batch_md)
        total_char_num += len(batch_md)

        activity.heartbeat({
            "stage":"extracting",
            "s3_path":params.s3_path,
            "page_done":end_page,
            "total_pages":total_pages,
            "chars_extracted":total_char_num
        })
    full_md = "\n\n".join(all_text_chunks)

    return ExtractPDFOutput(
        s3_path=params.s3_path,
        markdown_text=full_md,
        page_count=total_pages
    )

# activity 2 call the llm from OpenAI
@activity.defn
async def call_llm(params: CallLLMInput) -> CallLLMOutput:
    activity.logger.info("starting call llm")

    llm = OpenAI(
        api_key=os.environ["GROQ_API_KEY"],
        base_url="https://api.groq.com/openai/v1",
    )

    try:
        response = llm.chat.completions.create(
            model=os.environ["GROQ_MODEL"], 
            messages=[{"role": "user", "content": params.prompt}],
            max_tokens=1000
        )

        content = response.choices[0].message.content
        activity.logger.info(f"Completed call llm. LLM returned {len(content)} chars.")
        
        return CallLLMOutput(content=content)
        
    except Exception as e:
        activity.logger.error(f"Error calling OpenAI: {str(e)}")
        raise e 