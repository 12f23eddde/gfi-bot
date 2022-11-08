import sys
import nltk
import logging
import os

from typing import List
from pathlib import Path

from dynaconf import Dynaconf

# init logger
logging.basicConfig(
    format="%(asctime)s (PID %(process)d) [%(levelname)s] %(filename)s:%(lineno)d %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)],
)

# load config
BASE_DIR = Path(__file__).parent.parent.absolute()

CONFIG = Dynaconf(
    envvar_prefix="GFIBOT",
    settings_files=[
        os.path.join(BASE_DIR, "settings.toml"),
        os.path.join(BASE_DIR, ".secrets.toml"),
    ],
    environments=True,
    env_switcher="GFIBOT_ENV",
)

# load tokens
TOKENS: List[str] = []
TOKENS = CONFIG.get("github.tokens", [])

if (BASE_DIR / "tokens.txt").exists():
    with open(BASE_DIR / "tokens.txt") as f:
        TOKENS.extend(f.read().splitlines())

if not TOKENS:
    logging.error(
        "No tokens found in %s or %s",
        BASE_DIR / "tokens.txt",
        BASE_DIR / ".secrets.toml",
    )

# download nltk data if not exists
for corpus_data in ["wordnet", "omw-1.4", "stopwords"]:
    try:
        nltk.data.find(f"corpora/{corpus_data}.zip")
    except LookupError:
        nltk.download(corpus_data)


logging.info("Running in %s environment", CONFIG.get("ENV_FOR_DYNACONF"))
