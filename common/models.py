from typing import Annotated
from typing import Literal
from typing import Union

from pydantic import BaseModel
from pydantic import Field
from pydantic import model_validator


SUPER_SECRET_PASSWORDS = {
    "lead_ingest": "super-secret-123",
    "billing_update": "money-talks-99",
    "user_signup": "welcome-hero-00",
}


def get_secret_for_webhook(webhook_id: str) -> str | None:
    """Return the secret for a webhook id.

    This is deliberately a separate function so tests can monkeypatch
    it, or it can later be replaced with a call to a secrets manager.
    """
    return SUPER_SECRET_PASSWORDS.get(webhook_id)


class StorageBaseModel(BaseModel):
    webhook_id: str = Field(..., description="Unique ID for the webhook type")


class WebhookBaseModel(BaseModel):
    secret_key: str = Field(..., description="The poor man's API key")

    @model_validator(mode="after")
    def validate_signature(self) -> "WebhookBaseModel":
        webhook_id = getattr(self, "webhook_id", None)
        secret_key = self.secret_key

        if not webhook_id:
            raise ValueError("webhook_id is missing from the payload")

        expected_secret = get_secret_for_webhook(webhook_id)

        if secret_key != expected_secret:
            raise ValueError(f"Invalid signature for webhook type: {webhook_id}")

        return self


class LeadStorage(StorageBaseModel):
    webhook_id: Literal["lead_ingest"]  # type: ignore[override]
    lead_id: str
    email: str
    status: str = "new"


class LeadIngest(LeadStorage, WebhookBaseModel):
    pass


class BillingStorage(StorageBaseModel):
    webhook_id: Literal["billing_update"]  # type: ignore[override]
    customer_id: str
    amount: float
    currency: str = "USD"
    transaction_id: str


class BillingIngest(BillingStorage, WebhookBaseModel):
    pass


class UserSignupStorage(StorageBaseModel):
    webhook_id: Literal["user_signup"]  # type: ignore[override]
    username: str
    email: str
    source_campaign: str | None = None
    is_premium: bool = False


class UserSignupIngest(UserSignupStorage, WebhookBaseModel):
    pass


DiscriminatedIngestionPayload = Annotated[
    Union[LeadIngest, BillingIngest, UserSignupIngest],
    Field(discriminator="webhook_id"),
]

DiscriminatedStoragePayload = Annotated[
    Union[LeadStorage, BillingStorage, UserSignupStorage],
    Field(discriminator="webhook_id"),
]
