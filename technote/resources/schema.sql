BEGIN;

CREATE TABLE IF NOT EXISTS directories(
    directory_id        TEXT    PRIMARY KEY NOT NULL,
    directory_path      TEXT    NOT NULL UNIQUE,
    directory_name      TEXT    NOT NULL,
    is_directory_hidden INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS notes(
    note_id          TEXT    PRIMARY KEY NOT NULL,
    note_pretty_name TEXT    NOT NULL,
    note_filename    TEXT    NOT NULL,
    note_directory   TEXT    NOT NULL,
    FOREIGN KEY (note_directory)
        REFERENCES directories(directory_id)
);

COMMIT;
