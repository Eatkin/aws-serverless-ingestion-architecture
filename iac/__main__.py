import atexit
import os
from typing import Any
from typing import Dict

import pulumi
import pulumi_aws as aws

from buckets.code_bucket import CodeBucket
from database import Database
from ingestion_handler import IngestionHandler
from ingestion_queue import IngestionQueue
from webhook_handler import WebhookHandler

infra: Dict[str, Any] = {}

# Create bucket for the webhook lambda function code to go in
infra["code_bucket"] = CodeBucket("crm-code")

# Ingestion queue for webhook lambda to queue to
infra["ingestion_queue"] = IngestionQueue("crm-ingestion-sqs")
pulumi.export("ingestion_queue_url", infra["ingestion_queue"].queue.url)

# Lambda to accept incoming webhooks
infra["webhook_handler"] = WebhookHandler(
    "crm-webhook",
    code_bucket=infra["code_bucket"].code_bucket,
    ingestion_queue=infra["ingestion_queue"].queue,
)
pulumi.export("webhook_endpoint", infra["webhook_handler"].lambda_url.function_url)
pulumi.export("webhook_id", infra["webhook_handler"].webhook_lambda.id)
pulumi.export("webhook_arn", infra["webhook_handler"].webhook_lambda.arn)

# Database for storage
infra["database"] = Database("database")
pulumi.export("database_arn", infra["database"].db.arn)

# Lambda to ingest data from the queue and write to db
infra["ingestion_handler"] = IngestionHandler(
    "crm-ingest",
    code_bucket=infra["code_bucket"].code_bucket,
    ingestion_queue=infra["ingestion_queue"].queue,
    database=infra["database"].db,
)
pulumi.export("ingester_id", infra["ingestion_handler"].ingestion_lambda.id)
pulumi.export("ingester_arn", infra["ingestion_handler"].ingestion_lambda.arn)


@atexit.register
def cleanup() -> None:
    """Remove zipfiles and junk"""
    for _, o in infra.items():
        if not hasattr(o, "junk"):
            continue

        for j in o.junk:
            if os.path.exists(j):
                os.remove(j)
