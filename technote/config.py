import os
from pathlib import Path

from . import __version__
from .helpers import cache_dir, data_dir

APP_DIR = Path(__file__).resolve().parent
PROJECT_DIR = Path(__file__).resolve().parent.parent

ENV = os.environ.get("TECHNOTE_ENV", "prod").strip().lower()
IS_DEV = ENV in {"dev", "development"}

APP_MODULE = "technote.app:app"
APP_NAME = "TechNote"
APP_DESCRIPTION = "A self-hosted Markdown-based note-taking app"
MODULE_NAME = "technote"
NAMESPACE = "ir.miladnia.technote"

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8087

DATA_DIR = (
    PROJECT_DIR / ".dev/data"
    if IS_DEV
    else data_dir(app_name=MODULE_NAME, env_name="TECHNOTE_DATA_DIR")
)
DB_FILE = DATA_DIR / "technote.db"
DB_SCHEMA_FILE = APP_DIR / "resources/schema.sql"

CACHE_DIR = (
    PROJECT_DIR / ".dev/cache"
    if IS_DEV
    else cache_dir(app_name=MODULE_NAME, env_name="TECHNOTE_CACHE_DIR")
)
HTML_CACHE_DIR = CACHE_DIR / "html" / __version__
CACHE_ENABLED = True

PANDOC_TEMPLATE = APP_DIR / "templates/pandoc.html"
VITE_MANIFEST_FILE = APP_DIR / "static/dist/.vite/manifest.json"
DEV_VITE_MAIN_FILE = "/src/web-client/main.jsx"
EXAMPLE_NOTES_DIR = APP_DIR / "example_tech_notes"
