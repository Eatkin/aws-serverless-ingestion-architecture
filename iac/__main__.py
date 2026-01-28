import atexit
import os

import pulumi
import pulumi_aws as aws
from webhook_handler import WebhookHandler
from buckets.code_bucket import CodeBucket

# Create bucket for the lambda function code to go in
code_bucket = CodeBucket("code-bucket")

# CRM webhook
webhook = WebhookHandler("crm-webhook", code_bucket=code_bucket)
pulumi.export("webhook_endpoint", webhook.lambda_url.function_url)


@atexit.register
def cleanup() -> None:
    """Remove zipfiles and junk"""
    junk = ["crm-webhook_bundle.zip"]
    for j in junk:
        if os.path.exists(j):
            os.remove(j)
