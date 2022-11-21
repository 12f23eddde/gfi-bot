import os

from gfibot.collections import *
from fastapi.testclient import TestClient
from gfibot.backend.server import app
from gfibot.backend.models import *


def test_get_features(mock_mongodb):
    if os.environ.get("CI"):  # skip this test in CI
        return

    client = TestClient(app)
    response = client.get("/api/model/features")
    assert response.status_code == 200
    res = GFIResponse[Dict[str, float]].parse_obj(response.json())
    print(res.json())
    assert len(res.result) > 0


def test_get_issue_dataset(mock_mongodb):
    client = TestClient(app)
    response = client.get(
        "/api/model/dataset", params={"name": "name", "owner": "owner", "number": 5}
    )
    assert response.status_code == 200
    res = GFIResponse.parse_obj(response.json())
    print(res.json())
    assert res.result is not None


def test_get_performance(mock_mongodb):
    client = TestClient(app)
    response = client.get("/api/model/performance")
    assert response.status_code == 200
    res = GFIResponse[TrainingResult].parse_obj(response.json())
    print(res.json())

    response = client.get(
        "/api/model/performance", params={"name": "name", "owner": "owner"}
    )
    assert response.status_code == 200
    res2 = GFIResponse[TrainingResult].parse_obj(response.json())
    print(res2.json())
    assert res2.result != res.result
