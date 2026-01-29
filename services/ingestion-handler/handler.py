import json
import logging
import os

import boto3
import botocore.exceptions
from pydantic import TypeAdapter

from common.models import DiscriminatedStoragePayload as StoragePayload
from common.models import LeadStorage
from common.models import BillingStorage
from common.models import UserSignupStorage
from common.utils import get_stable_hash

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Create an adapter for our Union type
adapter = TypeAdapter(StoragePayload)

TABLE = None


def get_table():
    """Lazy load table"""
    global TABLE
    if TABLE is None:
        table_name = os.environ.get("TABLE_NAME", "data-table")
        TABLE = boto3.resource("dynamodb").Table(table_name)

    return TABLE


def save_to_db(payload, pk, sk, uid):
    table = get_table()
    try:
        table.put_item(
            Item={"PK": pk, "SK": sk, "record_hash": uid, **payload.model_dump()},
            # Fail if already written
            ConditionExpression="attribute_not_exists(PK) AND attribute_not_exists(SK)",
        )
        logger.info(f"Successfully saved {sk} for {pk}")
    except botocore.exceptions.ClientError as e:
        # Avoid sending to dlq
        if (
            e.response.get("Error", {}).get("Code", "")
            == "ConditionalCheckFailedException"
        ):
            logger.info(f"Duplicate ignored for {pk} | {sk}")
        else:
            raise e


def handler(event, context):
    dlq = []
    for record in event["Records"]:
        message_id = record["messageId"]
        try:
            # SQS body is a string, so load it first
            raw_body = json.loads(record["body"])

            # Hash prevents data duplication
            uid = get_stable_hash(record["body"])

            payload = adapter.validate_python(raw_body)

            # Route based on the actual class type
            if isinstance(payload, LeadStorage):
                process_lead(payload, uid)
            elif isinstance(payload, BillingStorage):
                process_billing(payload, uid)
            elif isinstance(payload, UserSignupStorage):
                process_signup(payload, uid)

        except Exception as e:
            logger.error(f"Failed to process record {record['messageId']}: {e}")
            dlq.append({"itemIdentifier": message_id})

    return {"batchItemFailures": dlq}


def process_lead(payload: LeadStorage, uid: str):
    logger.info(f"PROCESSING LEAD: {payload.email} - Status: ({payload.status})")
    save_to_db(
        payload=payload,
        pk=f"USER#{payload.email}",
        sk=f"LEAD#{payload.lead_id}",
        uid=uid,
    )


def process_billing(payload: BillingStorage, uid: str):
    logger.info(
        f"PROCESSING BILLING: {payload.customer_id} - Amount: {payload.amount} {payload.currency}"
    )
    save_to_db(
        payload=payload,
        pk=f"USER#{payload.customer_id}",
        sk=f"BILL#{payload.transaction_id}",
        uid=uid,
    )


def process_signup(payload: UserSignupStorage, uid: str):
    logger.info(
        f"PROCESSING SIGNUP: {payload.username} - Source Campaign: {payload.source_campaign}"
    )
    # Static sk
    save_to_db(payload=payload, pk=f"USER#{payload.email}", sk="METADATA", uid=uid)
