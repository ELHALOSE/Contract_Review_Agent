import asyncio
import textwrap
from dataclasses import dataclass
from datetime import timedelta
from typing import Optional
import json_repair
import json

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError
from temporalio.workflow import ParentClosePolicy

from prompts import _SYNTHESIS_PROMPT, _REVISION_PROMPT

with workflow.unsafe.imports_passed_through():
    from activities import (
        call_llm, CallLLMInput,
    )
    from child_workflow import (
        PDFSummaryWorkflow, PDFSummaryInput
    )

    
DEFAULT_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=3),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(seconds=60),
    maximum_attempts=4,
)

@dataclass
class ContractReviewInput:
    s3_paths: list
    max_revisions: int = 2


@dataclass
class ContractReviewOutput:
    report: str
    source: list
    approved_by: str




@workflow.defn
class ContractReviewWorkflow:
    def __init__(self):
        self.status: str = "processing"
        self._summaries: list= []
        self._report: str = ""

    @workflow.run
    #step 1: Fan-out:- one child workflow per pdf, all in parallel
    async def run(self,params: ContractReviewInput) -> ContractReviewOutput:
        self._status = "extracting"

        workflow.logger.info(f"fanning out to{len(params.s3_paths)} child workflows")

        workflow_id = workflow.info().workflow_id
        workflow_task_queue = workflow.info().task_queue

        handles = await asyncio.gather(
            *[
                workflow.start_child_workflow(
                    PDFSummaryWorkflow.run,
                    PDFSummaryInput(s3_path=current_s3_path),
                    id= f"{workflow_id}-pdf-{idx+1}",
                    task_queue=workflow_task_queue,

                    parent_close_policy=ParentClosePolicy.ABANDON
                )
                for idx,current_s3_path in enumerate(params.s3_paths)

            ]
        )

        raw_results = await asyncio.gather(
            *handles,
            return_exceptions=True, 
        )

        for i,res in enumerate(raw_results):
            if isinstance(res, Exception):
                workflow.logger.warning(f"PDF {i} failed with {res}")
            else:
                self._summaries.append({
                    "s3_path": res.s3_path,
                    "summary": res.summary,
                    "key_risks": res.key_risks
                })

        if len(self._summaries) == 0:
            raise ApplicationError("no pdfs processed")
        


        # Step 2: Synthesize all summaries into a risk report
        self._status = "analyizing"
        workflow.logger.info(f"Synthesize {len(self._summaries)} summaries")

        combined_summary = "\n\n".join([

            f"**Contract {i+1}** (`{summary['s3_path']}`):\n"
            f"Summary: {summary['summary']}\n"
            f"Risks: {summary['key_risks']}"

            for i, summary in enumerate(self._summaries)
        ])

        llm_prompt = _SYNTHESIS_PROMPT.format(
            summaries=combined_summary,
            n = len(self._summaries)
        )

        llm_result = await workflow.execute_activity(
            call_llm,
            CallLLMInput(prompt=llm_prompt),
            retry_policy=DEFAULT_RETRY_POLICY,
            start_to_close_timeout=timedelta(minutes=3),
            heartbeat_timeout=timedelta(seconds=180),
        )


        # At the end of ContractReviewWorkflow.run
        parsed_report = json_repair.loads(llm_result.content)

        return ContractReviewOutput(
            report=json.dumps(parsed_report),
            source=params.s3_paths,
            approved_by="System"
        )