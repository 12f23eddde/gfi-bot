from typing import List, Optional
import math

from fastapi import APIRouter, HTTPException

from gfibot.collections import *
from gfibot.backend.models import (
    GFIResponse,
    TrainingResult,
    FeatureImportance,
    GFIDataset,
)
from gfibot.backend.utils import get_gfi_threshold, get_newcomer_threshold

from gfibot.model.predict import get_feature_importance

api = APIRouter()
logger = logging.getLogger(__name__)


@api.get("/features", response_model=GFIResponse[FeatureImportance])
def get_features():
    """
    Read feature importance from training logs
    TODO: save importance to database
    """
    newcomer_thres = get_newcomer_threshold(None, None)
    imp = get_feature_importance(newcomer_thres)
    return GFIResponse(result=imp)


@api.get("/dataset", response_model=GFIResponse)
def get_issue_dataset(owner: str, name: str, number: int):
    """
    Get dataset of issue /owner/name/number
    """
    dataset = (
        Dataset.objects(name=name, owner=owner, number=number)
        .exclude(
            "id",
            "name",
            "owner",
            "number",
            "title",
            "body",
            "created_at",
            "closed_at",
            "before",
        )
        .order_by("-before")
        .first()
    )
    if not dataset:
        raise HTTPException(404, f"Dataset not found: {owner}/{name}/{number}")
    return GFIResponse(result=dataset.to_mongo())


@api.get("/performance", response_model=GFIResponse[TrainingResult])
def get_training_result(
    name: Optional[str] = None,
    owner: Optional[str] = None,
):
    """
    Get model performance on owner/name (leave owner&name blank for global perf)
    """
    newcomer_thres = get_newcomer_threshold(name=name, owner=owner)

    if not owner or not name:
        owner = ""
        name = ""

    query: List[TrainingSummary] = list(
        TrainingSummary.objects(Q(name=name, owner=owner, threshold=newcomer_thres))
        .only(*TrainingResult.__fields__)
        .aggregate(
            {
                "$set": {
                    "issues_train": {"$size": "$issues_train"},
                    "issues_test": {"$size": "$issues_test"},
                }
            },
            {"$limit": 1},
        )
    )

    if not query:
        raise HTTPException(status_code=404, detail="Training result not found")

    # q = {**query[0].to_mongo()}
    # q["issues_train"] = len(q["issues_train"])
    # q["issues_test"] = len(q["issues_test"])
    # q = {
    #     k: 0.0 if isinstance(v, float) and math.isnan(v) else v
    #     for k, v in q.items()
    # }  # convert nan to 0

    return GFIResponse(result=query[0])
