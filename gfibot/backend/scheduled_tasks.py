"""
Routines below are blocking and should be run in a separate thread (i.e. scheduler)
NEVER call them directly from the backend, otherwise the backend will be blocked
"""

import argparse
from typing import Optional, Callable
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from functools import wraps
import logging
import random
import datetime

import mongoengine
from pytz import utc
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from github import Github
from github import BadCredentialsException, RateLimitExceededException, GithubException

from gfibot import CONFIG, TOKENS

from gfibot.data.update import update_repo
from gfibot.collections import *
from gfibot.check_tokens import check_tokens
from gfibot.data.dataset import get_dataset_for_repo, get_dataset_all
from gfibot.backend.ghapp import get_repo_app_token

from gfibot.model.predict import predict_repo

from gfibot.backend.utils import get_gfi_threshold, get_newcomer_threshold

executor = ThreadPoolExecutor(max_workers=10)

logger = logging.getLogger(__name__)

DEFAULT_JOB_ID = "gfibot-daemon"

COMMENT_TEMPLATE = """
Hi there, I'm GFI-Bot! :robot:

I have predicted that this issue is a good first issue with a probability of {:.2f}%. :sparkles:
"""


def _add_label_and_comment_to_github_issue(
    owner: str,
    name: str,
    number: int,
    token: str,
    label: str = None,
    comment: Optional[str] = None,
):
    """
    Add label and comment to Github issue
    """
    g = Github(jwt=token)
    repo = g.get_repo(owner + "/" + name)
    issue = repo.get_issue(number)
    # check if label exists
    for _label in issue.labels:
        if _label.name == label:
            logger.info("Label %s exists: %s/%s/%s", label, owner, name, number)
            return

    issue.add_to_labels(label)
    logger.info("Label %s added: %s/%s/%s", label, owner, name, number)
    if comment:
        issue.create_comment(comment)
        logger.info("Comment added: %s/%s/%s", owner, name, number)


# def _tag_and_comment(owner: str, name: str):
#     """
#     Add labels and comments (if necessary) to GitHub issue
#     """
#     repo_query = GfiQueries.objects(Q(name=name) & Q(owner=owner)).first()
#     threshold = repo_query.repo_config.gfi_threshold
#     newcomer_threshold = repo_query.repo_config.newcomer_threshold
#     issue_tag = repo_query.repo_config.issue_tag
#     if repo_query and repo_query.is_github_app_repo:
#         predicts = Prediction.objects(
#             Q(owner=owner)
#             & Q(name=name)
#             & Q(probability__gte=threshold)
#             & Q(threshold=newcomer_threshold)
#         )
#         logger.info(
#             "Found {} good first issues for repo {} with threshold {}".format(
#                 len(predicts), name, threshold
#             )
#         )
#         should_comment = repo_query.repo_config.need_comment
#         for predict in predicts:
#             if predict.tagged != True:
#                 if (
#                     _add_gfi_label_to_github_issue(
#                         github_login=github_login,
#                         repo_name=predict.name,
#                         repo_owner=predict.owner,
#                         issue_number=predict.number,
#                         label_name=issue_tag,
#                     )
#                     == 200
#                 ):
#                     predict.tagged = True
#                     predict.save()
#                 else:
#                     logger.warning(
#                         "Failed to add label to issue {} in repo {}".format(
#                             predict.number, predict.name
#                         )
#                     )
#             if predict.commented != True and should_comment:
#                 comment = "[GFI-Bot] Predicted as Good First Issue with probability {}%.".format(
#                     round((predict.probability) * 100, 2)
#                 )
#                 if (
#                     _add_comment_to_github_issue(
#                         github_login=github_login,
#                         repo_name=predict.name,
#                         repo_owner=predict.owner,
#                         issue_number=predict.number,
#                         comment=comment,
#                     )
#                     == 200
#                 ):
#                     predict.commented = True
#                     predict.save()
#                 else:
#                     logger.warning(
#                         "Failed to add comment to issue {} in repo {}".format(
#                             predict.number, predict.name
#                         )
#                     )


def get_valid_tokens() -> List[str]:
    """
    Get valid tokens
    """
    tokens = [
        user.oauth_token
        for user in GfibotUser.objects()
        if user.oauth_token is not None
    ] + TOKENS
    return list(set(tokens) - check_tokens(tokens))


def label_and_comment(owner: str, name: str, token: str):
    """
    Add labels and comments (if necessary) to GitHub issue
    """
    repo: Optional[GfibotRepo] = GfibotRepo.objects(
        Q(name=name) & Q(owner=owner)
    ).first()
    if not repo:
        return

    gfi_thres = get_gfi_threshold(name=name, owner=owner)
    newcomer_thres = get_newcomer_threshold(name=name, owner=owner)

    predicted_gfis: List[Prediction] = Prediction.objects(
        owner=owner,
        name=name,
        probability__gte=gfi_thres,
        threshold=newcomer_thres,
        state="open",
    )

    logger.info(
        "Found {} good first issues for repo {} with threshold {}".format(
            len(predicted_gfis), name, gfi_thres
        )
    )

    issue_label = repo.config.issue_label
    should_comment = repo.config.need_comment

    for gfi in predicted_gfis:
        try:
            if gfi.tagged:
                continue
            _add_label_and_comment_to_github_issue(
                owner=owner,
                name=name,
                number=gfi.number,
                token=token,
                label=issue_label,
                comment=COMMENT_TEMPLATE.format(gfi.probability * 100)
                if should_comment
                else None,
            )
            gfi.tagged = True
            if should_comment:
                gfi.commented = True
            gfi.save()
        except GithubException as e:
            logger.error(
                "Failed to add label/comment to issue {} in repo {}".format(
                    gfi.number, name
                )
            )
            logger.error(e)


def update_gfi_info(token: str, owner: str, name: str, send_email: bool = False):
    """
    Repository manual updater (will block until done)
    token: GitHub token
    owner: GitHub repository owner
    name: GitHub repository name
    send_email: if True, send email to user
    """
    logger.info(
        "Updating gfi info for " + owner + "/" + name + " at {}.".format(datetime.now())
    )

    # 0. set state
    # q = GfiQueries.objects(Q(name=name) & Q(owner=owner)).first()
    q: Optional[GfibotRepo] = GfibotRepo.objects(Q(name=name) & Q(owner=owner)).first()
    if q:
        # if q.is_updating:
        #     logger.info("{}/{} is already updating.".format(owner, name))
        #     return
        # q.update(is_updating=True, is_finished=False)

        if q.state in ["collecting", "training"]:
            logger.info("%s/%s is already updating: %s", owner, name, q.state)
            return
        q.update(state="collecting")
    else:
        logger.info("No such repo: %s/%s", owner, name)
        return

    try:
        # 1. fetch repo data
        try:
            update_repo(token, owner, name)
        except (BadCredentialsException, RateLimitExceededException) as e:
            # second try with a new token
            logger.error(e)
            valid_tokens = get_valid_tokens()
            if not valid_tokens:
                logger.error("No valid tokens found.")
                return
            random.seed(datetime.now())
            token = random.choice(valid_tokens)
            update_repo(token, owner, name)

        # 2. rebuild repo dataset
        begin_datetime = datetime(2008, 1, 1)
        get_dataset_for_repo(owner=owner, name=name, since=begin_datetime)
        q.update(state="training")

        # 3. update training summary
        # 4. update gfi prediction
        for newcomer_thres in [1, 2, 3, 4, 5]:
            predict_repo(owner=owner, name=name, newcomer_thres=newcomer_thres)

        logger.info(
            "Update done for " + owner + "/" + name + " at {}.".format(datetime.now())
        )

        # 5. label and comment (if necessary)
        if q.config.auto_label:
            # obtain a valid token
            try:
                app_token = get_repo_app_token(owner=owner, name=name)
                if not app_token:
                    raise GithubException("App installation not found.")
                label_and_comment(owner=owner, name=name, token=app_token)
            except GithubException as e:
                logger.error("Failed to obtain installation token: %s", e)

        q.update(state="done")

    # 6. set state
    except Exception as e:
        logger.error("Error updating %s/%s: %s", owner, name, e)
        q.update(state="error")
        raise e


def start_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone=utc)
    scheduler.add_job(daemon, "cron", hour=0, minute=0, id=DEFAULT_JOB_ID)
    valid_tokens = get_valid_tokens()
    if not valid_tokens:
        raise Exception("No valid tokens found.")
    for i, repo in enumerate(GfibotRepo.objects()):
        if repo.config:
            config = repo.config
            trigger = CronTrigger.from_crontab(config.update_cron)
            trigger.jitter = 1200
            task_id = f"{repo.owner}-{repo.name}-update"
            scheduler.add_job(
                update_gfi_info,
                trigger=trigger,
                args=[valid_tokens[i % len(valid_tokens)], repo.owner, repo.name],
                id=task_id,
                replace_existing=True,
            )
            logger.info("Scheduled task: " + task_id + " added.")
    scheduler.start()
    logger.info("Scheduler started.")
    return scheduler


def daemon(init=False):
    """
    Daemon updates repos without specific update config.
    init: if True, it will update all repos.
    """
    logger.info("Daemon started at " + str(datetime.now()))

    valid_tokens = get_valid_tokens()
    if not valid_tokens:
        raise Exception("No valid tokens found.")
    if init:
        logger.info("Fetching ALL repo data from github")
        for i, project in enumerate(CONFIG["gfibot"]["projects"]):
            owner, name = project.split("/")
            update_repo(valid_tokens[i % len(valid_tokens)], owner, name)
    else:
        for i, repo in enumerate(list(Repo.objects().only("owner", "name"))):
            repo_query = GfibotRepo.objects(
                Q(name=repo.name) & Q(owner=repo.owner)
            ).first()
            if not repo_query or not repo_query.config:
                logger.info(
                    "Fetching repo data from github: %s/%s", repo.owner, repo.name
                )
                update_repo(valid_tokens[i % len(valid_tokens)], repo.owner, repo.name)

    logger.info("Building dataset")
    get_dataset_all(datetime(2008, 1, 1))

    for threshold in [1, 2, 3, 4, 5]:
        for i, repo in enumerate(list(Repo.objects().only("owner", "name"))):
            repo_query = GfibotRepo.objects(
                Q(name=repo.name) & Q(owner=repo.owner)
            ).first()
            if not repo_query or not repo_query.config:
                logger.info(
                    "Updating training summary and prediction: %s/%s@%d",
                    repo.owner,
                    repo.name,
                    threshold,
                )
                predict_repo(repo.owner, repo.name, newcomer_thres=threshold)

    logger.info("Daemon finished at " + str(datetime.now()))


def mongoengine_fork_safe_wrapper(*mongoengine_args, **mongoengine_kwargs):
    """
    Wrap a mongoengine function to make it fork safe
    """

    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            mongoengine.disconnect_all()
            mongoengine.connect(*mongoengine_args, **mongoengine_kwargs)
            try:
                return func(*args, **kwargs)
            finally:
                mongoengine.disconnect()

        return wrapper

    return decorator


@mongoengine_fork_safe_wrapper(
    db=CONFIG["mongodb"]["db"],
    host=CONFIG["mongodb"]["url"],
    tz_aware=True,
    uuidRepresentation="standard",
)
def update_repo_mp(token: str, owner: str, name: str):
    update_repo(token, owner, name)


@mongoengine_fork_safe_wrapper(
    db=CONFIG["mongodb"]["db"],
    host=CONFIG["mongodb"]["url"],
    tz_aware=True,
    uuidRepresentation="standard",
)
def update_training_summary_and_prediction_mp(owner: str, name: str, threshold: int):
    predict_repo(owner, name, newcomer_thres=threshold)


# @mongoengine_fork_safe_wrapper(
#     db=CONFIG["mongodb"]["db"],
#     host=CONFIG["mongodb"]["url"],
#     tz_aware=True,
#     uuidRepresentation="standard",
# )
# def update_prediction_mp(threshold: int):
#     update_prediction(threshold)


def daemon_mp(init=False, n_workers: Optional[int] = None):
    """
    Daemon updates repos without specific update config.
    init: if True, it will update all repos.
    n_workers: if not None, it will use n_workers to update repos.
        note that workers eat up loads of memory (~10GB each during model training)
    """
    logger.info("Daemon started at %s, workers=%s", str(datetime.now()), str(n_workers))

    mongoengine.connect(
        CONFIG["mongodb"]["db"],
        host=CONFIG["mongodb"]["url"],
        tz_aware=True,
        uuidRepresentation="standard",
        connect=False,
    )

    valid_tokens = get_valid_tokens()

    # 1. fetch data from github
    repos_to_update = []
    if init:
        repos_to_update = [
            (s.split("/")[0], s.split("/")[1]) for s in CONFIG["gfibot"]["projects"]
        ]
    else:
        for repo in Repo.objects():
            repo_query = GfibotRepo.objects(
                Q(name=repo.name) & Q(owner=repo.owner)
            ).first()
            if (not repo_query) or (repo_query and not repo_query.config):
                repos_to_update.append((repo.owner, repo.name))
    logger.info("Fetching %d repos from github", len(repos_to_update))

    if n_workers is not None:
        with ProcessPoolExecutor(max_workers=n_workers):
            for i, (owner, name) in enumerate(repos_to_update):
                executor.submit(
                    update_repo_mp, valid_tokens[i % len(valid_tokens)], owner, name
                )
    else:
        for i, (owner, name) in enumerate(repos_to_update):
            update_repo(valid_tokens[i % len(valid_tokens)], owner, name)

    # 2. build dataset
    logger.info("Building dataset")
    get_dataset_all(datetime(2008, 1, 1), n_process=n_workers)

    # 3. update training summary
    # 4. update prediction
    if n_workers is not None:
        with ProcessPoolExecutor(max_workers=n_workers):
            for threshold in [1, 2, 3, 4, 5]:
                for i, (owner, name) in enumerate(repos_to_update):
                    executor.submit(
                        update_training_summary_and_prediction_mp,
                        owner,
                        name,
                        threshold,
                    )
    else:
        for threshold in [1, 2, 3, 4, 5]:
            for i, (owner, name) in enumerate(repos_to_update):
                predict_repo(owner, name, newcomer_thres=threshold)
            logger.info("Prediction updated for threshold %d", threshold)

    logger.info("Daemon finished at " + str(datetime.now()))


if __name__ == "__main__":
    parser = argparse.ArgumentParser("GFI-Bot Dataset Builder")
    parser.add_argument(
        "--init", action="store_true", default=False, help="init dataset"
    )
    parser.add_argument(
        "--n_workers", type=int, default=None, help="number of workers to use"
    )
    args = parser.parse_args()

    # daemon_mp(args.init, args.n_workers)
    mongoengine.connect(
        CONFIG["mongodb"]["db"],
        host=CONFIG["mongodb"]["url"],
        tz_aware=True,
        uuidRepresentation="standard",
        connect=False,
    )
    daemon(args.init)
