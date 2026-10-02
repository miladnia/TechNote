from .config import DB_FILE, DB_SCHEMA_FILE
from .helpers import init_db


def prepare_environment() -> None:
    init_db(db_file=DB_FILE, schema_file=DB_SCHEMA_FILE)
