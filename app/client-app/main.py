# curl -X POST http://localhost:5000/process-pdf/execute \
#   -H "Content-Type: application/json" \
#   -d '{"s3_path": "s3://temporal-dev/files/Moemn-Adel-Hassan.pdf"}'


# curl -X POST http://localhost:5000/process-pdf/start \
#   -H "Content-Type: application/json" \
#   -d '{"s3_path": "s3://temporal-dev/files/Moemn_Adel_Hassan.pdf"}'

'''
curl -X POST http://localhost:5000/contract-review/start \
  -H "Content-Type: application/json" \
  -d '{
    "s3_paths": [
      "s3://temporal-dev/legal-docs/vendor-service-agreement.pdf",
      "s3://temporal-dev/legal-docs/nda-innovate-consultpro.pdf",
      "s3://temporal-dev/legal-docs/software-license-globalsoft.pdf"
    ]
  }'
'''


import os
import uuid

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from dotenv import load_dotenv
from temporalio.client import Client
from temporalio.client import WorkflowExecutionStatus as WES

load_dotenv()


TEMPORAL_HOST      = os.environ["TEMPORAL_HOST"]
TEMPORAL_NAMESPACE = os.environ["TEMPORAL_NAMESPACE"]
TEMPORAL_PDF_PROCESS_TASK_QUEUE = os.environ["TEMPORAL_PDF_PROCESS_TASK_QUEUE"]
TEMPORAL_TASK_QUEUE = os.environ["TEMPORAL_TASK_QUEUE"]


app = FastAPI(
    title="PDF Extraction APP",
    description="API for extracting PDFs to Markdown",
    version="1.0.0",
)

class ProcessPDFRequest(BaseModel):
    s3_path: str

class ProcessPDFExecuteResponse(BaseModel):
    workflow_id: str
    result: dict

class ProcessPDFStartResponse(BaseModel):
    workflow_id: str

class StartReviewRequest(BaseModel):
    s3_path: list[str]
    max_revisions: int = 2



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


@app.post("/process_pdf/execute",response_model=ProcessPDFExecuteResponse)
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
    return ProcessPDFExecuteResponse(workflow_id=workflow_id, result=results)



@app.post("/process_pdf/start",response_model=ProcessPDFStartResponse)
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
    return ProcessPDFStartResponse(workflow_id=workflow_id)


@app.get("/workflow/status/{workflow_id}")
async def get_workflow_status(workflow_id: str):
    client = await get_temporal_client()

    handle = client.get_workflow_handle(workflow_id,result_type=dict)

    desc = await handle.describe()

    try:
        result = await handle.result()
    except:
        result = None

    workflow_status = desc.status

    return {
        "workflow_id": workflow_id,
        "workflow_status": workflow_status.name,
        "workflow_result": result
    }

@app.post("/contract-review/start")
async def start_contract_review(request:StartReviewRequest):
    #define Id
    workflow_id = f"contract-review-{uuid.uuid4()}"
    #connect to temporal
    client = await get_temporal_client()

    await client.start_workflow(
        "ContractReviewWorkflow",
        args=[{
            "s3_paths": request.s3_path,
            "max_revisions": request.max_revisions
        }],
        id=workflow_id,
        task_queue=TEMPORAL_TASK_QUEUE,
    )
    return {"workflow_id": workflow_id}