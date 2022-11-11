import logging
from typing import Any, Optional, List

from fastapi import APIRouter, HTTPException, Depends, Path, Header
from pydantic import BaseModel

from gfibot.backend.models import (
    GFIResponse,
    UserRepo,
    UserRepoConfig,
    UserSearchedRepo,
)
from gfibot.collections import GfibotRepo, GfibotUser, GfibotSearch
from gfibot.backend.background_tasks import (
    add_repo_to_gfibot,
    remove_repo_from_gfibot,
    schedule_repo_update_now,
    schedule_tag_task_now,
    recommend_repo_config,
)
from gfibot.backend.auth import check_token_headers, check_write_access_headers
from gfibot.backend.ghapp import get_repo_app_token

api = APIRouter()
logger = logging.getLogger(__name__)


@api.get(
    "/repos",
    response_model=GFIResponse[List[UserRepo]],
    dependencies=[Depends(check_token_headers)],
)
def get_user_repo_list(x_github_user: str = Header()):
    """
    Get repo config
    """
    user = x_github_user
    if not user:
        raise HTTPException(403, "Check X-Github-User header")
    repos = list(GfibotRepo.objects(added_by=user).only(*UserRepo.__fields__))
    return GFIResponse(result=repos)


@api.post(
    "/repos/{owner}/{name}",
    response_model=GFIResponse[str],
    dependencies=[Depends(check_write_access_headers)],
)
def add_repo(owner: str, name: str, x_github_user: str = Header()):
    """
    Add repository to GFI-Bot
    """
    user = x_github_user
    gfi_repo: Optional[GfibotRepo] = GfibotRepo.objects(name=name, owner=owner).first()
    if not gfi_repo:
        add_repo_to_gfibot(owner=owner, name=name, user=user)
        return GFIResponse(result="Repository added")
    elif gfi_repo.state == "done":
        return GFIResponse(result="Repository already exists")
    else:
        return GFIResponse(result="Repository is being processed by GFI-Bot")


@api.delete(
    "/repos/{owner}/{name}",
    response_model=GFIResponse[str],
    dependencies=[Depends(check_write_access_headers)],
)
def delete_user_repo(owner: str, name: str, x_github_user: str = Header()):
    """
    Deletes repository from GFI-Bot
    """
    user = x_github_user
    gfi_repo: Optional[GfibotRepo] = GfibotRepo.objects(name=name, owner=owner).first()
    if not gfi_repo:
        raise HTTPException(404, f"Repository {owner}/{name} does not exist")
    remove_repo_from_gfibot(owner=owner, name=name, user=user)
    return GFIResponse(result=f"Repository {owner}/{name} removed from GFI-Bot")


@api.get(
    "/repos/{owner}/{name}/config",
    response_model=GFIResponse[UserRepoConfig],
    dependencies=[Depends(check_write_access_headers)],
)
def get_user_repo_config(owner: str, name: str):
    """
    Get user repository config
    """
    gfi_repo: Optional[GfibotRepo] = GfibotRepo.objects(name=name, owner=owner).first()
    if not gfi_repo:
        raise HTTPException(404, f"Repository {owner}/{name} does not exist")
    return GFIResponse(result=gfi_repo.config)


@api.get(
    "/repos/{owner}/{name}/config/recommended",
    response_model=GFIResponse[UserRepoConfig],
    dependencies=[Depends(check_write_access_headers)],
)
def recommened_user_repo_config(
    owner: str,
    name: str,
    newcomer_percentage: Optional[int] = None,
    gfi_percentage: Optional[int] = None,
):
    """
    Get recommended user repository config
    """
    rec = recommend_repo_config(
        owner=owner,
        name=name,
        newcomer_percentage=newcomer_percentage,
        gfi_percentage=gfi_percentage,
    )
    return GFIResponse(result=rec)


@api.put(
    "/repos/{owner}/{name}/config",
    response_model=GFIResponse[str],
    dependencies=[Depends(check_write_access_headers)],
)
def set_user_repo_config(owner: str, name: str, config: UserRepoConfig):
    """
    Set user repository config
    """
    gfi_repo: Optional[GfibotRepo] = GfibotRepo.objects(name=name, owner=owner).first()
    if not gfi_repo:
        raise HTTPException(404, f"Repository {owner}/{name} does not exist")
    gfi_repo.update(config=config)
    gfi_repo.save()
    return GFIResponse(result=f"Repository {owner}/{name}'s config has been updated")


@api.put(
    "/repos/{owner}/{name}/actions/update",
    response_model=GFIResponse[str],
    dependencies=[Depends(check_write_access_headers)],
)
def force_update_repo(owner: str, name: str, x_github_token: str = Header()):
    """
    Force repository update
    """
    token = x_github_token
    schedule_repo_update_now(owner, name, token)
    return GFIResponse(result=f"Repository {owner}/{name} update job scheduled")


@api.put(
    "/repos/{owner}/{name}/actions/label",
    response_model=GFIResponse[str],
    dependencies=[Depends(check_write_access_headers)],
)
def force_label_issues(owner: str, name: str):
    """
    Force label issues
    """
    token = get_repo_app_token(owner, name)
    if not token:
        raise HTTPException(403, "Github App not installed")
    schedule_tag_task_now(owner, name, token)
    return GFIResponse(result=f"Repository {owner}/{name} label job scheduled")


@api.get(
    "/searches",
    response_model=GFIResponse[List[str]],
    dependencies=[Depends(check_token_headers)],
)
def get_user_search_queries(limit: int = 5, x_github_user: str = Header()):
    """
    Get user's searched queries
    """
    user = x_github_user
    if not user:
        raise HTTPException(403, "Check X-Github-User header")
    recent_queries = (
        GfibotSearch.objects(login=user)
        .order_by("-searched_at")
        .distinct(field="query")
        .only("query")
        .limit(limit)
    )
    recent_queries = [r.query for r in recent_queries]
    return GFIResponse(result=recent_queries)


@api.get(
    "/history",
    response_model=GFIResponse[List[UserSearchedRepo]],
    dependencies=[Depends(check_token_headers)],
)
def get_user_search_repos(limit: int = 10, x_github_user: str = Header()):
    """
    Get user's searched repos
    """
    user = x_github_user
    if not user:
        raise HTTPException(401, "Unauthorized: check X-Github-User header")
    recent_repos = (
        GfibotSearch.objects(login=user).order_by("-searched_at").limit(limit)
    )
    recent_repos = list(recent_repos)
    return GFIResponse(result=recent_repos)
