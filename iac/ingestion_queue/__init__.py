import pulumi
import pulumi_aws as aws


class IngestionQueue(pulumi.ComponentResource):
    def __init__(self, name, opts=None) -> None:
        super().__init__("crm-app:ingestion:IngestionQueue", name, {}, opts)

        self.child_opts = pulumi.ResourceOptions(parent=self)

        self.queue = self._create_queue(name)

        self.arn = self.queue.arn
        self.url = self.queue.id

        self.register_outputs(
            {
                "queue_arn": self.arn,
                "queue_url": self.url,
            }
        )

    def _create_queue(self, name) -> aws.sqs.Queue:
        """Set up SQS"""
        q = aws.sqs.Queue(
            f"{name}-queue", visibility_timeout_seconds=300, opts=self.child_opts
        )
        return q
