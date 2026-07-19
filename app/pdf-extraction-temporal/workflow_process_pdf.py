from dataclasses import dataclass
from temporalio import workflow
from datetime import timedelta
from temporalio.common import RetryPolicy


with workflow.unsafe.imports_passed_through():
    from activities import (
        download_pdf, 
        extract_to_markdown, 
        upload_markdown
    )
    from helpers import (Download_input, 
    Extract_input, 
    UploadInput, 
    TEMP_DIR
    )


@dataclass
class PDFPipelineInput:
    s3_path: str

@dataclass
class PDFPipelineOutput:
    output_s3_path: str



DEFAULT_RETRY = RetryPolicy(    
    initial_interval=timedelta(seconds=2), #wait 2 seconds before first retry
    backoff_coefficient=2.0, # double the wait each retry: 2s, 4s, 8s
    maximum_interval=timedelta(seconds=60), # max wait is 60 seconds
    maximum_attempts=5 # max attempts is 5
)





@workflow.defn
class PDFPipelineWorkflow:
    @workflow.run
    async def run(self,params: PDFPipelineInput) -> PDFPipelineOutput:
   

        workflow.logger.info(f"Starting PDF pipeline for: {params.s3_path}")
        
        # ── Step 1: Download PDF from S3 ─────────────────────────────────────
        download_result = await workflow.execute_activity(
            download_pdf,
            Download_input(s3_path=params.s3_path),
            retry_policy=DEFAULT_RETRY,
            start_to_close_timeout=timedelta(minutes=3),
        )

        # ── Step 2: Extract PDF to Markdown ─────────────────────────────────
        extract_result = await workflow.execute_activity(
            extract_to_markdown,
            Extract_input(local_pdf_path=download_result.local_path),
            retry_policy=DEFAULT_RETRY,
            start_to_close_timeout=timedelta(minutes=5),
        )

        # ── Step 3: Upload Markdown to S3 ────────────────────────────────────
        upload_result = await workflow.execute_activity(
            upload_markdown,
            UploadInput(
                markdown_text=extract_result.markdown_text,
                original_S3_path=params.s3_path
            ),
            retry_policy=DEFAULT_RETRY,
            start_to_close_timeout=timedelta(minutes=10),
        )
        workflow.logger.info(f"Pipeline complete. Output: {upload_result.output_path}")
        return PDFPipelineOutput(output_s3_path=upload_result.output_path)
