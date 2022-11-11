from typing import List, Optional, Any, Dict, Final
from urllib.parse import urlencode, parse_qsl
import os

from fastapi import APIRouter, HTTPException, Header
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, HttpUrl

from github import GithubIntegration

from gfibot import CONFIG
from gfibot.collections import *
from gfibot.backend.models import (
    GFIResponse,
    GitHubAppWebhookResponse,
)
from gfibot.backend.ghapp import (
    add_repos_from_github_app,
    delete_repos_from_github_app,
    create_installation,
    delete_installation,
)

api = APIRouter()
logger = logging.getLogger(__name__)


@api.post("/webhook", response_model=GFIResponse[str])
def github_app_webhook_process(
    data: GitHubAppWebhookResponse, x_github_event: str = Header(default=None)
) -> GFIResponse[str]:
    """
    Process Github App webhook
    """
    event = x_github_event
    installation_id = data.installation["id"]

    failed_repos = 0
    if event == "installation":
        action = data.action
        if action == "created":
            create_installation(installation_id)
            failed_repos = add_repos_from_github_app(data.repositories, installation_id)
        elif action == "deleted":
            failed_repos = delete_repos_from_github_app(data.repositories)
            delete_installation(installation_id)
        elif action == "suspend":
            failed_repos = delete_repos_from_github_app(data.repositories)
        elif action == "unsuspend":
            failed_repos = add_repos_from_github_app(data.repositories, installation_id)
    elif event == "installation_repositories":
        action = data.action
        if action == "added":
            failed_repos = add_repos_from_github_app(
                data.repositories_added, installation_id
            )
        elif action == "removed":
            failed_repos = delete_repos_from_github_app(data.repositories_removed)
    elif event == "issues":
        action = data.action
        logger.info(
            f"{action} issue {data.issue['number']} in {data.repository.full_name}"
        )
        return GFIResponse(result="Not implemented: event=%s" % event)
    else:
        return GFIResponse(result="Not implemented: event=%s" % event)

    if failed_repos:
        raise HTTPException(
            status_code=500,
            detail=f"Operation failed: {','.join(failed_repos)}",
        )
    return GFIResponse(result=f"{failed_repos} repos processed")
