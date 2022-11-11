from typing import List, Optional, Any, Dict, Final
from urllib.parse import urlencode, parse_qsl
import os

from github import GithubIntegration, GithubException

from gfibot import CONFIG
from gfibot.collections import *
from gfibot.backend.models import (
    GitHubRepo,
)


_gfibot_gh_app: GithubIntegration = None


def get_gh_app() -> GithubIntegration:
    """
    Initialize GithubIntegration object
    """
    global _gfibot_gh_app

    if not _gfibot_gh_app:
        integration_id = CONFIG["github_app"]["app_id"]
        if not integration_id:
            raise ValueError("github app id not found in config")
        private_key = CONFIG["github_app"]["private_key"]
        if not private_key:
            raise ValueError("github app private key not found in config")
        # is it a path?
        if not "PRIVATE KEY" in private_key and os.path.exists(private_key):
            with open(private_key, "r") as f:
                logging.info(f"loading github app private key from {private_key}")
                private_key = f.read()
        _gfibot_gh_app = GithubIntegration(integration_id, private_key)

    return _gfibot_gh_app


def get_repo_installation_id(owner: str, name: str) -> Optional[int]:
    """
    Get installation id for a repository
    """
    gh_app = get_gh_app()
    repo: Optional[GfibotRepo] = GfibotRepo.objects(owner=owner, name=name).first()
    if repo and repo.installation_id:
        return repo.installation_id
    else:
        try:
            installation_id = gh_app.get_installation(owner, name).id
        except GithubException as e:
            if e.status == 404:
                return None
            else:
                raise e
        if repo:
            repo.installation_id = installation_id
            repo.save()
        return installation_id


def get_repo_app_token(
    owner: str,
    name: str,
) -> Optional[str]:
    """
    Get repo app token
    """
    installation_id = get_repo_installation_id(owner, name)
    if not installation_id:
        return None
    return get_installation_token(installation_id)


def get_installation_token(
    installation_id: int,
) -> str:
    gh_app = get_gh_app()
    installation: GfibotInstallation = GfibotInstallation.objects(
        installation_id=installation_id
    ).first()
    if not installation:
        try:
            app_auth = gh_app.get_access_token(installation_id)
        except GithubException as e:
            if e.status == 404:
                return None
            else:
                raise e
        # upsert installation
        installation = GfibotInstallation(
            installation_id=installation_id,
            token=app_auth.token,
            expires_at=app_auth.expires_at,
            login=app_auth.on_behalf_of.login,
        )
        installation.save()
    return installation.token


def create_installation(
    installation_id: int,
) -> None:
    """
    Create installation
    """
    get_installation_token(installation_id)


def delete_installation(
    installation_id: int,
) -> None:
    """
    Delete installation
    """
    installation = GfibotInstallation.objects(installation_id=installation_id).first()
    if installation:
        installation.delete()
        GfibotRepo.objects(installation_id=installation_id).update(installation_id=None)
    else:
        logging.warning(f"installation {installation_id} not found")


def add_repos_from_github_app(
    repositories: List[GitHubRepo],
    installation_id: int,
) -> List[str]:
    """
    Add repositories to github app
    returns: failed repos
    """
    repos_failed = []
    for repo in repositories:
        owner, name = repo.full_name.split("/")
        record: Optional[GfibotRepo] = GfibotRepo.objects(
            owner=owner, name=name
        ).first()
        if not record:
            repos_failed.append(repo.full_name)
            logging.warning(f"failed to add repo {owner}/{name} to gfibot: Not Found")
        else:
            logging.info(f"adding repo {owner}/{name} to github app")
            record.installation_id = installation_id
            record.save()
    return repos_failed


def delete_repos_from_github_app(repositories: List[GitHubRepo]) -> List[str]:
    """
    Delete repositories from background tasks (returns immediately)
    returns: failed repos
    """
    repos_failed = []
    for repo in repositories:
        owner, name = repo.full_name.split("/")
        record: Optional[GfibotRepo] = GfibotRepo.objects(
            owner=owner, name=name
        ).first()
        if not record:
            repos_failed.append(repo.full_name)
            logging.warning(
                f"failed to delete repo {owner}/{name} from gfibot: Not Found"
            )
        else:
            logging.info(f"deleting repo {owner}/{name} from github app")
            record.installation_id = None
            record.save()
    return repos_failed
