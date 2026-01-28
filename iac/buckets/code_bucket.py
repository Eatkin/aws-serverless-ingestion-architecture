import pulumi
import pulumi_aws as aws


class CodeBucket(pulumi.ComponentResource):
    def __init__(self, name, opts=None) -> None:
        """Create a bucket for code to go in for lambda functions"""
        super().__init__("crm-app:ingestion:bucket", name, {}, opts)

        self.child_opts = pulumi.ResourceOptions(parent=self)

        self.code_bucket = aws.s3.Bucket(f"{name}-code-bucket", force_destroy=True)

        self.register_outputs(
            {"bucket_id": self.code_bucket.id, "bucket_arn": self.code_bucket.arn}
        )
