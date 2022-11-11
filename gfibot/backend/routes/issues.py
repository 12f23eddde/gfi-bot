from typing import List, Optional, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime

from gfibot.collections import *
from gfibot.backend.models import GFIResponse, GFIBrief, GFIPaginated, GFISort
from gfibot.backend.utils import get_gfi_threshold, get_newcomer_threshold

api = APIRouter()
logger = logging.getLogger(__name__)


@api.get("/count", response_model=GFIResponse[int])
def get_issues_count(
    owner: Optional[str] = None,
    name: Optional[str] = None,
    option: Optional[Literal["gfis"]] = None,
):
    """
    Get number of open issues
    """
    newcomer_thres = get_newcomer_threshold(owner, name)
    selector = Q(state="open", threshold=newcomer_thres)
    if option == "gfis":
        gfi_thres = get_gfi_threshold(owner, name)
        selector = selector & Q(probability__gte=gfi_thres)
    if owner and name:
        selector = selector & Q(name=name, owner=owner)
    return GFIResponse(result=Prediction.objects(selector).count())


@api.get("", response_model=GFIPaginated[GFIBrief])
def get_issues(
    owner: str,
    name: str,
    start: int = 0,
    limit: int = 10,
    sort: Optional[GFISort] = None,
    option: Optional[Literal["gfis"]] = None,
):
    """
    Get open issues of a repository
    """
    newcomer_thres = get_newcomer_threshold(name=name, owner=owner)

    if not sort:
        sort = GFISort.PROBABILITY_DESC

    selector = Q(name=name, owner=owner) & Q(threshold=newcomer_thres) & Q(state="open")
    if option == "gfis":
        gfi_thres = get_gfi_threshold(owner, name)
        selector = selector & Q(probability__gte=gfi_thres)

    gfis = (
        Prediction.objects(selector)
        .only(
            "name",
            "owner",
            "number",
            "threshold",
            "probability",
            "last_updated",
            "created_at",
        )
        .order_by(
            sort.value, "-number"  # probability may be the same -> repeated issue
        )
    )

    count = gfis.count()

    gfis = gfis.skip(start).limit(limit)

    gfis = list(gfis)

    # inner join with RepoIssue on name, owner, number
    repo_issues = RepoIssue.objects(
        Q(name=name) & Q(owner=owner) & Q(number__in=[gfi.number for gfi in gfis])
    )

    repo_issues_dict = {
        (repo_issue.name, repo_issue.owner, repo_issue.number): repo_issue.to_mongo()
        for repo_issue in repo_issues
    }

    gfis_full = [
        GFIBrief(
            **repo_issues_dict[(gfi.name, gfi.owner, gfi.number)],
            threshold=gfi.threshold,
            probability=gfi.probability,
            last_updated=gfi.last_updated,
        )
        for gfi in gfis
    ]

    return GFIPaginated(
        result=gfis_full,
        total=count,
        current=start,
        size=len(gfis),
    )


@api.get("/{owner}/{name}/count", response_model=GFIResponse[int])
def get_issues_count_path_params(
    owner: str, name: str, option: Optional[Literal["gfis"]] = None
):
    return get_issues_count(owner, name, option)


@api.get("/{owner}/{name}", response_model=GFIPaginated[GFIBrief])
def get_issues_path_params(
    owner: str,
    name: str,
    start: int = 10,
    limit: int = 10,
    sort: Optional[GFISort] = None,
    option: Optional[Literal["gfis"]] = None,
):
    return get_issues(owner, name, start, limit, sort, option)
