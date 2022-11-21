"""
All functions in this file are called from the backend
"""

import logging
import random
from random import randint
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import HTTPException
from apscheduler.triggers.cron import CronTrigger
import pandas as pd
from github import GithubException

from gfibot.backend.models import UserRepoConfig
from gfibot.backend.utils import get_newcomer_threshold
from gfibot.collections import *
from gfibot.backend.scheduled_tasks import (
    update_gfi_info,
    get_valid_tokens,
    label_and_comment,
)
from gfibot.backend.ghapp import (
    get_repo_app_token,
)

logger = logging.getLogger(__name__)


def add_repo_to_gfibot(owner: str, name: str, user: str) -> None:
    """
    Add repo to GFI-Bot (returns immediately)
        -> temp_worker (run once)
        -> scheduled_worker (run every day from tomorrow)
    """
    logger.info("Adding repo %s/%s on backend request", owner, name)
    user: GfibotUser = GfibotUser.objects(login=user).first()
    if not user:
        raise HTTPException(status_code=403, detail="User not found")
    # add to repo_queries
    q: Optional[GfibotRepo] = GfibotRepo.objects(name=name, owner=owner).first()
    if not q:
        logger.info("Adding repo %s/%s to GFI-Bot", owner, name)
        q = GfibotRepo(
            owner=owner,
            name=name,
            state="collecting",
            added_by=user,
        )
    else:
        logger.info(f"update new query {name}/{owner}")
        q.update(
            state="collecting",
            added_by=user,
        )

    if not q.config:  # create initial config
        q.config = GfibotRepo.GfibotRepoConfig()

    q.save()

    # obtain a valid token
    try:
        token = get_repo_app_token(owner=owner, name=name)
        if not token:
            raise GithubException("App installation not found.")
    except GithubException as e:
        logger.error("Failed to obtain installation token: %s", e)
        token = user.oauth_token

    schedule_repo_update_now(owner=owner, name=name, token=token)

    from .server import get_scheduler

    scheduler = get_scheduler()
    trigger = CronTrigger.from_crontab(q.config.update_cron)
    trigger.jitter = 1200  # flatten the curve
    if not scheduler.get_job(f"{owner}-{name}-update"):  # job not scheduled, create job
        scheduler.add_job(
            update_gfi_info,
            trigger=trigger,
            id=f"{owner}-{name}-update",
            args=[token, owner, name, False],
            replace_existing=True,
        )


def schedule_repo_update_now(
    owner: str, name: str, token: Optional[str] = None
) -> None:
    """
    Run a temporary repo update job once
    owner: Repo owner
    name: Repo name
    token: if None, random choice a token from the token pool
    send_email: if True, send email to user after update
    """
    from .server import get_scheduler

    scheduler = get_scheduler()

    job_id = f"{owner}-{name}-manual-update"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)

    if not token:
        valid_tokens = get_valid_tokens()
        if not valid_tokens:
            raise HTTPException(status_code=500, detail="No valid tokens available")
        # random choice 1 of the valid tokens
        random.seed(datetime.now())
        token = random.choice(valid_tokens)

    # run once
    scheduler.add_job(
        update_gfi_info,
        id=job_id,
        kwargs={"token": token, "owner": owner, "name": name},
    )


def schedule_tag_task_now(owner: str, name: str, token: str):
    """
    Run a temporary tag and comment job once
    owner: Repo owner
    name: Repo name
    token: if None, random choice a token from the token pool
    send_email: if True, send email to user after update
    """
    from .server import get_scheduler

    scheduler = get_scheduler()

    job_id = f"{owner}-{name}-manual-tag"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)

    # run once
    scheduler.add_job(
        label_and_comment,
        id=job_id,
        kwargs={"owner": owner, "name": name, "token": token},
    )


def remove_repo_from_gfibot(owner: str, name: str, user: str) -> None:
    """
    Remove repo from GFI-Bot
    """
    logger.info("Removing repo %s/%s on backend request", owner, name)
    q = GfibotRepo.objects(name=name, owner=owner).first()
    if not q:
        raise HTTPException(status_code=400, detail="Repo not found")
    q.delete()
    # delete job
    from .server import get_scheduler

    scheduler = get_scheduler()
    job_id = f"{owner}-{name}-update"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
    # delete TrainingSummary
    TrainingSummary.objects(owner=owner, name=name).delete()
    # delete Repo
    Repo.objects(owner=owner, name=name).delete()


def recommend_repo_config(
    owner: str,
    name: str,
    user: Optional[str] = None,
    newcomer_percentage: Optional[int] = None,
    gfi_percentage: Optional[int] = None,
) -> UserRepoConfig:
    """
    Recommend good first issue for a repository
    :param owner: Repo owner
    :param name: Repo name
    :param user: Committer login
    :param newcomer_percentage: percentage of newcomers
    :param gfi_percentage: percentage of good first issues in open issues
    """
    if not newcomer_percentage:
        newcomer_percentage = 0.4
    else:
        newcomer_percentage = newcomer_percentage / 100

    if not gfi_percentage:
        gfi_percentage = 0.05
    else:
        gfi_percentage = gfi_percentage / 100

    selector = Q(name=name, owner=owner)
    if user:
        selector = selector & Q(committer=user)

    repo_commits = pd.DataFrame(
        RepoCommit.objects(selector)
        .only("committer", "committed_at")
        .order_by("committed_at")
        .as_pymongo()
    )
    repo_commits["committed_at"] = pd.to_datetime(repo_commits["committed_at"])

    # the hour with most commits
    hour_of_day = repo_commits["committed_at"].dt.hour.value_counts().index[0]
    # the day of week with most commits
    day_of_week = repo_commits["committed_at"].dt.dayofweek.value_counts().index[0]

    # median committed_at interval
    repo_commits["committed_at"] = pd.to_datetime(repo_commits["committed_at"])
    median_interval = repo_commits["committed_at"].diff().median()

    # generate cron
    if median_interval < pd.Timedelta("1 days"):  # daily
        cron = f"{randint(0, 59)} {hour_of_day} * * *"
    else:  # weekly
        cron = f"{randint(0, 59)} {hour_of_day} {day_of_week} * 0"

    # 25% percentile commits per user
    _newcomer_thres = (
        repo_commits["committer"].value_counts().quantile(newcomer_percentage)
    )
    logger.info("median_interval: %s #commits: %s", median_interval, _newcomer_thres)
    # closest int between 1-5
    _newcomer_thres = int(_newcomer_thres)
    if _newcomer_thres < 1:
        _newcomer_thres = 1
    elif _newcomer_thres > 5:
        _newcomer_thres = 5

    # 25% quantile of predicted probability -> gfi_threshold
    newcomer_thres = get_newcomer_threshold(owner, name)
    gfis = pd.DataFrame(
        Prediction.objects(owner=owner, name=name, threshold=newcomer_thres)
        .only("number", "probability")
        .as_pymongo()
    )
    _gfi_thres = gfis["probability"].quantile(1 - gfi_percentage)
    _gfi_thres = float(round(_gfi_thres, 2))
    logger.info("gfi threshold: %s", _gfi_thres)
    if _gfi_thres > 0.8:
        _gfi_thres = 0.8
    if _gfi_thres < 0.2:
        _gfi_thres = 0.2

    logger.info(
        "Recommended config for %s/%s: cron=%s, newcomer_threshold=%s, gfi_threshold=%s",
        owner,
        name,
        cron,
        _newcomer_thres,
        _gfi_thres,
    )

    return UserRepoConfig(
        update_cron=cron,
        newcomer_threshold=int(_newcomer_thres),
        gfi_threshold=float(_gfi_thres),
        issue_label="good first issue",
        need_comment=True,
        auto_label=False,
        badge_prefix="recommended good first issues",
    )
