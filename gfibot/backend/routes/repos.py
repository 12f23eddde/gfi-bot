from typing import List, Optional, Any, Dict
from datetime import datetime

from fastapi import APIRouter, HTTPException, Response, Depends


from gfibot.collections import *
from gfibot.backend.models import (
    GFIResponse,
    GFIPaginated,
    RepoQuery,
    RepoBrief,
    RepoDetail,
    RepoDynamics,
    RepoSort,
)

from gfibot.backend.utils import (
    get_gfi_threshold,
    get_newcomer_threshold,
)

api = APIRouter()
logger = logging.getLogger(__name__)


@api.get("/languages", response_model=GFIResponse[List[str]])
def get_repo_languages():
    """
    Get all languages
    """
    return GFIResponse(
        result=list(Repo.objects.filter(language__ne=None).distinct("language"))
    )


@api.get("/count", response_model=GFIResponse[int])
def get_repo_count(language: Optional[List[str]] = None):
    """
    Get number of repositories
    """
    if language:
        return GFIResponse(result=Repo.objects.filter(language__in=language).count())
    return GFIResponse(result=Repo.objects.count())


@api.get("/list", response_model=GFIPaginated[RepoDetail])
def get_repo_detail_paginated(
    start: int = 0,
    limit: int = 10,
    language: Optional[List[str]] = None,
    sort: Optional[RepoSort] = None,
):
    """
    Get detailed info of repository (paginated)
    :param start: start index
    :param limit: max number of items to return
    :param language: filter by languages
    :param sort: sort by
    """
    rank_threshold = get_newcomer_threshold(
        None, None
    )  # newcomer_thres used for ranking repos

    q = TrainingSummary.objects(threshold=rank_threshold).filter(
        owner__ne=""
    )  # "": global perf metrics

    assert rank_threshold >= 1, "No training summary found"

    if language:
        # TODO: add language field to TrainingSummary (current code might be slow)
        lang_repos = list(
            Repo.objects().filter(language__in=language).only("name", "owner")
        )
        lang_names = [repo.name for repo in lang_repos]
        lang_owners = [repo.owner for repo in lang_repos]
        q = q.filter(name__in=lang_names, owner__in=lang_owners)

    if not sort:
        sort = RepoSort.ALPHABETICAL_ASC
    q = q.order_by(sort.value)

    count = q.count()

    print(count, rank_threshold)

    q = q.skip(start).limit(limit)  # paginate
    q = q.aggregate(
        # inner join with Repo on (name, owner)
        {
            "$lookup": {
                "from": "repo",
                "localField": "name",
                "foreignField": "name",
                "as": "repo",
            }
        },
        {"$unwind": "$repo"},
        {
            "$match": {
                "$expr": {"$eq": ["$repo.owner", "$owner"]},
            }
        },
        {"$project": {"res": {"$mergeObjects": ["$$ROOT", "$repo"]}}},
        {"$replaceRoot": {"newRoot": "$res"}},
        {"$unset": "repo"},
        {
            "$set": {
                "issues_train": {"$size": "$issues_train"},
                "issues_test": {"$size": "$issues_test"},
            }
        },
        {"$project": {k: 1 for k in RepoDetail.__fields__}},
    )
    repos_list = list(q)

    return GFIPaginated(
        result=repos_list,
        total=count,
        current=start,
        size=len(repos_list),
    )


@api.get("/search", response_model=GFIPaginated[RepoDetail])
def search_repo_detail_paginated(
    query: str,
    start: int = 0,
    limit: int = 10,
):
    """
    Search detailed info of repository (paginated)
    :param start: start index
    :param limit: max number of items to return
    :param query: search query
    """
    rank_threshold = get_newcomer_threshold(
        None, None
    )  # newcomer_thres used for ranking repos

    q = Repo.objects.search_text(query).order_by("$text_score")
    count = q.count()

    q = q.skip(start).limit(limit)  # paginate
    q = q.aggregate(
        # inner join with TrainingSummary on (name, owner)
        {
            "$lookup": {
                "from": "training_summary",
                "localField": "name",
                "foreignField": "name",
                "as": "training_summary",
            }
        },
        {"$unwind": "$training_summary"},
        {
            "$match": {
                "$expr": {
                    "$and": [
                        {"$eq": ["$training_summary.owner", "$owner"]},
                        {"$eq": ["$training_summary.threshold", rank_threshold]},
                    ]
                },
            }
        },
        {"$project": {"res": {"$mergeObjects": ["$$ROOT", "$training_summary"]}}},
        {"$replaceRoot": {"newRoot": "$res"}},
        {"$unset": "training_summary"},
        {
            "$set": {
                "issues_train": {"$size": "$issues_train"},
                "issues_test": {"$size": "$issues_test"},
            }
        },
        {"$project": {k: 1 for k in RepoDetail.__fields__}},
    )
    repos_list = list(q)

    for repo in repos_list:
        s = GfibotSearch(
            name=repo.name, owner=repo.owner, query=query, searched_at=datetime.now()
        )
        s.save()

    return GFIPaginated(
        result=repos_list,
        total=count,
        current=start,
        size=len(repos_list),
    )


@api.get("/dynamics", response_model=GFIResponse[RepoDynamics])
def get_repo_dynamics(
    name: str,
    owner: str,
):
    repo = Repo.objects(name=name, owner=owner).only(*RepoDynamics.__fields__).first()
    if not repo:
        raise HTTPException(404, "Repository not found")
    return GFIResponse(result=repo.to_mongo())


@api.get("/{owner}/{name}/dynamics", response_model=GFIResponse[RepoDynamics])
def get_repo_dynamics_patharg(name: str, owner: str):
    return get_repo_dynamics(name, owner)
