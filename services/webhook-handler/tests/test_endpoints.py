import importlib
import sys
import json
import importlib
import importlib.util
import sys
import os
import types
import json

from fastapi.testclient import TestClient


def _import_handler_with_dummy(monkeypatch):
    """Import handler while patching boto3.client to avoid real AWS calls.

    This helper ensures the project root is on sys.path so import handler
    works when tests run under pytest, and it injects a fake boto3 module
    if boto3 isn't installed in the test environment.
    """

    class DummySQS:
        def __init__(self):
            self.sent = []

        def send_message(self, QueueUrl, MessageBody):
            # Record calls so tests can assert on them
            self.sent.append({"QueueUrl": QueueUrl, "MessageBody": MessageBody})
            return {"MessageId": "msg-1"}

    dummy = DummySQS()

    # Ensure QUEUE_URL exists so handler doesn't pass None to SQS
    monkeypatch.setenv("QUEUE_URL", "https://example.com/queue")

    # Ensure the package root is on sys.path so `import handler` works
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    # If boto3 isn't installed in the environment, inject a minimal fake module
    if importlib.util.find_spec("boto3") is None:
        fake_boto3 = types.SimpleNamespace()
        fake_boto3.client = lambda service: dummy
        sys.modules["boto3"] = fake_boto3  # type: ignore[reportArgumentType]
    else:
        # Patch boto3.client to return our dummy SQS client
        monkeypatch.setattr("boto3.client", lambda service: dummy)

    # Force a fresh import of handler so our monkeypatch is used during module import
    if "handler" in sys.modules:
        del sys.modules["handler"]

    handler = importlib.import_module("handler")
    # Ensure the models secret lookup returns expected test secrets by default.
    # Import models and monkeypatch its lookup so tests don't depend on module
    # constants and so future secret-manager changes are easy to test.
    from common import models

    default_secrets = {
        "lead_ingest": "super-secret-123",
        "billing_update": "money-talks-99",
        "user_signup": "welcome-hero-00",
    }

    monkeypatch.setattr(
        models, "get_secret_for_webhook", lambda wid: default_secrets.get(wid)
    )

    return handler, dummy


def test_root(monkeypatch):
    handler, _dummy = _import_handler_with_dummy(monkeypatch)
    client = TestClient(handler.app)

    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json() == {"status": "online"}


def test_lead_payload_accepted(monkeypatch):
    handler, dummy = _import_handler_with_dummy(monkeypatch)
    client = TestClient(handler.app)

    payload = {
        "webhook_id": "lead_ingest",
        "secret_key": "super-secret-123",
        "lead_id": "lead_123",
        "email": "lead@example.com",
        "status": "new",
    }

    resp = client.post("/webhook", json=payload)
    assert resp.status_code == 202
    assert resp.json() == {"status": "accepted"}

    # Ensure message was sent to SQS
    assert len(dummy.sent) == 1
    body = json.loads(dummy.sent[0]["MessageBody"])
    assert body["webhook_id"] == "lead_ingest"
    assert body["lead_id"] == "lead_123"


def test_billing_payload_accepted(monkeypatch):
    handler, dummy = _import_handler_with_dummy(monkeypatch)
    client = TestClient(handler.app)

    payload = {
        "webhook_id": "billing_update",
        "secret_key": "money-talks-99",
        "customer_id": "cust_007",
        "amount": 123.45,
        "currency": "USD",
        "transaction_id": "txn_001",
    }

    resp = client.post("/webhook", json=payload)
    assert resp.status_code == 202
    assert resp.json() == {"status": "accepted"}

    assert len(dummy.sent) == 1
    body = json.loads(dummy.sent[0]["MessageBody"])
    assert body["webhook_id"] == "billing_update"
    assert body["transaction_id"] == "txn_001"


def test_user_signup_payload_accepted(monkeypatch):
    handler, dummy = _import_handler_with_dummy(monkeypatch)
    client = TestClient(handler.app)

    payload = {
        "webhook_id": "user_signup",
        "secret_key": "welcome-hero-00",
        "username": "new_user",
        "email": "user@example.com",
        "source_campaign": "spring_launch",
        "is_premium": False,
    }

    resp = client.post("/webhook", json=payload)
    assert resp.status_code == 202
    assert resp.json() == {"status": "accepted"}

    assert len(dummy.sent) == 1
    body = json.loads(dummy.sent[0]["MessageBody"])
    assert body["webhook_id"] == "user_signup"
    assert body["username"] == "new_user"


def test_invalid_secret_rejected(monkeypatch):
    handler, _dummy = _import_handler_with_dummy(monkeypatch)
    client = TestClient(handler.app)

    payload = {
        "webhook_id": "lead_ingest",
        "secret_key": "wrong-secret",
        "lead_id": "lead_999",
        "email": "bad@example.com",
    }

    resp = client.post("/webhook", json=payload)
    # Validation should fail due to our field validator rejecting the secret
    assert resp.status_code == 422


def test_missing_required_field_rejected(monkeypatch):
    handler, _dummy = _import_handler_with_dummy(monkeypatch)
    client = TestClient(handler.app)

    # billing_update requires transaction_id; omit it
    payload = {
        "webhook_id": "billing_update",
        "secret_key": "money-talks-99",
        "customer_id": "cust_007",
        "amount": 10.0,
        "currency": "USD",
    }

    resp = client.post("/webhook", json=payload)
    assert resp.status_code == 422


def test_unknown_webhook_id_rejected(monkeypatch):
    handler, _dummy = _import_handler_with_dummy(monkeypatch)
    client = TestClient(handler.app)

    payload = {
        "webhook_id": "does_not_exist",
        "secret_key": "nope",
        "foo": "bar",
    }

    resp = client.post("/webhook", json=payload)
    # Discriminator should reject unknown webhook_id
    assert resp.status_code == 422
