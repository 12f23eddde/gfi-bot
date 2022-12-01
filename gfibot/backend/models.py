from typing import List, Tuple, TypeVar, Generic, Dict, Any, Optional, Final, Literal
from enum import Enum
from datetime import datetime

import orjson
from pydantic import BaseModel
from pydantic.generics import GenericModel

T = TypeVar("T")


class GFIResponse(GenericModel, Generic[T]):
    code: int = 200
    result: T


class GFIPaginated(GFIResponse[List[T]], Generic[T]):
    total: int
    current: int
    size: int


class RepoQuery(BaseModel):
    owner: str
    name: str


### Repo Models ###


class RepoBrief(BaseModel):
    name: str
    owner: str
    description: Optional[str]
    language: Optional[str]
    topics: List[str]


class RepoDetail(BaseModel):
    name: str
    owner: str
    description: Optional[str]
    language: Optional[str]
    topics: List[str]

    # repository metrics
    r_newcomer_resolved: float
    n_stars: int
    n_gfis: int
    issue_close_time: float

    # per-repo performance
    accuracy: Optional[float]
    auc: Optional[float]
    last_updated: datetime


class MonthlyCount(BaseModel):
    month: datetime
    count: int


class RepoDynamics(BaseModel):
    name: str
    owner: str
    # repository dynamics
    monthly_commits: List[MonthlyCount]
    monthly_issues: List[MonthlyCount]
    monthly_pulls: List[MonthlyCount]


class RepoSort(Enum):
    ALPHABETICAL_ASC = "name"
    ALPHABETICAL_DESC = "-name"
    STARS_ASC = "n_stars"
    STARS_DESC = "-n_stars"
    GFIS_ASC = "n_gfis"
    GFIS_DESC = "-n_gfis"
    ISSUE_CLOSE_TIME_ASC = "issue_close_time"
    ISSUE_CLOSE_TIME_DESC = "-issue_close_time"
    NEWCOMER_RESOLVE_RATE_ASC = "r_newcomer_resolved"
    NEWCOMER_RESOLVE_RATE_DESC = "-r_newcomer_resolved"


class UserSearchedRepo(BaseModel):
    id: str
    name: str
    owner: str
    query: str
    searched_at: datetime


### GFI Config Models ###


# class UpdateConfig(BaseModel):
#     task_id: str
#     interval: int
#     begin_time: datetime
#
#
# class RepoConfig(BaseModel):
#     newcomer_threshold: int
#     gfi_threshold: float
#     need_comment: bool
#     issue_tag: str
#
#
# class Config(BaseModel):
#     update_config: UpdateConfig
#     repo_config: RepoConfig


class UserRepo(BaseModel):
    owner: str
    name: str
    state: Literal["done", "collecting", "training", "error"]


class UserRepoConfig(BaseModel):
    """Config for a repo"""

    update_cron: str
    newcomer_threshold: int
    gfi_threshold: float
    need_comment: bool
    auto_label: bool
    issue_label: str
    badge_prefix: str


### GFI Data Models ###


class GFIBrief(BaseModel):
    name: str
    owner: str
    number: int
    threshold: float
    probability: float
    last_updated: datetime
    created_at: datetime
    closed_at: Optional[datetime]
    state: Optional[str] = None
    title: Optional[str] = None
    labels: Optional[List[str]] = None


class GFISort(Enum):
    PROBABILITY_ASC = "probability"
    PROBABILITY_DESC = "-probability"
    CREATED_AT_ASC = "created_at"
    CREATED_AT_DESC = "-created_at"


class TrainingResult(BaseModel):
    owner: str
    name: str
    issues_train: int
    issues_test: int
    n_resolved_issues: int
    n_newcomer_resolved: int
    last_updated: datetime

    auc: Optional[float]
    accuracy: Optional[float]
    precision: Optional[float]
    recall: Optional[float]
    f1: Optional[float]


FeatureImportance = Dict[str, float]

GFIDataset = Dict[str, Any]


### GitHub API Data Models ###


class GitHubRepo(BaseModel):
    full_name: str
    name: str

    @property
    def owner(self) -> str:
        return self.full_name.split("/")[0]


class GitHubAppWebhookResponse(BaseModel):
    sender: Dict[str, Any]
    installation: Dict[str, Any]
    action: str
    issue: Optional[Dict[str, Any]]
    repository: Optional[GitHubRepo]
    repositories: Optional[List[GitHubRepo]]
    repositories_added: Optional[List[GitHubRepo]]
    repositories_removed: Optional[List[GitHubRepo]]


class GitHubUserInfo(BaseModel):
    id: str
    login: str
    name: str
    avatar_url: Optional[str] = None
    email: Optional[str] = None
    url: Optional[str] = None
    twitter_username: Optional[str] = None
