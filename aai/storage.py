import sqlite3,json,time,uuid
from pathlib import Path
from contextlib import contextmanager
class Store:
    def __init__(self,path):
        self.path=str(path);Path(path).parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY,created REAL,payload TEXT);
            CREATE TABLE IF NOT EXISTS calls(id TEXT PRIMARY KEY,run_id TEXT,model TEXT,created REAL,reserved INTEGER,payload TEXT);
            CREATE TABLE IF NOT EXISTS states(name TEXT PRIMARY KEY,payload TEXT);
            CREATE TABLE IF NOT EXISTS feedback(run_id TEXT PRIMARY KEY,quality REAL,reward REAL);
            """)
    @contextmanager
    def connect(self):
        db=sqlite3.connect(self.path,timeout=30)
        try:
            db.execute('PRAGMA journal_mode=WAL')
            with db: yield db
        finally: db.close()
    def save(self,run):
        with self.connect() as db: db.execute('INSERT OR REPLACE INTO runs VALUES(?,?,?)',(run['id'],run['created'],json.dumps(run)))
    def get(self,run_id):
        with self.connect() as db: row=db.execute('SELECT payload FROM runs WHERE id=?',(run_id,)).fetchone()
        return json.loads(row[0]) if row else None
    def recent(self,limit=100):
        with self.connect() as db: rows=db.execute('SELECT payload FROM runs ORDER BY created DESC LIMIT ?',(limit,)).fetchall()
        return [json.loads(r[0]) for r in rows]
    def calls(self,run_id):
        with self.connect() as db: rows=db.execute('SELECT payload FROM calls WHERE run_id=? ORDER BY created',(run_id,)).fetchall()
        return [json.loads(r[0]) for r in rows]
    def state(self,name):
        with self.connect() as db: row=db.execute('SELECT payload FROM states WHERE name=?',(name,)).fetchone()
        return json.loads(row[0]) if row else None
    def save_state(self,name,value):
        with self.connect() as db: db.execute('INSERT OR REPLACE INTO states VALUES(?,?)',(name,json.dumps(value)))
