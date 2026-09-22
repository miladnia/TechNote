# TechNote

**TechNote lets you access your local Markdown files in your browser.**

Add the directories that contain your Markdown files (`.md`), and you'll be able to read them rendered in your browser. You can also search across all your files, or edit them directly in Markdown.

It's a lightweight app built with Python and React. It's named TechNote because I use it as a knowledge base for my tech notes, which are actually a bunch of Markdown files (~150) in a single directory.

![TechNote preview](https://raw.githubusercontent.com/miladnia/TechNote/refs/tags/v0.2.0/docs/technote_note_preview.png)

## 🚀 Get Started

### How to install

1. Install TechNote via `pipx`:

```sh
pipx install pytechnote
```

2. Set up TechNote to start automatically on login:

```sh
technote autostart enable
```

> [!TIP]
> You can also use `technote run` to run TechNote directly in your terminal without enabling autostart.

### How to use

First, open http://localhost:8087. Select **Open Directory** in the sidebar and choose a directory containing your Markdown files, or even an empty directory. Once you open the directory, you'll see a list of your files in the sidebar. Select any file to see it rendered. You can also edit your files or create new files right in the browser.

Select the options button next to the directory's name in the sidebar to create new files or open other directories.

---

## ✨ How It Works

### What technologies are used?

The backend is written in Python, using [Flask][flask] and [Gunicorn][gunicorn] to handle HTTP requests, while parts of the UI are built with [React][react].

### How does it render Markdown to HTML?

We use [Pandoc][pandoc] and [Pypandoc][pypandoc] to render the Markdown files.

### Is there any caching?

We render each Markdown file once and reuse the result the next time you access that file. The cached version is updated whenever the file changes on the filesystem.

### Why does it need a database?

We use a lightweight [SQLite][sqlite] database to store minimal metadata — such as unique IDs and display names for notes — and the paths to selected directories.

### How to build and run for development?

```sh
git clone https://github.com/miladnia/technote.git
cd technote
make env # Prepare the development environment
```

Use `make dev` to run the frontend and backend development servers at the same time, and then open http://127.0.0.1:5000/.

This is also possible to run TechNote without installation using `make run`.

**Requirements:**

- Python `>= 3.10`
- Node `>= 18.20`
- [make][gnu_make]

---

## ⚖️ License

TechNote is open-source software licensed under the [MIT License](./LICENSE).


[flask]: https://github.com/pallets/flask
[gunicorn]: https://github.com/benoitc/gunicorn
[react]: https://github.com/facebook/react
[pandoc]: https://github.com/jgm/pandoc
[pypandoc]: https://github.com/JessicaTegner/pypandoc
[sqlite]: https://github.com/sqlite/sqlite
[gnu_make]: https://www.gnu.org/software/make/
