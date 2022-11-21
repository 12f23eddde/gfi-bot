from typing import List, Optional, Any, Dict, Final
from urllib.parse import urlencode, parse_qsl
import json

from fastapi import APIRouter, HTTPException, Header
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, HttpUrl
import requests
from github import GithubIntegration

from gfibot import CONFIG
from gfibot.collections import *
from gfibot.backend.models import (
    GFIResponse,
    RepoQuery,
    GitHubRepo,
    GitHubAppWebhookResponse,
    GitHubUserInfo,
)
from gfibot.backend.background_tasks import add_repo_to_gfibot, remove_repo_from_gfibot

api = APIRouter()
logger = logging.getLogger(__name__)


GITHUB_LOGIN_URL: Final = "https://github.com/login/oauth/authorize"
GITHUB_OAUTH_URL: Final = "https://github.com/login/oauth/access_token"
GITHUB_USER_API_URL: Final = "https://api.github.com/user"


@api.get("/login", response_model=GFIResponse[HttpUrl])
def get_oauth_app_login_url():
    """
    Get Github OAuth App login URL
    """
    oauth_client_id = CONFIG["github_app"]["client_id"]
    if not oauth_client_id:
        raise HTTPException(
            status_code=500, detail="Github app client id not configured"
        )
    return GFIResponse(result=f"{GITHUB_LOGIN_URL}?client_id={oauth_client_id}")


@api.get("/callback", response_class=RedirectResponse)
def redirect_from_github(code: str):
    """
    Github OAuth callback
    """
    client_id = CONFIG["github_app"]["client_id"]
    client_secret = CONFIG["github_app"]["client_secret"]

    if not client_id or not client_secret:
        raise HTTPException(
            status_code=500, detail="Github app client id or secret not configured"
        )

    # auth github app
    r = requests.post(
        GITHUB_OAUTH_URL,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
        },
    )
    if r.status_code != 200 or not "access_token" in r.text:
        logger.error(
            f"error getting access token via oauth: code={code} response={r.text}"
        )
        raise HTTPException(
            status_code=500, detail="Failed to obtain access token via oauth"
        )
    access_token = r.json()["access_token"]

    # get user info
    r = requests.get(
        GITHUB_USER_API_URL, headers={"Authorization": f"token {access_token}"}
    )
    if r.status_code != 200:
        logger.error(
            f"error getting user info via oauth: code={code} response={r.text}"
        )
        raise HTTPException(
            status_code=500, detail="Failed to obtain user info via oauth"
        )
    user_res = GitHubUserInfo(**json.loads(r.text))

    update_obj = {
        "login": user_res.login,
        "name": user_res.name,
        "avatar_url": user_res.avatar_url,
        "email": user_res.email,
    }

    update_obj["oauth_token"] = access_token

    GfibotUser.objects(login=user_res.login).upsert_one(**update_obj)

    logger.info(f"user {user_res.login} logged in via oauth")

    params = {
        "github_login": user_res.login,
        "github_name": user_res.name,
        "github_id": user_res.id,
        "github_token": access_token,
        "github_avatar_url": user_res.avatar_url,
    }

    return RedirectResponse(url="/login/redirect?" + urlencode(params))
