import json
import logging
import os
import sys
from typing import Any
from typing import Dict

import boto3
import botocore.exceptions
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import status
from mangum import Mangum

from common.models import DiscriminatedIngestionPayload as IngestionPayload
from common.models import DiscriminatedStoragePayload as StoragePayload
from common.models import BillingIngest
from common.models import BillingStorage
from common.models import LeadIngest
from common.models import LeadStorage
from common.models import UserSignupIngest
from common.models import UserSignupStorage


def setup_logging() -> logging.Logger:
    """Setup CRM ingestion logger"""
    logger = logging.getLogger("crm_ingestion")

    if not logger.handlers:
        logger.setLevel(logging.INFO)
        stream_handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter("%(levelname)s | %(name)s | %(message)s")
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)
        logger.propagate = False

    return logger


QUEUE_URL = os.environ.get("QUEUE_URL")

app = FastAPI(title="CRM Ingestion Webhook")

logger = setup_logging()

_sqs_client = None


def get_sqs_client():
    """Lazily create and return a boto3 SQS client."""
    global _sqs_client
    if _sqs_client is None:
        _sqs_client = boto3.client("sqs")
    return _sqs_client


def transmute_to_storage(ingest_data: IngestionPayload) -> StoragePayload:
    """Converts any Ingest model to its corresponding Storage model, stripping secrets."""
    if isinstance(ingest_data, LeadIngest):
        return LeadStorage.model_validate(ingest_data, from_attributes=True)
    if isinstance(ingest_data, BillingIngest):
        return BillingStorage.model_validate(ingest_data, from_attributes=True)
    if isinstance(ingest_data, UserSignupIngest):
        return UserSignupStorage.model_validate(ingest_data, from_attributes=True)
    raise ValueError("Unknown payload type")


@app.get("/", status_code=status.HTTP_200_OK)
async def root() -> Dict[str, str]:
    """Returns service status"""
    return {"status": "online"}


@app.post("/webhook", status_code=status.HTTP_202_ACCEPTED)
def receive_webhook(data: IngestionPayload) -> Dict[str, str]:
    """Accepts a payload and send to SQS Queue
    Raises:
        HTTPException if no data received
    """
    logger.info(f"Received Webhook Data: {data}")

    if not data:
        logger.warning("Received empty payload")
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail={"status": "error", "message": "No data received"},
        )

    try:
        storage_data = transmute_to_storage(data)
        get_sqs_client().send_message(
            QueueUrl=QUEUE_URL, MessageBody=json.dumps(storage_data.model_dump())
        )
        return {"status": "accepted"}
    except botocore.exceptions.ClientError as error:
        logger.exception("Failed to send to SQS")
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"status": "error", "message": "Internal storage failure"},
        )
    except Exception as e:
        logging.exception("Unknown exception occurred")
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"status": "error", "message": str(e)},
        )


# Mangum wrapper for Lambda
handler = Mangum(app, lifespan="off")
