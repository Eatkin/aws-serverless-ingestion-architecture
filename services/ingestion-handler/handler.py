import json
import logging

from pydantic import TypeAdapter
from common.models import DiscriminatedPayload
from common.models import LeadPayload
from common.models import BillingPayload
from common.models import UserSignupPayload

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Create an adapter for our Union type
adapter = TypeAdapter(DiscriminatedPayload)


def handler(event, context):
    for record in event["Records"]:
        try:
            # SQS body is a string, so load it first
            raw_body = json.loads(record["body"])

            payload = adapter.validate_python(raw_body)

            # Route based on the actual class type
            if isinstance(payload, LeadPayload):
                process_lead(payload)
            elif isinstance(payload, BillingPayload):
                process_billing(payload)
            elif isinstance(payload, UserSignupPayload):
                process_signup(payload)

        except Exception as e:
            logger.error(f"Failed to process record {record['messageId']}: {e}")
            raise e  # Keeps message in SQS for retry


def process_lead(payload: LeadPayload):
    logger.info(f"PROCESSING LEAD: {payload.email} - Status: ({payload.status})")


def process_billing(payload: BillingPayload):
    logger.info(
        f"PROCESSING BILLING: {payload.customer_id} - Amount: {payload.amount} {payload.currency}"
    )


def process_signup(payload: UserSignupPayload):
    logger.info(
        f"PROCESSING SIGNUP: {payload.username} - Source Campaign: {payload.source_campaign}"
    )
