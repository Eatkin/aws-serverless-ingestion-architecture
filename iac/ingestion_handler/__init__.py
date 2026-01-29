from typing import List

import pulumi
import pulumi_aws as aws

from iam.lambda_function import add_sqs_consumer_policy
from iam.lambda_function import create_lambda_role
from iam.lambda_function import add_db_write_policy
from utils import bundle_directory


class IngestionHandler(pulumi.ComponentResource):
    def __init__(
        self, name, opts=None, code_bucket=None, ingestion_queue=None, database=None
    ) -> None:
        super().__init__("crm-app:ingestion:IngestionHandler", name, {}, opts)

        requirements = [code_bucket, ingestion_queue, database]
        for r in requirements:
            if r is None:
                raise ValueError(
                    "Missing requirement: code bucket, ingestion queue or database"
                )

        self.junk: List[str] = []

        self.code_bucket = code_bucket
        self.queue = ingestion_queue
        self.db = database

        self.child_opts = pulumi.ResourceOptions(parent=self)

        # Roles handled by iam module
        self.role = create_lambda_role(name, self.child_opts)
        self._consumer_policy = add_sqs_consumer_policy(
            name, self.role, self.queue.arn, self.child_opts  # type: ignore
        )
        self._database_policy = add_db_write_policy(
            name, self.role, self.db.arn, opts=self.child_opts  # type: ignore
        )

        self.ingestion_lambda = self._create_lambda(name)

        self.register_outputs({})

    def _create_lambda(self, name) -> aws.lambda_.Function:
        """Dumb, package and upload to bucket
        Better using Docker but no ECR with LocalStack"""
        bundle_name = f"{name}_bundle"
        bundle_file = f"{bundle_name}.zip"
        source = "../services/ingestion-handler"
        bundle_directory(source, bundle_name)

        self.junk.append(bundle_file)

        code_blob = aws.s3.BucketObject(
            f"{name}-zip",
            bucket=self.code_bucket.id,  # type: ignore
            key=bundle_file,
            source=pulumi.FileArchive(bundle_file),
        )

        l = aws.lambda_.Function(
            f"{name}-function",
            name=f"{name}-function",
            role=self.role.arn,
            runtime="python3.12",
            handler="handler.handler",
            s3_bucket=self.code_bucket.id,  # type: ignore
            s3_key=code_blob.key,
            timeout=60,
            opts=self.child_opts,
            environment=aws.lambda_.FunctionEnvironmentArgs(
                variables={"DATABASE_NAME": self.db.name}  # type: ignore
            ),
        )

        # Set up queue as a source
        aws.lambda_.EventSourceMapping(
            f"{name}-sqs-mapping",
            event_source_arn=self.queue.arn,  # type: ignore
            function_name=l.name,
            batch_size=5,
            function_response_types=["ReportBatchItemFailures"],
            opts=self.child_opts,
        )
        return l
