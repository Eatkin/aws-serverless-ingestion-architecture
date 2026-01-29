import pulumi
import pulumi_aws as aws


class Database(pulumi.ComponentResource):
    def __init__(self, name, opts=None) -> None:
        super().__init__("crm-app:ingestion:IngestionHandler", name, {}, opts)

        self.child_opts = pulumi.ResourceOptions(parent=self)

        self.db = self._create_table(name)
        self.register_outputs({"database_arn": self.db.arn})

    def _create_table(self, name) -> aws.dynamodb.Table:
        crm_table = aws.dynamodb.Table(
            f"{name}-table",
            name="data-table",
            attributes=[
                aws.dynamodb.TableAttributeArgs(name="PK", type="S"),
                aws.dynamodb.TableAttributeArgs(name="SK", type="S"),
            ],
            hash_key="PK",
            range_key="SK",
            billing_mode="PAY_PER_REQUEST",
            opts=self.child_opts,
        )
        return crm_table
