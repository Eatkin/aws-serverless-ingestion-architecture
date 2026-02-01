import json
from dataclasses import dataclass

import pulumi
import pulumi_aws as aws

@dataclass
class User:
    user: aws.iam.User
    keys: aws.iam.AccessKey
    literal_name: str

class ApiAccessManager(pulumi.ComponentResource):
    def __init__(self, name, opts=None) -> None:
        super().__init__("crm-app:egress:DataAPIAccess", name, {}, opts)
        self.child_opts = pulumi.ResourceOptions(parent=self)
        self.invoker_role = aws.iam.Role(f"{name}-invoker-role",
            assume_role_policy=json.dumps({
                "Version": "2012-10-17",
                "Statement": [{
                    "Effect": "Allow",
                    "Principal": {"AWS": "*"}, 
                    "Action": "sts:AssumeRole"
                }]
            }),
            opts=self.child_opts
        )

        self.invoker_group = aws.iam.Group(f"{name}-invoker-group",
            opts=self.child_opts)

        group_policy_doc = aws.iam.get_policy_document_output(
            statements=[aws.iam.GetPolicyDocumentStatementArgs(
            effect="Allow",
            actions=["sts:AssumeRole"],
            resources=[self.invoker_role.arn], 
        )],
    )

        self.group_assume_policy = aws.iam.GroupPolicy(f"{name}-group-policy",
            group=self.invoker_group.name,
            policy=group_policy_doc.json,
            opts=self.child_opts
            )

    def create_user(self, user_name: str):
        """Helper to create a user and put them in the group."""
        user = aws.iam.User(user_name)
        aws.iam.GroupMembership(f"mem-{user_name}",
            group=self.invoker_group.name,
            users=[user.name],
            opts=self.child_opts
        )
        keys = aws.iam.AccessKey(f"{user_name}-keys", user=user.name,
            opts=self.child_opts)
        return User(user, keys, user_name)