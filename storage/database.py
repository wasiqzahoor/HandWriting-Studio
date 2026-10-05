"""SQLite storage: documents, batch jobs/records, exports, key-value."""
import sqlite3
import threading
import time


_SCHEMA = """
CREATE TABLE IF NOT EXISTS documents(
  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, template TEXT,
  profile TEXT, seed INTEGER, created REAL, status TEXT, location TEXT);
CREATE TABLE IF NOT EXISTS batch_jobs(
  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, template TEXT,
  profile TEXT, source TEXT, total INTEGER, done INTEGER DEFAULT 0,
  ok INTEGER DEFAULT 0, failed INTEGER DEFAULT 0,
  status TEXT DEFAULT 'ready', created REAL, outdir TEXT);
CREATE TABLE IF NOT EXISTS batch_records(
  job_id INTEGER, idx INTEGER, status TEXT DEFAULT 'pending',
  error TEXT DEFAULT '', outputs TEXT DEFAULT '',
  PRIMARY KEY(job_id, idx));
CREATE TABLE IF NOT EXISTS exports(
  id INTEGER PRIMARY KEY AUTOINCREMENT, filename TEXT, doc_type TEXT,
  template TEXT, profile TEXT, created REAL, format TEXT,
  status TEXT, location TEXT);
CREATE TABLE IF NOT EXISTS kv(key TEXT PRIMARY KEY, value TEXT);
"""


class Database:
    def __init__(self, path):
        self.path = path
        self._lock = threading.Lock()
        with self._connect() as c:
            c.executescript(_SCHEMA)

    def _connect(self):
        c = sqlite3.connect(self.path, check_same_thread=False)
        c.row_factory = sqlite3.Row
        return c

    def _exec(self, sql, args=(), fetch=None):
        with self._lock:
            with self._connect() as c:
                cur = c.execute(sql, args)
                if fetch == "one":
                    return cur.fetchone()
                if fetch == "all":
                    return cur.fetchall()
                return cur.lastrowid

    # ---- documents ----
    def add_document(self, name, template, profile, seed, status, location):
        return self._exec(
            "INSERT INTO documents(name,template,profile,seed,created,status,location)"
            " VALUES(?,?,?,?,?,?,?)",
            (name, template, profile, seed, time.time(), status, location))

    def recent_documents(self, limit=8):
        return self._exec("SELECT * FROM documents ORDER BY id DESC LIMIT ?",
                          (limit,), fetch="all")

    def count(self, table):
        row = self._exec(f"SELECT COUNT(*) n FROM {table}", fetch="one")
        return row["n"] if row else 0

    # ---- batch ----
    def create_job(self, name, template, profile, source, total, outdir):
        return self._exec(
            "INSERT INTO batch_jobs(name,template,profile,source,total,created,outdir)"
            " VALUES(?,?,?,?,?,?,?)",
            (name, template, profile, source, total, time.time(), outdir))

    def init_records(self, job_id, total):
        with self._lock:
            with self._connect() as c:
                c.executemany(
                    "INSERT OR IGNORE INTO batch_records(job_id,idx) VALUES(?,?)",
                    [(job_id, i) for i in range(total)])

    def set_record(self, job_id, idx, status, error="", outputs=""):
        self._exec("UPDATE batch_records SET status=?,error=?,outputs=?"
                   " WHERE job_id=? AND idx=?", (status, error, outputs,
                                                 job_id, idx))

    def update_job_counts(self, job_id, done, ok, failed, status):
        self._exec("UPDATE batch_jobs SET done=?,ok=?,failed=?,status=?"
                   " WHERE id=?", (done, ok, failed, status, job_id))

    def set_job_status(self, job_id, status):
        self._exec("UPDATE batch_jobs SET status=? WHERE id=?", (status, job_id))

    def failed_records(self, job_id):
        return self._exec("SELECT idx,error FROM batch_records WHERE job_id=?"
                          " AND status='failed' ORDER BY idx",
                          (job_id,), fetch="all")

    def jobs(self, limit=50):
        return self._exec("SELECT * FROM batch_jobs ORDER BY id DESC LIMIT ?",
                          (limit,), fetch="all")

    def job(self, job_id):
        return self._exec("SELECT * FROM batch_jobs WHERE id=?", (job_id,),
                          fetch="one")

    # ---- exports ----
    def add_export(self, filename, doc_type, template, profile, fmt, status,
                   location):
        return self._exec(
            "INSERT INTO exports(filename,doc_type,template,profile,created,"
            "format,status,location) VALUES(?,?,?,?,?,?,?,?)",
            (filename, doc_type, template, profile, time.time(), fmt,
             status, location))

    def exports(self, limit=200):
        return self._exec("SELECT * FROM exports ORDER BY id DESC LIMIT ?",
                          (limit,), fetch="all")

    def delete_export(self, export_id):
        self._exec("DELETE FROM exports WHERE id=?", (export_id,))

    # ---- kv ----
    def kv_get(self, key, default=""):
        row = self._exec("SELECT value FROM kv WHERE key=?", (key,),
                         fetch="one")
        return row["value"] if row else default

    def kv_set(self, key, value):
        self._exec("INSERT INTO kv(key,value) VALUES(?,?)"
                   " ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                   (key, value))
