import json
import os
from typing import List

import pulumi
import pulumi_aws as aws

from iam.lambda_function import add_db_read_policy
from iam.lambda_function import create_lambda_role
from utils import bundle_directory


class DataAPI(pulumi.ComponentResource):
    def __init__(
        self, name, opts=None, code_bucket=None, database=None
    ) -> None:
        super().__init__("crm-app:ingestion:IngestionHandler", name, {}, opts)

        requirements = [code_bucket, database]
        for r in requirements:
            if r is None:
                raise ValueError(
                    "Missing requirement: code bucket, ingestion queue or database"
                )

        self.junk: List[str] = []

        self.code_bucket = code_bucket
        self.db = database

        self.child_opts = pulumi.ResourceOptions(parent=self)

        # Roles handled by iam module
        self.role = create_lambda_role(name, self.child_opts)
        self._database_policy = add_db_read_policy(
            name, self.role, self.db.arn, opts=self.child_opts  # type: ignore
        )

        self.data_api_lambda = self._create_lambda(name)
        self.url = self._create_url(name)

        self.register_outputs({"data_api_url": self.url})

    def _create_lambda(self, name) -> aws.lambda_.Function:
        """Dumb, package and upload to bucket
        Better using Docker but no ECR with LocalStack"""
        bundle_name = f"{name}_bundle"
        bundle_file = f"{bundle_name}.zip"
        source = "../services/data-api"
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
                variables={
                    "TABLE_NAME": self.db.name
                }
            ),
        )

        return l

    def _create_url(self, name) -> aws.lambda_.FunctionUrl:
        egress_url = aws.lambda_.FunctionUrl(f"{name}-url",
            function_name=self.data_api_lambda.name,
            authorization_type="NONE", # TODO: Set IAM auth
        )
        return egress_url
