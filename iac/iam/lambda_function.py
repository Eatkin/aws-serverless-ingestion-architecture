import json
import pulumi_aws as aws


def create_lambda_role(name, opts) -> aws.iam.Role:
    # Allows Lambda to use this role
    role = aws.iam.Role(
        f"{name}-role",
        assume_role_policy=json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Action": "sts:AssumeRole",
                        "Effect": "Allow",
                        "Principal": {"Service": "lambda.amazonaws.com"},
                    }
                ],
            }
        ),
        opts=opts,
    )

    # Allows writing logs to CloudWatch
    aws.iam.RolePolicyAttachment(
        f"{name}-logs",
        role=role.name,
        policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
        opts=opts,
    )
    return role


def add_sqs_send_policy(name, role, queue_arn, opts) -> aws.iam.RolePolicy:
    # Allow sending to specific queue
    sqs_policy_doc = aws.iam.get_policy_document(
        statements=[
            {
                "actions": ["sqs:SendMessage"],
                "resources": [queue_arn],
            }
        ]
    )
    return aws.iam.RolePolicy(
        f"{name}-sqs-send",
        role=role.id,
        policy=sqs_policy_doc.json,
        opts=opts,
    )


def add_sqs_consumer_policy(name, role, queue_arn, opts) -> aws.iam.RolePolicy:
    policy_doc = aws.iam.get_policy_document(
        statements=[
            {
                "actions": [
                    "sqs:ReceiveMessage",
                    "sqs:DeleteMessage",
                    "sqs:GetQueueAttributes",
                ],
                "resources": [queue_arn],
            }
        ]
    )

    return aws.iam.RolePolicy(
        f"{name}-sqs-consumer-policy", role=role.id, policy=policy_doc.json, opts=opts
    )


def add_db_read_policy(name, role, db_arn, opts) -> aws.iam.RolePolicy:
    """Grants read-only access: Get, Query, and Scan."""
    policy_doc = aws.iam.get_policy_document(
        statements=[
            {
                "actions": [
                    "dynamodb:GetItem",
                    "dynamodb:BatchGetItem",
                    "dynamodb:Query",
                    "dynamodb:Scan",
                    "dynamodb:DescribeTable",
                ],
                "resources": [db_arn],
            }
        ]
    )

    return aws.iam.RolePolicy(
        f"{name}-db-read-policy", role=role.id, policy=policy_doc.json, opts=opts
    )


def add_db_write_policy(name, role, db_arn, opts) -> aws.iam.RolePolicy:
    """Grants full CRUD: Put, Update, and Delete."""
    policy_doc = aws.iam.get_policy_document(
        statements=[
            {
                "actions": [
                    "dynamodb:PutItem",
                    "dynamodb:UpdateItem",
                    "dynamodb:DeleteItem",
                    "dynamodb:BatchWriteItem",
                    "dynamodb:GetItem",
                    "dynamodb:Query",
                ],
                "resources": [db_arn],
            }
        ]
    )

    return aws.iam.RolePolicy(
        f"{name}-db-write-policy", role=role.id, policy=policy_doc.json, opts=opts
    )
