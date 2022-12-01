# from fastapi.testclient import TestClient
# import logging

# from gfibot.collections import *
# from gfibot.backend.routes.user import UserQueryModel
# from gfibot.backend.models import *
# from gfibot.backend.background_tasks import has_write_access
# from gfibot.backend.server import app

from fastapi.testclient import TestClient
import responses

from gfibot.collections import *
from gfibot.backend.server import app
from gfibot.backend.models import *


def test_get_user_repos(mock_mongodb):
    client = TestClient(app)
    response = client.get(
        "/api/user/repos",
        headers={"X-Github-User": "owner", "X-Github-Token": "not_a_token"},
    )
    print(response.json())
    assert response.status_code == 200
    r = GFIResponse[List[UserRepo]].parse_obj(response.json())
    assert len(r.result) > 0


def test_add_repo(mock_mongodb):
    client = TestClient(app)
    response = client.post(
        "/api/user/repos/owner/name",
        headers={"X-Github-User": "owner", "X-Github-Token": "not_a_token"},
    )
    assert response.status_code == 200  # expect to succeed
    res = GFIResponse[str].parse_obj(response.json())
    assert "exists" in res.result
    response = client.post(
        "/api/user/repos/owner2/name2",
        headers={"X-Github-User": "owner2", "X-Github-Token": "not_a_token"},
    )
    print(response.json())
    assert response.status_code == 403  # expect to fail


def test_delete_repo(mock_mongodb):
    client = TestClient(app)
    response = client.delete(
        "/api/user/repos/owner/name",
        headers={"X-Github-User": "owner", "X-Github-Token": "not_a_token"},
    )
    assert response.status_code == 200  # expect to succeed
    response = client.get(
        "/api/user/repos/owner/name/config",
        headers={"X-Github-User": "owner", "X-Github-Token": "not_a_token"},
    )
    assert response.status_code == 404  # expect to fail


def test_update_config(mock_mongodb):
    client = TestClient(app)
    # get repo config
    response = client.get(
        "/api/user/repos/owner/name/config",
        headers={"X-Github-User": "owner", "X-Github-Token": "not_a_token"},
    )
    assert response.status_code == 200
    res = GFIResponse[UserRepoConfig].parse_obj(response.json())

    # edit repo config
    conf = res.result
    conf.auto_label = not conf.auto_label
    conf.badge_prefix = "new_prefix"
    response = client.put(
        "/api/user/repos/owner/name/config",
        headers={"X-Github-User": "owner", "X-Github-Token": "not_a_token"},
        json=conf.dict(),
    )
    print(response.json())
    assert response.status_code == 200

    # check if config was updated
    response = client.get(
        "/api/user/repos/owner/name/config",
        headers={"X-Github-User": "owner", "X-Github-Token": "not_a_token"},
    )
    assert response.status_code == 200
    res = GFIResponse[UserRepoConfig].parse_obj(response.json())
    assert res.result.auto_label == conf.auto_label
    assert res.result.badge_prefix == conf.badge_prefix


def test_force_repo_update(mock_mongodb):
    client = TestClient(app)
    response = client.put(
        "/api/user/repos/owner/name/actions/update",
        headers={"X-Github-User": "owner", "X-Github-Token": "not_a_token"},
    )
    assert response.status_code == 200


def test_force_repo_label(mock_mongodb):
    client = TestClient(app)
    response = client.put(
        "/api/user/repos/owner/name/actions/label",
        headers={"X-Github-User": "owner", "X-Github-Token": "not_a_token"},
    )
    assert response.status_code == 200  # expect to succeed


def test_get_queries(mock_mongodb):
    client = TestClient(app)
    response = client.get(
        "/api/user/searches",
        headers={"X-Github-User": "owner", "X-Github-Token": "not_a_token"},
    )
    assert response.status_code == 200
    res = GFIResponse[List[str]].parse_obj(response.json())
    assert len(res.result) > 0


def test_get_delete_history(mock_mongodb):
    client = TestClient(app)
    response = client.get(
        "/api/user/history",
        headers={"X-Github-User": "owner", "X-Github-Token": "not_a_token"},
    )
    print(response.json())
    assert response.status_code == 200
    res = GFIResponse[List[UserSearchedRepo]].parse_obj(response.json())
    assert len(res.result) > 0
    first = res.result[0]
    response = client.delete(
        "/api/user/history",
        params={"id": first.id},
        headers={"X-Github-User": "owner", "X-Github-Token": "not_a_token"},
    )
    assert response.status_code == 200
    response = client.get(
        "/api/user/history",
        headers={"X-Github-User": "owner", "X-Github-Token": "not_a_token"},
    )
    print(response.json())
    assert response.status_code == 200
    res = GFIResponse[List[UserSearchedRepo]].parse_obj(response.json())
    assert len(res.result) == 0


# def test_has_write_access(mock_mongodb):
#     assert has_write_access(owner="owner", name="name", user="chuchu")
#     assert not has_write_access(owner="owner", name="name", user="nobody")


# # # routes should be moved somewhere else
# # def test_get_github_oauth_url(mock_mongodb):
# #     pass


# # def test_get_github_callback(mock_mongodb):
# #     pass


# def test_get_user_queries(mock_mongodb):
#     client = TestClient(app)
#     response = client.get(
#         "/api/user/queries", params={"user": "chuchu", "filter": "gfis"}
#     )
#     logging.info(response.json())
#     assert response.status_code == 200
#     res = GFIResponse[UserQueryModel].parse_obj(response.json())
#     assert res.result.nums == 1


# def test_delete_user_queries(mock_mongodb):
#     client = TestClient(app)
#     response = client.delete(
#         "/api/user/queries", params={"user": "nobody", "name": "name", "owner": "owner"}
#     )
#     logging.info(response.json())
#     assert response.status_code == 403  # expect to fail
#     response = client.delete(
#         "/api/user/queries", params={"user": "chuchu", "name": "name", "owner": "owner"}
#     )
#     logging.info(response.json())
#     assert response.status_code == 200
#     # nums should be 0
#     response = client.get("/api/user/queries", params={"user": "chuchu"})
#     logging.info(response.json())
#     assert response.status_code == 200
#     res = GFIResponse[UserQueryModel].parse_obj(response.json())
#     assert res.result.nums == 0


# def test_get_repo_config(mock_mongodb):
#     client = TestClient(app)
#     response = client.get(
#         "/api/user/queries/config", params={"name": "name", "owner": "owner"}
#     )
#     logging.info(response.json())
#     assert response.status_code == 200
#     res = GFIResponse[RepoConfig].parse_obj(response.json())
#     assert res.result.gfi_threshold == 0.5


# def test_update_repo_config(mock_mongodb):
#     client = TestClient(app)
#     response = client.put(
#         "/api/user/queries/config",
#         json={
#             "newcomer_threshold": 5,
#             "gfi_threshold": 0.5,
#             "need_comment": True,
#             "issue_tag": "gfi",
#         },
#         params={"name": "name", "owner": "owner", "user": "chuchu"},
#     )
#     logging.info(response.json())
#     assert response.status_code == 200


# def test_get_user_search(mock_mongodb):
#     client = TestClient(app)
#     response = client.get("/api/user/searches", params={"user": "nobody"})
#     logging.info(response.json())
#     assert response.status_code == 200
#     res = GFIResponse[List[UserSearchedRepo]].parse_obj(response.json())
#     assert len(res.result) == 3


# def test_delete_user_search(mock_mongodb):
#     client = TestClient(app)
#     response = client.delete("/api/user/searches", params={"user": "nobody", "id": 1})
#     logging.info(response.json())
#     assert response.status_code == 200
#     response = client.get("/api/user/searches", params={"user": "nobody"})
#     logging.info(response.json())
#     res = GFIResponse[List[UserSearchedRepo]].parse_obj(response.json())
#     assert len(res.result) == 2
