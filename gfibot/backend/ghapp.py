import logging
from typing import Optional
from datetime import datetime, timedelta

import jwt
from github import Github, GithubException


def get_jwt_token(
    app_id: int,
    app_private_key: Optional[str],
    app_private_key_path: Optional[str],
) -> str:
    """Generate JWT token for GitHub App"""
    if app_private_key_path:
        with open(app_private_key_path, "r") as key_file:
            app_private_key = key_file.read()
    if not app_private_key:
        raise ValueError("No private key provided")
    payload = {
        "iat": datetime.utcnow() - timedelta(minutes=1),
        "exp": datetime.utcnow() + timedelta(minutes=9),
        "iss": app_id,
    }
    encoded = jwt.encode(
        payload,
        app_private_key,
        algorithm="RS256",
        headers={"typ": "JWT", "alg": "RS256"},
    )
    return encoded


class GfibotGitHubApp(object):
    def __init__(
        self,
        token: Optional[str] = None,
        app_id: Optional[int] = None,
        app_private_key: Optional[str] = None,
        app_private_key_path: Optional[str] = None,
    ):
        if not token:
            self.app_id = app_id
            self.app_private_key = app_private_key
            self.app_private_key_path = app_private_key_path
            self.gh = Github(
                jwt=get_jwt_token(
                    app_id=self.app_id,
                    app_private_key=self.app_private_key,
                    app_private_key_path=self.app_private_key_path,
                )
            )
        else:
            if not self.token:
                raise ValueError("Must provide token or app_id and app_private_key")
            self.gh = Github(jwt=self.token)

    def request_wrapper(self, method, *args, **kwargs):
        """Wrapper for GitHub API requests"""
        try:
            return method(*args, **kwargs)
        except GithubException as exc:
            logging.error(exc)
            if exc.status == 401:
                if self.app_id:
                    # refresh token and try again
                    self.gh = Github(
                        jwt=get_jwt_token(
                            app_id=self.app_id,
                            app_private_key=self.app_private_key,
                            app_private_key_path=self.app_private_key_path,
                        )
                    )

                return method(*args, **kwargs)
            else:
                raise exc

    def is_issue_labelled(self, owner: str, name: str, number: str, label: str) -> bool:
        """Check if issue is labelled with label"""
        issue = self.request_wrapper(
            self.gh.get_repo(f"{owner}/{name}").get_issue, number
        )
        return any([x.name == label for x in issue.labels])

    def add_issue_comment(self, owner: str, name: str, number: str, comment: str):
        """Add a comment to an issue"""
        repo = self.gh.get_repo(f"{owner}/{name}")
        issue = repo.get_issue(number)
        self.request_wrapper(issue.create_comment, comment)

    def add_issue_label(self, owner: str, name: str, number: str, label: str):
        """Add a label to an issue"""
        repo = self.gh.get_repo(f"{owner}/{name}")
        issue = repo.get_issue(number)
        self.request_wrapper(issue.add_to_labels, label)
