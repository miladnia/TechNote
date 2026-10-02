import json
import os
import sqlite3
from contextlib import closing
from hashlib import md5
from pathlib import Path

from flask import Response, g, jsonify, render_template, url_for
from platformdirs import user_cache_dir, user_data_dir


def data_dir(app_name: str, env_name: str) -> Path:
    # 'appauthor=False' avoids the extra Author\App nesting on Windows
    default_dir = Path(user_data_dir(app_name, appauthor=False))
    return read_env_dir(env_name, default=default_dir)


def cache_dir(app_name: str, env_name: str) -> Path:
    default_dir = Path(user_cache_dir(app_name, appauthor=False))
    return read_env_dir(env_name, default=default_dir)


def read_env_dir(env_name: str, default: Path) -> Path:
    value = os.environ.get(env_name)
    if value:
        # Convert the value to a clean absolute path
        return Path(value).expanduser().resolve()
    return default


def init_db(db_file: str, schema_file: str) -> None:
    Path(db_file).parent.mkdir(parents=True, exist_ok=True)
    schema = Path(schema_file).read_text(encoding="utf-8")
    with closing(sqlite3.connect(db_file, timeout=10)) as conn:
        conn.executescript(schema)


def get_db(db_file: Path):
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(db_file)
    db.row_factory = sqlite3.Row
    return db


def query_db(db_file: Path, query: str, args=(), one=False):
    cur = get_db(db_file).execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv


def close_db():
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


def release_resources():
    close_db()


def dbhash(string: str) -> str:
    return md5(string.encode()).hexdigest()


def api_response(result: any | None = None, message: str | None = None) -> Response:
    return jsonify(
        {
            "result": result,
            "message": message,
        }
    )


def render_notfound() -> str:
    return render_alert("Oops! The page you have requested was not found.", 404)


def render_badrequest() -> str:
    return render_alert("Bad request!", 400)


def render_alert(message: str, code: int) -> str:
    """Render an alert message."""
    return render_template("alert.html", message=message, code=code), code


def render_vite_dev_assets(main_file_path: str) -> str:
    return f"""
        <script type="module">
            import RefreshRuntime from 'http://localhost:5173/@react-refresh'
            RefreshRuntime.injectIntoGlobalHook(window)
            window.$RefreshReg$ = () => {{}}
            window.$RefreshSig$ = () => (type) => type
            window.__vite_plugin_react_preamble_installed__ = true
        </script>
        <script type="module" src="http://localhost:5173/@vite/client"></script>
        <script type="module" src="http://localhost:5173{main_file_path}"></script>
    """


def render_vite_prod_assets(manifest_file: Path) -> str:
    assets = []
    with open(manifest_file) as f:
        manifest = json.load(f)
    for v in manifest.values():
        if v.get("isEntry", False):
            for css in v.get("css", []):
                asset_url = url_for("static", filename=f"dist/{css}")
                assets.append(f'<link rel="stylesheet" href="{asset_url}">')
            asset_url = url_for("static", filename=f"dist/{v.get('file')}")
            assets.append(f'<script type="module" src="{asset_url}" defer></script>')
    return "\n".join(assets)


def prettify(name: str) -> str:
    """Create a pretty title."""
    return name.replace("_", " ").replace("-", " ").replace(".", " ").title()
