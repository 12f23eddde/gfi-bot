from fastapi.testclient import TestClient
from gfibot.collections import *
from gfibot.backend.server import app
from gfibot.backend.models import *


def test_get_repo_badge(mock_mongodb):
    client = TestClient(app)
    response = client.get("/api/badge?name=name&owner=owner")
    assert response.status_code == 200
    # response should be a svg file
    assert "image/svg+xml" in response.headers["Content-Type"]
    response2 = client.get("/api/badge/owner/name")
    assert response2.status_code == 200
    # response should be the same
    assert response.content == response2.content
