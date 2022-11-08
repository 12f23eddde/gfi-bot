from gfibot.collections import *
from fastapi.testclient import TestClient
from gfibot.backend.server import app
from gfibot.backend.models import *


def test_get_number_of_issues(mock_mongodb):
    client = TestClient(app)
    response = client.get("/api/issues/count")
    logging.info(response.json())
    assert response.status_code == 200
    res = GFIResponse[int].parse_obj(response.json())
    assert res.result == OpenIssue.objects.count()


def test_get_number_of_issues_gfis(mock_mongodb):
    client = TestClient(app)
    response = client.get("/api/issues/count", params={"option": "gfis"})
    logging.info(response.json())
    assert response.status_code == 200
    res = GFIResponse[int].parse_obj(response.json())
    assert res.result < OpenIssue.objects.count()


def test_get_repo_gfis(mock_mongodb):
    client = TestClient(app)
    response = client.get("/api/issues/owner/name", params={"start": 0, "limit": 10})
    logging.info(response.json())
    assert response.status_code == 200
    res = GFIPaginated[GFIBrief].parse_obj(response.json())
    assert res.size == len(res.items)
    assert res.items[0].name == "name"

    response = client.get(
        "/api/issues", params={"name": "name", "owner": "owner", "option": "gfis"}
    )
    logging.info(response.json())
    assert response.status_code == 200
    res2 = GFIPaginated[GFIBrief].parse_obj(response.json())
    assert res2.size < res.size
