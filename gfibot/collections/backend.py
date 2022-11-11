from tokenize import String
from typing import List
from datetime import datetime
from mongoengine import *


# class GfibotToken(Document):
#     """Github App Tokens"""

#     app_name = StringField(required=True)
#     client_id = StringField(required=True)
#     client_secret = StringField(required=True)
#     token = StringField(required=True)

#     meta = {
#         "indexes": [
#             {"fields": ["client_id"], "unique": True},
#             {"fields": ["app_name"], "unique": True},
#         ]
#     }


class GfibotInstallation(Document):
    """
    Github App Installation
    """

    installation_id = IntField(required=True, unique=True)
    token = StringField(required=True)
    expires_at = DateTimeField(required=True)
    login = StringField(required=True)

    meta = {
        "indexes": [
            {"fields": ["installation_id"], "unique": True},
            "#login",
        ]
    }


class GfibotRepo(Document):
    """Repos added to Gfibot"""

    class GfibotRepoConfig(EmbeddedDocument):
        """Config for a repo"""

        update_cron = StringField(required=True, default="0 0 * * *")
        newcomer_threshold: int = IntField(
            required=True, min_value=0, max_value=5, default=5
        )
        gfi_threshold: float = FloatField(
            required=True, min_value=0.0, max_value=1, default=0.5
        )
        need_comment: bool = BooleanField(required=True, default=True)
        auto_label: bool = BooleanField(required=True, default=False)
        issue_label: str = StringField(required=True, default="good first issue")
        badge_prefix: str = StringField(
            required=True, default="recommended good first issues"
        )

    name: str = StringField(required=True)
    owner: str = StringField(required=True)
    state: str = StringField(
        required=True, choices=["done", "collecting", "training", "error"]
    )

    # login of the user who added the repo
    added_by: str = StringField(required=False)
    installation_id: int = IntField(required=False)
    config: GfibotRepoConfig = EmbeddedDocumentField(GfibotRepoConfig)
    _added_at: datetime = DateTimeField(required=True, default=datetime.utcnow)
    _updated_at: datetime = DateTimeField(required=True, default=datetime.utcnow)


class GfibotUser(Document):
    """Registered Users"""

    login: str = StringField(required=True)
    name: str = StringField(required=True)
    oauth_token: str = StringField(required=False)
    email: str = StringField(required=False)
    avatar_url: str = StringField(required=False)
    meta = {
        "indexes": [
            {"fields": ["login"], "unique": True},
        ]
    }


class GfibotSearch(Document):
    login: str = StringField(required=True)
    name: str = StringField(required=True)
    owner: str = StringField(required=True)
    query: str = StringField(required=True)
    searched_at: datetime = DateTimeField(required=True, default=datetime.utcnow)

    meta = {
        "indexes": [
            "#query",
            "-searched_at",
        ]
    }


# class GithubTokens(Document):
#     """GitHub tokens for GitHub App"""

#     app_name: str = StringField(
#         required=True, choices=["gfibot-githubapp", "gfibot-webapp"]
#     )
#     client_id: str = StringField(required=True)
#     client_secret: str = StringField(required=True)

#     meta = {
#         "indexes": [
#             {"fields": ["client_id"], "unique": True},
#             {"fields": ["#app_name"], "unique": True},
#         ]
#     }


# class GfiUsers(Document):
#     """User statictics for GFI-Bot Web App Users"""

#     github_id: int = IntField(required=True)
#     github_access_token: str = StringField(required=False)
#     github_app_token: str = StringField(required=False)
#     github_login: str = StringField(required=True)
#     github_name: str = StringField(required=True)

#     github_avatar_url: str = StringField(required=False)
#     github_url: str = StringField(required=False)
#     github_email: str = StringField(required=False)
#     twitter_user_name = StringField(required=False)

#     class UserQuery(EmbeddedDocument):
#         repo: str = StringField(required=True)
#         owner: str = StringField(required=True)
#         created_at: datetime = DateTimeField(required=True)
#         increment: int = IntField(required=False, min_value=0)

#     # repos added by user
#     user_queries: List[UserQuery] = EmbeddedDocumentListField(UserQuery, default=[])
#     # user's searches
#     user_searches: List[UserQuery] = EmbeddedDocumentListField(UserQuery, default=[])

#     meta = {
#         "indexes": [
#             {"fields": ["github_id"], "unique": True},
#             {"fields": ["github_login"], "unique": True},
#             {"fields": ["github_email"]},
#             {"fields": ["twitter_user_name"]},
#         ]
#     }


# class GfiQueries(Document):
#     """GFI-Bot Web App queries"""

#     name: str = StringField(required=True)
#     owner: str = StringField(required=True)

#     is_pending: bool = BooleanField(required=True)
#     is_finished: bool = BooleanField(required=True)
#     is_updating: bool = BooleanField(required=False)

#     is_github_app_repo: bool = BooleanField(required=True, default=False)
#     app_user_github_login: str = StringField(required=False)

#     _created_at: datetime = DateTimeField(required=True)
#     _finished_at: datetime = DateTimeField(required=False)

#     class GfiUpdateConfig(EmbeddedDocument):
#         task_id: str = StringField(required=True)
#         interval: int = IntField(required=True, default=24 * 3600)
#         begin_time: datetime = DateTimeField(required=False)

#     class GfiRepoConfig(EmbeddedDocument):
#         newcomer_threshold: int = IntField(
#             required=True, min_value=0, max_value=5, default=5
#         )
#         gfi_threshold: float = FloatField(
#             required=True, min_value=0.0, max_value=1, default=0.5
#         )
#         need_comment: bool = BooleanField(required=True, default=True)
#         issue_tag: str = StringField(required=True, default="good first issue")

#     update_config: GfiUpdateConfig = EmbeddedDocumentField(
#         GfiUpdateConfig, required=True
#     )

#     repo_config: GfiRepoConfig = EmbeddedDocumentField(GfiRepoConfig, required=True)

#     mata = {
#         "indexes": [
#             {"fields": ["name", "owner"], "unique": True},
#         ]
#     }


# class GfiEmail(Document):
#     """Emails for GFI-Bot backend"""

#     email: str = StringField(required=True)
#     password: str = StringField(required=True)

#     meta = {
#         "indexes": [
#             {"fields": ["email"], "unique": True},
#         ]
#     }
