# Serverless CRM Ingestion Platform

AWS serverless data ingestion pipeline using LocalStack and Pulumi. Handles asynchronous webhook processing with decoupled storage, idempotency checks, and strict security controls.

Designed to be run on localstack free tier.

## Quick Start

### Prerequisites

- Docker (for LocalStack)
- LocalStack
- Pulumilocal (wrapper for Pulumi)
- direnv

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

awslocal dynamodb scan --table-name data-table
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
