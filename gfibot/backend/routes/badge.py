import logging

import requests
from fastapi import Response, APIRouter
from mongoengine import Q

from gfibot.collections import Prediction, GfibotRepo
from gfibot.backend.utils import get_gfi_threshold, get_newcomer_threshold

BADGE_PREFIX = "recommended good first issues"

api = APIRouter()
logger = logging.getLogger(__name__)


@api.get("", response_class=Response)
def get_badge(name: str, owner: str):
    """
    Get README badge for a repository
    """
    prob_thres = get_gfi_threshold(name, owner)
    newcomer_thres = get_newcomer_threshold(name, owner)
    n_gfis = Prediction.objects(
        Q(name=name)
        & Q(owner=owner)
        & Q(probability__gte=prob_thres)
        & Q(threshold=newcomer_thres)
        & Q(state="open")
    ).count()

    repo = GfibotRepo.objects(owner=owner, name=name).first()
    if repo:
        badge_prefix = repo.config.badge_prefix
    else:
        badge_prefix = BADGE_PREFIX
    img_src = "https://img.shields.io/badge/{}-{}-{}".format(
        badge_prefix, n_gfis, "success"
    )
    svg = requests.get(img_src).content
    return Response(svg, media_type="image/svg+xml")


@api.get("/{owner}/{name}", response_class=Response)
def get_badge_by_path(name: str, owner: str):
    return get_badge(name, owner)
