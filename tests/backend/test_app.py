import logging

from pydantic import HttpUrl
from fastapi.testclient import TestClient

from gfibot.collections import *
from gfibot.backend.server import app
from gfibot.backend.models import *


def test_webhook_issue_open(mock_mongodb):
    client = TestClient(app)
    response = client.post(
        "/api/app/webhook",
        json={
            "action": "opened",
            "sender": {"id": 1},
            "installation": {"id": 1},
            "repository": {"full_name": "owner/name", "name": "name"},
            "issue": {"number": 1, "title": "title", "body": "body"},
        },
        headers={"X-GitHub-Event": "issues"},
    )
    logging.info(response.json())
    assert response.status_code == 200
    res = GFIResponse[str].parse_obj(response.json())
    assert "not implemented" in res.result.lower()


def test_webhook_create(mock_mongodb):
    client = TestClient(app)
    response = client.post(
        "/api/app/webhook",
        json={
            "action": "created",
            "sender": {"id": 1},
            "installation": {"id": 1},
            "repositories": [{"full_name": "owner/name", "name": "name"}],
        },
        headers={"X-GitHub-Event": "installation"},
    )
    logging.info(response.json())
    assert response.status_code == 200


def test_webhook_delete(mock_mongodb):
    client = TestClient(app)
    response = client.post(
        "/api/app/webhook",
        json={
            "action": "deleted",
            "sender": {"id": 1},
            "installation": {"id": 1},
            "repositories": [{"full_name": "owner/name", "name": "name"}],
        },
        headers={"X-GitHub-Event": "installation"},
    )
    logging.info(response.json())
    assert response.status_code == 200


def test_webhook_add(mock_mongodb):
    client = TestClient(app)
    response = client.post(
        "/api/app/webhook",
        json={
            "action": "added",
            "sender": {"id": 1},
            "installation": {"id": 1},
            "repositories_added": [{"full_name": "owner/name", "name": "name"}],
        },
        headers={"X-GitHub-Event": "installation_repositories"},
    )
    logging.info(response.json())
    assert response.status_code == 200


def test_webhook_remove(mock_mongodb):
    client = TestClient(app)
    response = client.post(
        "/api/app/webhook",
        json={
            "action": "removed",
            "sender": {"id": 1},
            "installation": {"id": 1},
            "repositories_removed": [{"full_name": "owner/name", "name": "name"}],
        },
        headers={"X-GitHub-Event": "installation_repositories"},
    )
    logging.info(response.json())
    assert response.status_code == 200
