CREATE VIRTUAL TABLE IF NOT EXISTS records_fts USING fts5(content, source, project, content='records', content_rowid='rowid', tokenize='porter unicode61');
CREATE TRIGGER IF NOT EXISTS records_ai AFTER INSERT ON records WHEN new.kind='memories' BEGIN
 INSERT INTO records_fts(rowid, content, source, project) VALUES(new.rowid, new.content, new.source, new.project);
END;
CREATE TRIGGER IF NOT EXISTS records_ad AFTER DELETE ON records WHEN old.kind='memories' BEGIN
 INSERT INTO records_fts(records_fts, rowid, content, source, project) VALUES('delete', old.rowid, old.content, old.source, old.project);
END;
CREATE TRIGGER IF NOT EXISTS records_au AFTER UPDATE ON records WHEN new.kind='memories' BEGIN
 INSERT INTO records_fts(records_fts, rowid, content, source, project) VALUES('delete', old.rowid, old.content, old.source, old.project);
 INSERT INTO records_fts(rowid, content, source, project) VALUES(new.rowid, new.content, new.source, new.project);
END;
INSERT INTO records_fts(rowid,content,source,project) SELECT rowid,content,source,project FROM records WHERE kind='memories';
