import atexit
import os
from typing import Any
from typing import Dict

import pulumi
import pulumi_aws as aws
from webhook_handler import WebhookHandler
from buckets.code_bucket import CodeBucket

infra: Dict[str, Any] = {}

# Create bucket for the lambda function code to go in
infra["code_bucket"] = CodeBucket("code-bucket")

# CRM webhook
infra["webhook_handler"] = WebhookHandler(
    "crm-webhook", code_bucket=infra["code_bucket"]
)
pulumi.export("webhook_endpoint", infra["webhook_handler"].lambda_url.function_url)


@atexit.register
def cleanup() -> None:
    """Remove zipfiles and junk"""
    for _, o in infra.items():
        if not hasattr(o, "junk"):
            continue

        for j in o.junk:
            if os.path.exists(j):
                os.remove(j)
