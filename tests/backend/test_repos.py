from fastapi.testclient import TestClient
from gfibot.collections import *
from gfibot.backend.server import app
from gfibot.backend.models import *


def test_get_repo_language(mock_mongodb):
    client = TestClient(app)
    response = client.get("/api/repos/languages")
    assert response.status_code == 200
    res = GFIResponse[List[str]].parse_obj(response.json())
    assert set(res.result) == {"Python", "C#"}


def test_get_number_of_repos(mock_mongodb):
    client = TestClient(app)

    response = client.get("/api/repos/count")
    assert response.status_code == 200
    res = GFIResponse[int].parse_obj(response.json())
    assert res.result == Repo.objects.count()

    # num by language
    response = client.get("/api/repos/count?language=Python")
    assert response.status_code == 200
    res = GFIResponse[int].parse_obj(response.json())
    assert res.result == Repo.objects(language="Python").count()


def test_get_repo_dynamics(mock_mongodb):
    client = TestClient(app)
    response = client.get("/api/repos/owner/name/dynamics")
    assert response.status_code == 200
    res = GFIResponse[RepoDynamics].parse_obj(response.json())
    assert res.result.name == "name"


# mongomock has poor support for aggregation
def test_get_repo_paged(real_mongodb):
    client = TestClient(app)
    response = client.get("/api/repos/list?start=0&limit=3")
    assert response.status_code == 200
    res = GFIPaginated[RepoDetail].parse_obj(response.json())
    assert res.result[0].name == "name"

    # test language
    response = client.get("/api/repos/list?start=0&limit=3&language=C++")
    assert response.status_code == 200
    res = GFIPaginated[RepoDetail].parse_obj(response.json())
    assert len(res.result) == 0

    # test sort
    response = client.get("/api/repos/list?start=0&limit=3&sort=-n_stars")
    assert response.status_code == 200
    res = GFIPaginated[RepoDetail].parse_obj(response.json())
    assert res.result[0].name == "name2"  # 2nd repo is the most popular

    response = client.get("/api/repos/list?start=0&limit=3&sort=-n_gfis")
    assert response.status_code == 200
    res = GFIPaginated[RepoDetail].parse_obj(response.json())
    assert res.result[0].name == "name"  # 1st repo is the most GFIS

    response = client.get("/api/repos/list?start=0&limit=3&sort=issue_close_time")
    assert response.status_code == 200
    res = GFIPaginated[RepoDetail].parse_obj(response.json())
    assert res.result[0].name == "name2"  # 2nd repo median_issue_resolve_time is lower

    response = client.get("/api/repos/list?start=0&limit=3&sort=-r_newcomer_resolved")
    assert response.status_code == 200
    res = GFIPaginated[RepoDetail].parse_obj(response.json())
    assert res.result[0].name == "name"  # 1st repo r_newcomer_resolved is higher


# mongomock doesn't support text search
def test_search_repo(real_mongodb):
    client = TestClient(app)
    # search by name
    response = client.get("/api/repos/search?query=name")
    assert response.status_code == 200
    res = GFIPaginated[RepoDetail].parse_obj(response.json())

    # search by description
    response = client.get("/api/repos/search?query=APP")
    assert response.status_code == 200
    res = GFIPaginated[RepoDetail].parse_obj(response.json())
    assert res.result[0].name == "name"
