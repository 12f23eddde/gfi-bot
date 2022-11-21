import pytest
import logging
from typing import Dict, List, Optional, Any, TypeVar

import mongoengine
import mongoengine.context_managers

from datetime import datetime, timezone
from gfibot import CONFIG, TOKENS
from gfibot.check_tokens import check_tokens
from gfibot.collections import *
from gfibot.data.dataset import *
import gfibot.model.base


@pytest.fixture(scope="session", autouse=True)
def execute_before_any_test():
    check_tokens(TOKENS)

    # Ensure that the production database is not touched in all tests
    CONFIG["mongodb"]["db"] = "gfibot-test"
    mongoengine.disconnect_all()
    gfibot.model.base.GFIBOT_MODEL_PATH = "models-test"
    os.makedirs("models-test", exist_ok=True)

    # don't start scheduler in tests
    os.environ["GFIBOT_SKIP_SCHEDULER"] = "1"
    # limit since_date in tests
    os.environ["CI"] = "1"
    # don't authenticate in tests
    os.environ["GFIBOT_DISABLE_AUTH"] = "1"
    os.environ["GFIBOT_ENV"] = "test"


# Mocked mongodb data
MONGOMOCK_DATA: Dict[Document.__class__, List[Document]] = {
    Repo: [
        Repo(
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            owner="owner",
            name="name",
            language="C#",
            topics=["topic1", "topic2"],
            description="Your Awesome Random APP",
            repo_created_at=datetime(2022, 1, 1, tzinfo=timezone.utc),
            monthly_stars=[
                Repo.MonthCount(
                    month=datetime(2022, 1, 1, tzinfo=timezone.utc), count=1
                )
            ],
            monthly_commits=[
                Repo.MonthCount(
                    month=datetime(2022, 1, 1, tzinfo=timezone.utc), count=1
                )
            ],
            monthly_issues=[
                Repo.MonthCount(
                    month=datetime(2022, 1, 1, tzinfo=timezone.utc), count=3
                )
            ],
            monthly_pulls=[
                Repo.MonthCount(
                    month=datetime(2022, 1, 1, tzinfo=timezone.utc), count=1
                )
            ],
        ),
        Repo(
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            owner="owner2",
            name="name2",
            language="Python",
            topics=["topic1", "topic2"],
            description="Another Awesome Random Project",
            repo_created_at=datetime(2022, 1, 1, tzinfo=timezone.utc),
            monthly_stars=[
                Repo.MonthCount(
                    month=datetime(2022, 1, 1, tzinfo=timezone.utc), count=1
                )
            ],
            monthly_commits=[
                Repo.MonthCount(
                    month=datetime(2022, 1, 1, tzinfo=timezone.utc), count=1
                )
            ],
            monthly_issues=[
                Repo.MonthCount(
                    month=datetime(2022, 1, 1, tzinfo=timezone.utc), count=3
                )
            ],
            monthly_pulls=[
                Repo.MonthCount(
                    month=datetime(2022, 1, 1, tzinfo=timezone.utc), count=1
                )
            ],
        ),
    ],
    RepoCommit: [
        RepoCommit(
            owner="owner",
            name="name",
            sha="50d4fff434ac6b7c6a728bd796413f279867f859",
            author="a1",
            authored_at=datetime(2022, 1, 2, tzinfo=timezone.utc),
            committer="a1",
            committed_at=datetime(2022, 1, 2, tzinfo=timezone.utc),
            message="fixes #1",
        )
    ],
    RepoIssue: [
        RepoIssue(
            owner="owner",
            name="name",
            number=1,
            user="a1",
            state="closed",
            created_at=datetime(2022, 1, 1, tzinfo=timezone.utc),
            closed_at=datetime(2022, 1, 2, tzinfo=timezone.utc),
            title="issue 1",
            body="issue 1",
            labels=[],
            is_pull=False,
            merged_at=None,
        ),
        RepoIssue(
            owner="owner",
            name="name",
            number=2,
            user="a1",
            state="closed",
            created_at=datetime(2022, 1, 3, tzinfo=timezone.utc),
            closed_at=datetime(2022, 1, 4, tzinfo=timezone.utc),
            title="issue 2",
            body="issue 2",
            labels=["bug"],
            is_pull=False,
            merged_at=None,
        ),
        RepoIssue(
            owner="owner",
            name="name",
            number=3,
            user="a1",
            state="closed",
            created_at=datetime(2022, 1, 3, tzinfo=timezone.utc),
            closed_at=datetime(2022, 1, 4, tzinfo=timezone.utc),
            title="PR 3",
            body="Fixes #2",
            labels=[],
            is_pull=True,
            merged_at=datetime(2022, 1, 4, tzinfo=timezone.utc),
        ),
        RepoIssue(
            owner="owner",
            name="name",
            number=4,
            user="a2",
            state="open",
            created_at=datetime(2022, 1, 5, tzinfo=timezone.utc),
            closed_at=None,
            title="issue 4",
            body="issue 4 body",
            labels=["good first issue"],
            is_pull=False,
            merged_at=None,
        ),
    ],
    RepoStar: [
        RepoStar(
            owner="owner",
            name="name",
            user="a1",
            starred_at=datetime(2022, 1, 1, tzinfo=timezone.utc),
        )
    ],
    ResolvedIssue: [
        ResolvedIssue(
            owner="owner",
            name="name",
            number=1,
            created_at=datetime(2022, 1, 1, tzinfo=timezone.utc),
            resolved_at=datetime(2022, 1, 2, tzinfo=timezone.utc),
            resolver="a1",
            resolved_in="50d4fff434ac6b7c6a728bd796413f279867f859",
            resolver_commit_num=0,
            events=[],
        ),
        ResolvedIssue(
            owner="owner",
            name="name",
            number=2,
            created_at=datetime(2022, 1, 3, tzinfo=timezone.utc),
            resolved_at=datetime(2022, 1, 4, tzinfo=timezone.utc),
            resolver="a1",
            resolved_in=3,
            resolver_commit_num=1,
            events=[
                IssueEvent(
                    type="labeled",
                    label="bug",
                    actor="a1",
                    time=datetime(2022, 1, 3, tzinfo=timezone.utc),
                ),
                IssueEvent(
                    type="labeled",
                    label="gfi",
                    actor="a2",
                    time=datetime(2022, 1, 3, tzinfo=timezone.utc),
                ),
                IssueEvent(
                    type="unlabeled",
                    label="gfi",
                    actor="a2",
                    time=datetime(2022, 1, 3, tzinfo=timezone.utc),
                ),
                IssueEvent(
                    type="commented",
                    actor="a2",
                    time=datetime(2022, 1, 3, tzinfo=timezone.utc),
                    comment="a comment",
                ),
            ],
        ),
    ],
    OpenIssue: [
        OpenIssue(
            owner="owner",
            name="name",
            number=4,
            created_at=datetime(2022, 1, 5, tzinfo=timezone.utc),
            updated_at=datetime(2022, 1, 5, tzinfo=timezone.utc),
            events=[
                IssueEvent(
                    type="labeled",
                    label="good first issue",
                    actor="a1",
                    time=datetime(2022, 1, 5, tzinfo=timezone.utc),
                )
            ],
        )
    ],
    User: [
        User(
            _created_at=datetime.utcnow(),
            _updated_at=datetime.utcnow(),
            name="a1",
            login="a1",
            issues=[
                User.Issue(
                    owner="owner",
                    name="name",
                    repo_stars=1,
                    state="closed",
                    number=1,
                    created_at=datetime(2022, 1, 1, tzinfo=timezone.utc),
                )
            ],
            pulls=[],
            pull_reviews=[],
            commit_contributions=[],
        ),
        User(
            _created_at=datetime.utcnow(),
            _updated_at=datetime.utcnow(),
            name="a2",
            login="a2",
            issues=[],
            pulls=[],
            pull_reviews=[],
            commit_contributions=[],
        ),
    ],
    Dataset: [
        Dataset(
            owner="owner",
            name="name",
            number=5,
            created_at=datetime(1970, 1, 2, tzinfo=timezone.utc),
            closed_at=datetime(1970, 1, 3, tzinfo=timezone.utc),
            before=datetime(1970, 1, 3, tzinfo=timezone.utc),
            resolver_commit_num=1,
            title="title",
            body="body",
            len_title=1,
            len_body=1,
            n_code_snips=0,
            n_urls=0,
            n_imgs=0,
            coleman_liau_index=0.1,
            flesch_reading_ease=0.1,
            flesch_kincaid_grade=0.1,
            automated_readability_index=0.1,
            labels=["good first issue"],
            label_category=Dataset.LabelCategory(gfi=1),
            reporter_feat=Dataset.UserFeature(
                name="a1",
                n_commits=3,
                n_issues=1,
                n_pulls=2,
                resolver_commits=[4, 5, 6],
            ),
            owner_feat=Dataset.UserFeature(
                name="a2",
                n_commits=5,
                n_issues=1,
                n_pulls=2,
                resolver_commits=[1, 2, 3],
            ),
            n_stars=0,
            n_pulls=1,
            n_commits=5,
            n_contributors=2,
            n_closed_issues=1,
            n_open_issues=1,
            r_open_issues=1,
            issue_close_time=1.0,
            comment_users=[
                Dataset.UserFeature(
                    name="a3",
                    n_commits=5,
                    n_issues=1,
                    n_pulls=2,
                    resolver_commits=[1, 2],
                ),
                Dataset.UserFeature(
                    name="a4",
                    n_commits=3,
                    n_issues=1,
                    n_pulls=1,
                    resolver_commits=[4, 5],
                ),
            ],
        ),
        Dataset(
            owner="owner",
            name="name",
            number=6,
            created_at=datetime(1971, 1, 2, tzinfo=timezone.utc),
            closed_at=datetime(1971, 1, 3, tzinfo=timezone.utc),
            before=datetime(1971, 1, 3, tzinfo=timezone.utc),
            resolver_commit_num=3,
            title="title",
            body="body",
            len_title=1,
            len_body=1,
            n_code_snips=0,
            n_urls=0,
            n_imgs=0,
            coleman_liau_index=0.1,
            flesch_reading_ease=0.1,
            flesch_kincaid_grade=0.1,
            automated_readability_index=0.1,
            labels=[],
            label_category=Dataset.LabelCategory(gfi=1),
            reporter_feat=Dataset.UserFeature(
                name="a1",
                n_commits=3,
                n_issues=1,
                n_pulls=2,
                resolver_commits=[4, 5, 6],
            ),
            owner_feat=Dataset.UserFeature(
                name="a2",
                n_commits=5,
                n_issues=1,
                n_pulls=2,
                resolver_commits=[1, 2, 3],
            ),
            n_stars=0,
            n_pulls=1,
            n_commits=5,
            n_contributors=2,
            n_closed_issues=1,
            n_open_issues=1,
            r_open_issues=1,
            issue_close_time=1.0,
            comment_users=[
                Dataset.UserFeature(
                    name="a3",
                    n_commits=5,
                    n_issues=1,
                    n_pulls=2,
                    resolver_commits=[1, 2],
                ),
                Dataset.UserFeature(
                    name="a4",
                    n_commits=3,
                    n_issues=1,
                    n_pulls=1,
                    resolver_commits=[4, 5],
                ),
            ],
        ),
    ],
    TrainingSummary: [
        TrainingSummary(
            owner="owner",
            name="name",
            threshold=CONFIG["gfibot"]["default_newcomer_threshold"],
            issues_train=[["a1", "a2"], ["a3", "a4"]],
            issues_test=[["a1", "a2"], ["a3", "a4"]],
            n_resolved_issues=3,
            n_newcomer_resolved=2,
            last_updated=datetime(1970, 1, 1, tzinfo=timezone.utc),
            r_newcomer_resolved=0.4,
            n_stars=10,
            n_gfis=2,
            issue_close_time=114514,
        ),
        TrainingSummary(
            owner="owner2",
            name="name2",
            threshold=CONFIG["gfibot"]["default_newcomer_threshold"],
            issues_train=[["a1", "a2"], ["a3", "a4"]],
            issues_test=[["a1", "a2"], ["a3", "a4"]],
            n_resolved_issues=3,
            n_newcomer_resolved=0,
            last_updated=datetime(1970, 1, 1, tzinfo=timezone.utc),
            r_newcomer_resolved=0.0,
            n_stars=15,
            n_gfis=1,
            accuracy=0.5,
            auc=0.6,
            issue_close_time=114,
        ),
        TrainingSummary(
            owner="",
            name="",
            threshold=CONFIG["gfibot"]["default_newcomer_threshold"],
            last_updated=datetime(1970, 1, 1, tzinfo=timezone.utc),
            accuracy=0.5,
            auc=0.6,
            issue_close_time=114,
            n_resolved_issues=3,
            n_newcomer_resolved=0,
        ),
    ],
    Prediction: [
        Prediction(
            owner="owner",
            name="name",
            number=1,
            state="closed",
            threshold=CONFIG["gfibot"]["default_newcomer_threshold"],
            probability=0.9,
            last_updated=datetime(1970, 1, 1, tzinfo=timezone.utc),
        ),
        Prediction(
            owner="owner",
            name="name",
            number=4,
            state="open",
            threshold=CONFIG["gfibot"]["default_newcomer_threshold"],
            probability=0.3,
            last_updated=datetime(1970, 1, 1, tzinfo=timezone.utc),
        ),
        Prediction(
            owner="owner",
            name="name",
            number=9,
            state="open",
            threshold=1 if CONFIG["gfibot"]["default_newcomer_threshold"] != 1 else 5,
            probability=0.1,
            last_updated=datetime(1970, 1, 1, tzinfo=timezone.utc),
        ),
    ],
    GfibotUser: [
        GfibotUser(
            login="owner",
            name="GfibotUser1",
            oauth_token="not_a_real_token",
            email="owner@example.com",
            avatar_url="https://avatars.githubusercontent.com/u/1?v=4",
        )
    ],
    GfibotSearch: [
        GfibotSearch(
            owner="owner",
            name="name",
            query="query",
            login="owner",
            searched_at=datetime(2000, 1, 1, tzinfo=timezone.utc),
        )
    ],
    GfibotInstallation: [
        GfibotInstallation(
            token="not_a_real_token",
            installation_id=1,
            login="owner",
            expires_at=datetime(2050, 1, 1, tzinfo=timezone.utc),
        )
    ],
    GfibotRepo: [
        GfibotRepo(
            owner="owner",
            name="name",
            state="done",
            added_by="owner",
            config=GfibotRepo.GfibotRepoConfig(
                update_cron="0 0 * * *",
                newcomer_threshold=CONFIG["gfibot"]["default_newcomer_threshold"],
                gfi_threshold=CONFIG["gfibot"]["default_gfi_threshold"],
            ),
        )
    ],
}


def insert_mock_data():
    # It seems that drop database does not work with mongomock
    for cls, data in MONGOMOCK_DATA.items():
        cls.drop_collection()
        for index, d in enumerate(data):
            try:
                d.save(force_insert=True)  # TODO: won't work without force_insert=True?
            except mongoengine.errors.ValidationError as e:
                logging.error(f"Error at index {index} of {cls}: {e}")
                logging.error(f"Trying to insert: {d}")
                raise e
        # validate
        assert cls.objects().count() == len(data)

    for resolved_issue in MONGOMOCK_DATA[ResolvedIssue]:
        get_dataset(resolved_issue, resolved_issue.resolved_at)
        get_dataset(resolved_issue, resolved_issue.created_at)

    for open_issue in MONGOMOCK_DATA[OpenIssue]:
        get_dataset(open_issue, open_issue.updated_at)


@pytest.fixture(scope="function")
def real_mongodb():
    """
    Prepare a real MongoDB instance for test usage.
    This fixture should only be used for test_all().
    """
    CONFIG["mongodb"]["db"] = "gfibot-test"

    conn = mongoengine.connect(
        CONFIG["mongodb"]["db"],
        host=CONFIG["mongodb"]["url"],
        tz_aware=True,
        uuidRepresentation="standard",
    )
    conn.drop_database(CONFIG["mongodb"]["db"])

    insert_mock_data()

    yield

    mongoengine.disconnect()


@pytest.fixture(scope="function")
def mock_mongodb():
    """
    Prepare a mock MongoDB instance for test usage.
    This fixture can be used by any test that want some interaction with MongoDB.
    The MongoDB will contain some mock data for writing unit tests.
    """

    # run before tests

    CONFIG["mongodb"]["db"] = "gfibot-mock"

    mongoengine.connect(
        CONFIG["mongodb"]["db"],
        host="mongomock://localhost",
        tz_aware=True,
        uuidRepresentation="standard",
    )

    insert_mock_data()

    yield

    # run after tests

    mongoengine.disconnect()
