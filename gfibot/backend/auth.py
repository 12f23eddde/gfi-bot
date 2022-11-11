from typing import Optional
import logging

from gfibot import CONFIG
from gfibot.backend.utils import mask_token

from github import Github, GithubException
from fastapi import Body, Path, Header, HTTPException


def is_auth_disabled() -> bool:
    if CONFIG.get("disable_auth"):
        logging.warning(
            "Github authentification has been disbled (GFIBOT_DISABLE_AUTH=True)."
        )
        logging.warning(
            "This is DANGEROUS and NEVER do this in production environments."
        )
        return True
    return False


def get_github_login(
    token: str,
) -> Optional[str]:
    """
    Fetch user's github login for Github
    """
    g = Github(token)
    try:
        login = g.get_user().login
        return login
    except GithubException as e:
        logging.error(
            "Error fetching user login from github: %s %s", e, mask_token(token)
        )
        return None


def has_write_access(owner: str, name: str, token: str) -> bool:
    """
    Check if {user} has write access to {owner}/{name}
    """
    if is_auth_disabled():
        return True

    g = Github(token)
    try:
        repo = g.get_repo(f"{owner}/{name}")
        if repo.permissions.push:
            return True
        return False
    except GithubException as e:
        logging.error(
            "Error fetching user permission from github: %s %s", e, mask_token(token)
        )
        return False


def check_token_params(token: str, user: str):
    """
    Check if token matches username
    """
    if is_auth_disabled():
        return
    if get_github_login(token) != user:
        raise HTTPException(403, f"Token invalid or does not match username {user}")


def check_token_headers(
    x_github_user: str = Header(),
    x_github_token: str = Header(),
):
    """
    Check token in request headers, raise 403 if no write access
    e.g. get /user/history headers: X-Github-User: <user>, X-Github-Token: <token>
    """
    if not x_github_user:
        raise HTTPException(403, "Forbidden: X-Github-User header missing")
    if not x_github_token:
        raise HTTPException(401, "Unauthorized: X-Github-Token header missing")
    if is_auth_disabled():
        return
    user = get_github_login(x_github_token)
    if get_github_login(x_github_token) != user:
        raise HTTPException(403, f"Token invalid or does not match username {user}")


def check_write_access_body(
    token: str = Body(), owner: str = Path(), name: str = Path()
):
    """
    Check token in request body, raise 401 if no write access
    """
    if not has_write_access(owner, name, token):
        raise HTTPException(401, f"You must have write access to {owner}/{name}")


def check_write_access_params(token: str, owner: str, name: str):
    """
    Check token in request params, raise 401 if no write access
    """
    if not has_write_access(owner, name, token):
        raise HTTPException(401, f"You must have write access to {owner}/{name}")


def check_write_access_headers(
    owner: str = Path(),
    name: str = Path(),
    x_github_token: str = Header(),
):
    """
    Check token in request headers, raise 401 if no write access
    e.g. post /repos/{owner}/{name}/issues headers: X-Github-Token: <token>
    """
    if not x_github_token:
        raise HTTPException(401, "Unauthorized: X-Github-Token header missing")
    if not has_write_access(owner, name, x_github_token):
        raise HTTPException(401, f"You must have write access to {owner}/{name}")
