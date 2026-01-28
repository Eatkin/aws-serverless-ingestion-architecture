import json
import shutil
import subprocess
import sys
import tempfile

import pulumi
import pulumi_aws as aws


class WebhookHandler(pulumi.ComponentResource):
    def __init__(self, name, opts=None, code_bucket=None) -> None:
        super().__init__("crm-app:ingestion:WebhookHandler", name, {}, opts)

        if code_bucket is None:
            raise ValueError("Cannot deploy lambda without specifying bucket")

        self.junk = []

        self.code_bucket = code_bucket

        self.child_opts = pulumi.ResourceOptions(parent=self)

        self.role = self._create_role(name)
        self.queue = self._create_queue(name)
        self._attach_permissions(name)

        self.webhook_lambda = self._create_lambda(name)
        self.lambda_url = self._create_lambda_url(name)

        self.register_outputs({"url": self.lambda_url.function_url})

    def _create_lambda(self, name) -> aws.lambda_.Function:
        """Dumb, package and upload to bucket
        Better using Docker but no ECR with LocalStack"""
        bundle_name = f"{name}_bundle"
        bundle_file = f"{bundle_name}.zip"

        with tempfile.TemporaryDirectory() as build:
            shutil.copytree("../services/webhook-handler", build, dirs_exist_ok=True)

            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "-r",
                    f"{build}/requirements.txt",
                    "-t",
                    build,
                    "--platform",
                    "manylinux2014_x86_64",
                    "--only-binary=:all:",
                ],
                check=True,
            )

            shutil.make_archive(bundle_name, "zip", build)

            self.junk.append(bundle_file)

        code_blob = aws.s3.BucketObject(
            f"{name}-zip",
            bucket=self.code_bucket.id,
            key=bundle_file,
            source=pulumi.FileArchive(bundle_file),
        )

        return aws.lambda_.Function(
            f"{name}-function",
            role=self.role.arn,
            runtime="python3.12",
            handler="handler.handler",
            s3_bucket=self.code_bucket.id,
            s3_key=code_blob.key,
            timeout=30,
            opts=self.child_opts,
            environment={"variables": {"QUEUE_URL": self.queue.id}},
        )

    def _create_queue(self, name) -> aws.sqs.Queue:
        """Set up SQS"""
        q = aws.sqs.Queue(
            f"{name}-queue", visibility_timeout_seconds=300, opts=self.child_opts
        )
        return q

    def _create_role(self, name) -> aws.iam.Role:
        """Create role for lambda service"""
        role = aws.iam.Role(
            name,
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
            opts=self.child_opts,
        )
        return role

    def _attach_permissions(self, name) -> None:
        """Attach permissings to queue and lambda service"""
        self.lambda_policy = aws.iam.RolePolicyAttachment(
            f"{name}-logs",
            role=self.role.name,
            policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
            opts=self.child_opts,
        )
        self.queue_policy = aws.iam.RolePolicy(
            f"{name}-sqs-policy",
            role=self.role.id,
            policy=self.queue.arn.apply(
                lambda arn: json.dumps(
                    {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Action": "sqs:SendMessage",
                                "Effect": "Allow",
                                "Resource": arn,
                            }
                        ],
                    }
                )
            ),
            opts=self.child_opts,
        )

    def _create_lambda_url(self, name) -> aws.lambda_.FunctionUrl:
        url = aws.lambda_.FunctionUrl(
            name,
            function_name=self.webhook_lambda.name,
            authorization_type="NONE",
            opts=self.child_opts,
        )
        return url
