import re
from pathlib import Path
from sqlite3 import IntegrityError

import pypandoc as pandoc
from flask import url_for
from markupsafe import Markup

from .config import (
    CACHE_ENABLED,
    DB_FILE,
    EXAMPLE_NOTES_DIR,
    HTML_CACHE_DIR,
    PANDOC_TEMPLATE,
)
from .dtos import DirectoryDTO, NavigatorDTO
from .entities import Directory, Note
from .helpers import dbhash, get_db, prettify, query_db


def list_all() -> NavigatorDTO:
    query = """
    SELECT *
      FROM directories
     WHERE is_directory_hidden = 0
     ORDER BY directory_name
    """
    directory_rows = _query(query)
    if not directory_rows:
        return {}

    directories = [Directory.from_model(row) for row in directory_rows]
    if len(directories) == 1:
        return NavigatorDTO(
            directory=DirectoryDTO.from_domain(
                directory=directories[0],
                notes=find_notes_by_directory(directories[0].id),
            )
        )
    return NavigatorDTO(
        directory_list=[
            DirectoryDTO.from_domain(directory) for directory in directories
        ]
    )


def list_directory(directory_id: str) -> NavigatorDTO:
    return NavigatorDTO(
        directory=DirectoryDTO.from_domain(
            directory=get_directory(directory_id),
            notes=find_notes_by_directory(directory_id),
        )
    )


def add_directory(directory_path: str) -> int:
    """
    Add the directory with all the `.md` files to the database
    and return the id of the directory.
    """

    if not directory_path:
        raise ValueError("Empty value for directory.")

    dir = Path(directory_path)
    # Validate the directory
    if not dir.is_dir():
        raise ValueError(f"Invalid directory: '{directory_path}'")
    # Get all the Markdown files located in the directory
    md_files = dir.glob("*.md")
    # Create a unique hash for the directory
    directory_id = dbhash(str(dir.resolve()))

    with _db() as db:
        # Create a new directory in the database
        try:
            query = """
            INSERT INTO directories (directory_id, directory_path, directory_name)
            VALUES (?, ?, ?)
            """
            db.execute(
                query,
                (
                    directory_id,
                    str(dir.resolve()),
                    dir.stem,
                ),
            )
        except IntegrityError:
            # The directory already exists in the database just ensure it is not hidden
            query = """
            UPDATE directories SET is_directory_hidden = 0 WHERE directory_id = ?
            """
            db.execute(query, (directory_id,))
            return directory_id
        # Create a new note with a unique hash and a pretty name in the database
        query = """
        INSERT INTO notes (
            note_id,
            note_pretty_name,
            note_filename,
            note_directory
        )
        VALUES (?, ?, ?, ?)
        """
        db.executemany(
            query,
            [
                (
                    dbhash(str(f.resolve())),
                    prettify(f.stem),
                    f.name,
                    directory_id,
                )
                for f in md_files
            ],
        )
    return directory_id


def add_example_notes_directory() -> int:
    return add_directory(EXAMPLE_NOTES_DIR)


def hide_directory(directory_id):
    query = """
    UPDATE directories SET is_directory_hidden = 1 WHERE directory_id = ?
    """
    with _db() as db:
        db.execute(query, (directory_id,))


def find_all() -> list[Note]:
    db_rows = _query(
        "SELECT * FROM notes JOIN directories ON note_directory = directory_id ORDER BY note_directory, note_pretty_name"
    )
    return [Note.from_model(row) for row in db_rows]


def find_notes_by_directory(directory_id: str) -> list[Note]:
    note_rows = _query(
        "SELECT * FROM notes JOIN directories ON note_directory = directory_id WHERE directory_id = ? ORDER BY note_pretty_name",
        (directory_id,),
    )
    return [Note.from_model(row) for row in note_rows]


def get_note(
    note_id: str, with_content: bool = False, with_preview: bool = False
) -> Note:
    note_row = _query(
        "SELECT * FROM notes JOIN directories ON note_directory = directory_id WHERE note_id = ?",
        (note_id,),
        one=True,
    )
    if note_row is None:
        raise ValueError("Note not found.")
    note = Note.from_model(note_row)
    if with_content:
        note.content = note.path.read_text()
    if with_preview:
        note.preview = Markup(_render_note_content(note))
    return note


def get_directory(directory_id: str) -> Directory:
    query = """
    SELECT * FROM directories WHERE directory_id = ?
    """
    db_row = _query(query, (directory_id,), one=True)
    if db_row is None:
        raise ValueError("Directory not found.")
    return Directory.from_model(db_row)


def write_note_content(note_id: str, content: str):
    note = get_note(note_id)
    note.path.write_text(content)


def create_new_note(content: str, filename: str, directory_id: str) -> Note:
    if not filename:
        raise ValueError("Empty value for filename.")
    directory = get_directory(directory_id)
    note_path = (directory.path / filename).with_suffix(".md")
    # Create a new file but fail if the file already exists
    with note_path.open(mode="x") as f:
        f.write(content)
    # Create a new record for the new note in the database
    note_id = dbhash(str(note_path.resolve()))
    note_pretty_name = prettify(note_path.stem)
    with _db() as db:
        db.execute(
            "INSERT INTO notes(note_id, note_pretty_name, note_filename, note_directory) VALUES (?, ?, ?, ?)",
            (
                note_id,
                note_pretty_name,
                note_path.name,
                directory_id,
            ),
        )
    note = get_note(note_id)
    return note


def search(query: str):
    query = query.strip()
    if not query:
        return []
    pattern = re.compile(rf"{re.escape(query)}")
    results = []
    for note in find_all():
        if not note.path.is_file():
            continue
        with note.path.open("r", encoding="utf-8") as f:
            for line in f:
                if not pattern.search(line):
                    continue
                # In some cases like reference links it could be empty
                plain_text = _md_to_text(line)
                if not plain_text:
                    continue
                if not results or note.path.name != results[-1]["source"]:
                    results.append(
                        {
                            "source": note.path.name,
                            "source_url": url_for("note", note_id=note.id),
                            "occurrences": [],
                        }
                    )
                results[-1]["occurrences"].append(plain_text)
    return results


def list_filesystem(directory: str) -> dict:
    """List filesystem directory."""

    home = Path.home().resolve()
    # Normalize the path (e.g. resolve ".." components)
    cwd = (home / directory).resolve()

    if not cwd.is_dir():
        raise ValueError(f"Not found: {cwd}")

    # Ensure cwd is inside home
    if not cwd.is_relative_to(home):
        raise ValueError(f"Access denied: {cwd}")

    def create_entry(name, path, real_path, type_="directory"):
        return {
            "name": name,
            "path": str(path),
            "real_path": str(real_path),
            "type": type_,
        }

    relative_path = cwd.relative_to(home)

    current_directory = create_entry(".", relative_path, cwd)
    parent_directory = create_entry("..", relative_path.parent, cwd.parent)
    sub_directories = sorted(
        [
            create_entry(p.name, relative_path / p.name, p.resolve())
            for p in cwd.iterdir()
            if p.is_dir() and not p.name.startswith(".")
        ],
        key=lambda entry: entry["name"],
    )
    markdown_files = sorted(
        [create_entry(p.name, "", p.resolve(), type_="file") for p in cwd.glob("*.md")],
        key=lambda entry: entry["name"],
    )

    return {
        "current_directory": current_directory,
        "parent_directory": parent_directory,
        "directories": sub_directories,
        "files": markdown_files,
    }


def _render_note_content(note: Note) -> str:
    if not note.path.is_file():
        return ""

    if not CACHE_ENABLED:
        return _md_to_html(note.path)

    cache_file = HTML_CACHE_DIR / note.id
    cache_expired = (
        not cache_file.is_file()
        or cache_file.stat().st_mtime <= note.path.stat().st_mtime
    )
    # Generate a new cache
    if cache_expired:
        html_content = _md_to_html(note.path)
        # Make sure the cache directory exists
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(html_content)
        return html_content

    return cache_file.read_text()


def _md_to_html(source_file) -> str:
    """Convert a Markdown file to an HTML document"""
    return pandoc.convert_file(
        source_file,
        format="markdown",
        to="html5",
        extra_args=[
            "--standalone",
            f"--template={PANDOC_TEMPLATE}",
            "--table-of-contents",
            "--toc-depth=2",
        ],
    )


def _md_to_text(markdown: str) -> str:
    """Convert Markdown text to plain text"""
    text = pandoc.convert_text(
        markdown, format="markdown", to="plain", extra_args={"--wrap=none"}
    )
    # Convert reference links `[title][ref]` to plain text `title`
    text = re.sub(r"\[([^\]]+)\]\[[^\]]*\]", r"\1", text)
    # Remove spaces, list symbols, table borders
    text = text.strip(" \n-*+|")
    return text


def _db():
    return get_db(DB_FILE)


def _query(query: str, args=(), one=False):
    return query_db(DB_FILE, query, args, one)
