import logging

from pydantic import HttpUrl
from fastapi.testclient import TestClient
import responses

from gfibot.collections import *
from gfibot.backend.server import app
from gfibot.backend.models import *

# monkey-patch github oauth api
from gfibot.backend.routes.github import requests


def test_get_github_oauth_url(mock_mongodb):
    client = TestClient(app)
    response = client.get("/api/github/login")
    logging.info(response.json())
    assert response.status_code == 200
    res = GFIResponse[HttpUrl].parse_obj(response.json())
    assert "github" in res.result


@responses.activate
def test_github_redirect(mock_mongodb):
    responses.post(
        "https://github.com/login/oauth/access_token",
        json={"access_token": "not_a_token", "scope": "repo", "token_type": "bearer"},
        status=200,
    )
    responses.get(
        "https://api.github.com/user",
        json={
            "login": "chuchu",
            "id": 1,
            "name": "chuchu",
            "email": "",
            "avatar_url": "https://avatars.githubusercontent.com/u/1?v=4",
            "url": "https://api.github.com/users/chuchu",
        },
        status=200,
    )

    client = TestClient(app)
    response = client.get(
        "/api/github/callback",
        params={"code": "this_is_not_a_code"},
        allow_redirects=False,
    )
    # should be a valid redirect
    assert response.status_code in [301, 302, 303, 307, 308]
    assert "chuchu" in response.headers["Location"]
