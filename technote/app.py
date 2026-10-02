from flask import Flask, jsonify, redirect, render_template, request, url_for

from .helpers import api_response, release_resources, render_notfound, render_badrequest, render_vite_assets
from . import services
from .dtos import NoteDTO

app = Flask(__name__)


@app.context_processor
def inject_helpers():
    def assets():
        return render_vite_assets(app.debug)
    return {"assets": assets}


@app.teardown_appcontext
def close_connection(exception):
    release_resources()


@app.route("/")
def index():
    return render_template("home.html")


@app.route("/notes/<note_id>")
def note(note_id):
    try:
        note = services.get_note(note_id, with_preview=True)
    except ValueError:
        return render_notfound()
    return render_template("note.html", note=note)


@app.route("/api/html_notes/<note_id>", methods=["GET"])
def html_note(note_id):
    try:
        note = services.get_note(note_id, with_preview=True)
    except ValueError:
        return "NOT FOUND"
    return api_response(note.preview)


@app.route("/plain_notes/<note_id>", methods=["GET", "POST"])
def plain_note(note_id):
    if "POST" == request.method:
        content = request.form.get("note_content")
        # Validate inputs
        if not content:
            return render_badrequest()
        # Update content of the note
        services.write_note_content(note_id, content)
        return redirect(url_for("note", note_id=note_id))
    try:
        note = services.get_note(note_id, with_content=True)
        return note.content
    except ValueError:
        return render_notfound()


@app.route("/api/notes", methods=["POST"])
def api_notes():
    content = request.json.get("note_content", "")
    filename = request.json.get("note_filename", "")
    directory_id = request.json.get("note_directory_id", None)
    try:
        note = services.create_new_note(
            content=content,
            filename=filename,
            directory_id=directory_id,
        )
    except ValueError as e:
        return api_response(message=str(e))
    return api_response({
        "note": NoteDTO.from_domain(note)
    })


@app.route("/list")
def list_all():
    return api_response( services.list_all() )


@app.route("/list/<directory_id>")
def list_directory(directory_id):
    return api_response(
        services.list_directory(directory_id)
    )


@app.route("/search")
def search():
    query = request.args.get("q")
    if not query:
        return render_badrequest()
    result = services.search(query)
    return jsonify(result)


@app.route("/open", methods=["POST"])
def open():
    directory_path = request.json.get("directory", "")
    try:
        directory_id = services.add_directory(directory_path)
    except ValueError as e:
        return api_response(message=str(e))
    return api_response(
        services.list_directory(directory_id)
    )


@app.route("/open_example_notes", methods=["POST"])
def open_example_notes():
    try:
        directory_id = services.add_example_notes_directory()
    except ValueError as e:
        return api_response(message=str(e))
    return api_response(
        services.list_directory(directory_id)
    )


@app.route("/close", methods=["POST"])
def close():
    directory_id = request.json.get("directory_id")
    services.hide_directory(directory_id)
    return api_response({})


@app.route("/explore/", defaults={'directory': ''})
@app.route("/explore/<path:directory>")
def explore(directory: str):
    return api_response(
        services.list_filesystem(directory)
    )
