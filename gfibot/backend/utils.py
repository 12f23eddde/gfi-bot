from typing import Optional

from gfibot import CONFIG
from gfibot.collections import GfibotRepo


def get_newcomer_threshold(owner: Optional[str], name: Optional[str]) -> int:
    if owner and name:
        repo = GfibotRepo.objects(name=name, owner=owner).first()
        if repo:
            return repo.config.newcomer_threshold
    try:
        return CONFIG["gfibot"]["default_newcomer_threshold"]
    except KeyError:
        return 5


def get_gfi_threshold(owner: Optional[str], name: Optional[str]) -> float:
    if owner and name:
        repo = GfibotRepo.objects(name=name, owner=owner).first()
        if repo:
            return repo.config.gfi_threshold
    try:
        return CONFIG["gfibot"]["default_gfi_threshold"]
    except KeyError:
        return 0.5


def mask_token(token: str) -> str:
    unmasked_chars = max(3, len(token) // 3)
    return "*" * (len(token) - unmasked_chars) + token[-unmasked_chars:]
