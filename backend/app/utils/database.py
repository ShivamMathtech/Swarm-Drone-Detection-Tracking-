import json
import sqlite3
from app.config import DATA

class Database:
    def __init__(self, path=None):
        self.db=sqlite3.connect(path or DATA/"research.sqlite3",timeout=10)
        self.db.row_factory=sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS configuration(id INTEGER PRIMARY KEY, payload TEXT);
        CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY, source TEXT, started REAL, ended REAL);
        CREATE TABLE IF NOT EXISTS tracks(session_id TEXT,track_id INTEGER,class_name TEXT,first_seen REAL,last_seen REAL,status TEXT,PRIMARY KEY(session_id,track_id));
        CREATE TABLE IF NOT EXISTS detections(id INTEGER PRIMARY KEY,session_id TEXT,track_id INTEGER,timestamp REAL,frame_id INTEGER,source_frame INTEGER,source_time REAL,x1 REAL,y1 REAL,x2 REAL,y2 REAL,confidence REAL);
        CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,session_id TEXT,timestamp REAL,message TEXT);
        CREATE INDEX IF NOT EXISTS detections_session ON detections(session_id);
        """)
    def save_config(self, config):
        self.db.execute("INSERT OR REPLACE INTO configuration VALUES(1,?)",(config.model_dump_json(),));self.db.commit()
    def load_config(self):
        row=self.db.execute("SELECT payload FROM configuration WHERE id=1").fetchone()
        return json.loads(row[0]) if row else {}
    def start(self,sid,source,now):
        self.db.execute("INSERT INTO sessions VALUES(?,?,?,NULL)",(sid,source,now));self.db.commit()
    def record(self,sid,frame_id,source_frame,source_time,now,targets,events):
        for t in targets:
            self.db.execute("INSERT INTO tracks VALUES(?,?,?,?,?,?) ON CONFLICT(session_id,track_id) DO UPDATE SET last_seen=excluded.last_seen,status=excluded.status",(sid,t['track_id'],t['class_name'],t['first_seen'],t['last_seen'],t['status']))
            if t['status']!='LOST':
                self.db.execute("INSERT INTO detections(session_id,track_id,timestamp,frame_id,source_frame,source_time,x1,y1,x2,y2,confidence) VALUES(?,?,?,?,?,?,?,?,?,?,?)",(sid,t['track_id'],now,frame_id,source_frame,source_time,*t['bbox'],t['confidence']))
        for message in events:
            self.db.execute("INSERT INTO events(session_id,timestamp,message) VALUES(?,?,?)",(sid,now,message))
            if message.endswith(" expired"):
                tid=int(message.split()[0][3:]);self.db.execute("UPDATE tracks SET status='EXPIRED' WHERE session_id=? AND track_id=?",(sid,tid))
        self.db.commit()
    def end(self,sid,now):
        self.db.execute("UPDATE sessions SET ended=? WHERE id=?",(now,sid))
        self.db.execute("UPDATE tracks SET status='ENDED' WHERE session_id=? AND status!='EXPIRED'",(sid,));self.db.commit()
    def close(self): self.db.close()
