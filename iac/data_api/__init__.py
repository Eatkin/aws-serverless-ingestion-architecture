from typing import List

import pulumi
import pulumi_aws as aws

from iam.lambda_function import add_db_read_policy
from iam.lambda_function import create_lambda_role
from iam.lambda_function import grant_user_invoke_permission
from utils import bundle_directory


class DataAPI(pulumi.ComponentResource):
    def __init__(
        self, name, opts=None, code_bucket=None, database=None, invoke_users=None,
    ) -> None:
        super().__init__("crm-app:egress:DataAPI", name, {}, opts)

        requirements = [code_bucket, database, invoke_users]
        for r in requirements:
            if r is None:
                raise ValueError(
                    "Missing requirement: code bucket, ingestion queue or database"
                )

        if not isinstance(invoke_users, list):
            raise TypeError("Parameter invoke_users must be a list")

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

        # Allow users to invoke
        self.invoke_permissions = []
        for user in invoke_users:
            p = grant_user_invoke_permission(name, self.data_api_lambda, user, opts=self.child_opts)
            self.invoke_permissions.append(p)

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
            )
        )

        return l

    def _create_url(self, name) -> aws.lambda_.FunctionUrl:
        egress_url = aws.lambda_.FunctionUrl(f"{name}-url",
            function_name=self.data_api_lambda.name,
            authorization_type="AWS_IAM",
        )
        return egress_url
