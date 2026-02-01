# Serverless CRM Ingestion Platform

AWS serverless data ingestion pipeline using LocalStack and Pulumi. Handles asynchronous webhook processing with decoupled storage, idempotency checks, and strict security controls.

Designed to be run on localstack free tier.

## Quick Start

### Prerequisites

- Docker (for LocalStack)
- LocalStack
- Pulumi
- Pulumilocal (wrapper for Pulumi)
- direnv
- aws cli
- awslocal
- awscurl

### 1. Set up secrets

In the root of the repository run the following:

```bash
cat <<EOF > .envrc
export WEBHOOK_SECRET_INGEST="super-secret-123"
export WEBHOOK_SECRET_BILLING="money-talks-99"
export WEBHOOK_SECRET_SIGNUP="welcome-hero-00"
EOF

direnv allow
```

### 2. Install and deploy

The quickstart script sets up virtual environments and installs common utilities for the services.

```bash
chmod +x quickstart.sh
./quickstart.sh

# Start headless localstack
localstack start -d

# Set up pulumi local and initialise infrastructure
cd iac
pulumilocal stack init dev
pulumilocal up --yes
```

### 3. Test the pipeline

```bash
curl -X POST "$(pulumilocal stack output webhook_endpoint)/webhook" \
     -H "Content-Type: application/json" \
     -d '{
        "webhook_id": "lead_ingest",
        "secret_key": "super-secret-123",
        "lead_id": "LD-FINAL-001",
        "email": "zote@themighty.com",
        "status": "glorious"
     }'
```

NOTE: If you get a message about a malformed url you may have to export the following environment variable:

```bash
export CONFIG_STRATEGY=overwrite
```

Check logs:

```bash
awslocal logs tail /aws/lambda/crm-webhook-function --follow
```

Check database entries:

```bash
awslocal dynamodb scan --table-name data-table
```

You should have a user named zote_the_mighty with credentials allowing invocation of the service via awscurl, allowing you to retrieve the record you just added:

```bash
export AWS_ACCESS_KEY_ID="$(pulumilocal stack output zote_access_key)"
export AWS_SECRET_ACCESS_KEY="$(pulumilocal stack output zote_secret_key --show-secrets)"
export AWS_REGION=eu-north-1

awscurl \
  --service lambda \
  --region eu-north-1 \
  "$(pulumilocal stack output data_api_url)/leads?email=zote@themighty.com"
```

NOTE: LocalStack does not currently validate SigV4 request signatures for Lambda Function URLs. As a result, AWS_IAM authorization on Function URLs is not enforced locally, and unsigned requests may succeed. The following may also work:

```bash
curl -i "$(pulumilocal stack output data_api_url)/leads?email=zote@themighty.com"
```

## Architecture

**Ingest Layer:** FastAPI webhook handler with Pydantic validation. Intended to receive webhooks from external service.

**Security:** Secrets Manager integration via IAM roles; no plaintext in logs or queues. Uses "poor man's API keys" for services that do not explicitly allow authenticating requests.

**Async Buffer:** SQS decouples webhook from storage, handles traffic spikes.

**Storage:** DynamoDB with SHA-256 hashing for idempotency and duplicate prevention. Single-table design is practical for localstack free-tier constraints.

## Project Structure

- `iac/` - Pulumi infrastructure definitions
- `services/` - Lambda handlers and business logic
- `common/` - Shared models and utilities
