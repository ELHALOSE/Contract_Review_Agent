# curl -X POST http://localhost:5000/process-pdf/execute \
#   -H "Content-Type: application/json" \
#   -d '{"s3_path": "s3://temporal-dev/files/Moemn-Adel-Hassan.pdf"}'




import os
import uuid

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from dotenv import load_dotenv
from temporalio.client import Client

load_dotenv()


TEMPORAL_HOST      = os.environ["TEMPORAL_HOST"]
TEMPORAL_NAMESPACE = os.environ["TEMPORAL_NAMESPACE"]
TEMPORAL_PDF_PROCESS_TASK_QUEUE = os.environ["TEMPORAL_PDF_PROCESS_TASK_QUEUE"]
# TEMPORAL_CONTRACT_REVIEW_TASK_QUEUE = os.environ["TEMPORAL_CONTRACT_REVIEW_TASK_QUEUE"]


app = FastAPI(
    title="PDF Extraction APP",
    description="API for extracting PDFs to Markdown",
    version="1.0.0",
)

class ProcessPDFRequest(BaseModel):
    s3_path: str

class ProcessPDFResponse(BaseModel):
    workflow_id: str
    result: dict


# Temporal Client
async def get_temporal_client():
    return await Client.connect(
        TEMPORAL_HOST,
        namespace=TEMPORAL_NAMESPACE
    )

# Routes
@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/process_pdf",response_model=ProcessPDFResponse)
async def process_pdf(request:ProcessPDFRequest):
    #define Id
    workflow_id = f"pdf-pipline-{uuid.uuid4()}"
    #connect to temporal
    client = await get_temporal_client()
    #start workflow
    results = await client.execute_workflow(
        "PDFPipelineWorkflow",
        args=[
            {
                "s3_path": request.s3_path,
            }
        ],
        id = workflow_id,
        task_queue=TEMPORAL_PDF_PROCESS_TASK_QUEUE,
        result_type=dict,
    )
    #return results
    return ProcessPDFResponse(workflow_id=workflow_id, result=results)



@app.post("/process_pdf/start",response_model=ProcessPDFResponse)
async def process_pdf(request:ProcessPDFRequest):
    #define Id
    workflow_id = f"pdf-pipline-{uuid.uuid4()}"
    #connect to temporal
    client = await get_temporal_client()
    #start workflow
    results = await client.execute_workflow(
        "PDFPipelineWorkflow",
        args=[
            {
                "s3_path": request.s3_path,
            }
        ],
        id = workflow_id,
        task_queue=TEMPORAL_PDF_PROCESS_TASK_QUEUE,
        result_type=dict,
    )
    #return results
    return ProcessPDFResponse(workflow_id=workflow_id, result=None)
