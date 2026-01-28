from typing import Annotated
from typing import Literal
from typing import Union

from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator
from pydantic import ValidationInfo


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


class WebhookBaseModel(BaseModel):
    webhook_id: str = Field(..., description="Unique ID for the webhook type")
    secret_key: str = Field(..., description="The poor man's API key")

    @field_validator("secret_key")
    @classmethod
    def validate_signature(cls, v: str, info: ValidationInfo):
        # Access previously validated fields via info.data
        webhook_id = info.data.get("webhook_id")

        if not webhook_id:
            raise ValueError("webhook_id must be provided before secret_key")

        # Use a lookup function so tests or future secret manager
        # integrations can override how secrets are retrieved.
        expected_secret = get_secret_for_webhook(webhook_id)

        if v != expected_secret:
            raise ValueError(f"Invalid signature for webhook type: {webhook_id}")

        return v


class LeadPayload(WebhookBaseModel):
    webhook_id: Literal["lead_ingest"]  # type: ignore[override]
    lead_id: str
    email: str
    status: str = "new"


class BillingPayload(WebhookBaseModel):
    webhook_id: Literal["billing_update"]  # type: ignore[override]
    customer_id: str
    amount: float
    currency: str = "USD"
    transaction_id: str


class UserSignupPayload(WebhookBaseModel):
    webhook_id: Literal["user_signup"]  # type: ignore[override]
    username: str
    email: str
    source_campaign: str | None = None
    is_premium: bool = False


DiscriminatedPayload = Annotated[
    Union[LeadPayload, BillingPayload, UserSignupPayload],
    Field(discriminator="webhook_id"),
]
