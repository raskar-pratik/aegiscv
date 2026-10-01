"""SQLite scan and registry persistence with explicit connection lifetime."""
import json
import sqlite3
from contextlib import contextmanager


class Store:
    def __init__(self,path):
        self.path=path
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS scans (id TEXT PRIMARY KEY, status TEXT, data TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS registry (id TEXT PRIMARY KEY, kind TEXT, data TEXT)')
            db.execute("UPDATE scans SET status='FAILED', data=? WHERE status NOT IN ('COMPLETE','FAILED')",(json.dumps({'error':'Process interrupted; resubmit scan'}),))

    @contextmanager
    def connect(self):
        db=sqlite3.connect(self.path,timeout=30)
        try:
            with db: yield db
        finally: db.close()

    def set_scan(self,id,status,data):
        with self.connect() as db: db.execute('INSERT OR REPLACE INTO scans VALUES (?,?,?)',(id,status,json.dumps(data)))

    def scans(self,id=None):
        with self.connect() as db:
            rows=db.execute('SELECT id,status,data FROM scans'+(' WHERE id=?' if id else ' ORDER BY rowid DESC'),(id,) if id else ()).fetchall()
        return [{'id':i,'status':s,'data':json.loads(d)} for i,s,d in rows]

    def register(self,id,kind,data):
        with self.connect() as db: db.execute('INSERT INTO registry VALUES (?,?,?)',(id,kind,json.dumps(data)))

    def registry(self,kind,id=None):
        with self.connect() as db:
            rows=db.execute('SELECT id,data FROM registry WHERE kind=?'+(' AND id=?' if id else ''),(kind,id) if id else (kind,)).fetchall()
        return [{'id':i,**json.loads(d)} for i,d in rows]
