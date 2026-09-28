CREATE TABLE IF NOT EXISTS records (
    rowid INTEGER PRIMARY KEY,
    kind TEXT NOT NULL CHECK(kind IN ('facts','memories','entities','edges','blueprints','states')),
    project TEXT NOT NULL,
    id TEXT NOT NULL,
    data TEXT NOT NULL CHECK(json_valid(data)),
    content TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL DEFAULT 'agent',
    superseded INTEGER NOT NULL DEFAULT 0,
    UNIQUE(kind, project, id)
);
CREATE INDEX IF NOT EXISTS records_project_kind ON records(project, kind);
