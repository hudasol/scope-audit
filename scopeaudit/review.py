"""Append only review log with a hash chain.

Every observation moves through a fixed lifecycle: ai_candidate, human_review,
adjudication, approved, exported. A correction never overwrites an earlier record: it
appends a new one that references the previous record. Each record stores the hash of
the one before it, so any later edit of history is detectable by verify_chain().
Role gates: reviewers may record decisions, only an approver may approve, only an
administrator may export.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone

STATES = ["ai_candidate", "human_review", "adjudication", "approved", "exported"]
ROLES = {"reviewer": {"ai_candidate", "human_review", "adjudication"},
         "approver": {"ai_candidate", "human_review", "adjudication", "approved"},
         "admin": set(STATES)}
ALLOWED_NEXT = {None: {"ai_candidate"},
                "ai_candidate": {"human_review"},
                "human_review": {"human_review", "adjudication", "approved"},
                "adjudication": {"human_review", "approved"},
                "approved": {"human_review", "exported"},
                "exported": {"human_review"}}

SCHEMA = """
CREATE TABLE IF NOT EXISTS log (
  seq INTEGER PRIMARY KEY AUTOINCREMENT,
  observation_id TEXT NOT NULL,
  state TEXT NOT NULL,
  actor TEXT NOT NULL,
  role TEXT NOT NULL,
  timestamp_utc TEXT NOT NULL,
  payload TEXT NOT NULL,
  prev_hash TEXT NOT NULL,
  record_hash TEXT NOT NULL
);
"""
GENESIS = "0" * 64


class ReviewError(Exception):
    pass


def _hash(prev: str, obs: str, state: str, actor: str, role: str, ts: str, payload: str) -> str:
    return hashlib.sha256("|".join([prev, obs, state, actor, role, ts, payload]).encode("utf8")).hexdigest()


class ReviewLog:
    def __init__(self, path=":memory:"):
        self.con = sqlite3.connect(path)
        self.con.execute(SCHEMA)
        self.con.commit()

    def _last_hash(self) -> str:
        r = self.con.execute("SELECT record_hash FROM log ORDER BY seq DESC LIMIT 1").fetchone()
        return r[0] if r else GENESIS

    def current_state(self, observation_id: str):
        r = self.con.execute("SELECT state FROM log WHERE observation_id=? ORDER BY seq DESC LIMIT 1",
                             (observation_id,)).fetchone()
        return r[0] if r else None

    def append(self, observation_id: str, state: str, actor: str, role: str, payload: dict | None = None,
               timestamp_utc: str | None = None) -> str:
        if state not in STATES:
            raise ReviewError(f"Unknown state {state}.")
        if role not in ROLES or state not in ROLES[role]:
            raise ReviewError(f"Role {role} may not record state {state}.")
        cur = self.current_state(observation_id)
        if state not in ALLOWED_NEXT[cur]:
            raise ReviewError(f"Transition from {cur} to {state} is not allowed.")
        if state == "ai_candidate" and role != "admin" and payload is not None and payload.get("source") != "detector":
            raise ReviewError("An AI candidate must come from the detector.")
        ts = timestamp_utc or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        body = json.dumps(payload or {}, sort_keys=True)
        prev = self._last_hash()
        h = _hash(prev, observation_id, state, actor, role, ts, body)
        self.con.execute("INSERT INTO log (observation_id,state,actor,role,timestamp_utc,payload,prev_hash,record_hash) "
                         "VALUES (?,?,?,?,?,?,?,?)", (observation_id, state, actor, role, ts, body, prev, h))
        self.con.commit()
        return h

    def history(self, observation_id: str) -> list[dict]:
        cur = self.con.execute("SELECT seq,observation_id,state,actor,role,timestamp_utc,payload FROM log "
                               "WHERE observation_id=? ORDER BY seq", (observation_id,))
        keys = ["seq", "observation_id", "state", "actor", "role", "timestamp_utc", "payload"]
        out = [dict(zip(keys, r)) for r in cur.fetchall()]
        for r in out:
            r["payload"] = json.loads(r["payload"])
        return out

    def latest(self, state: str | None = None) -> list[dict]:
        """Latest record for every observation, optionally filtered by state."""
        rows = self.con.execute("SELECT observation_id, MAX(seq) FROM log GROUP BY observation_id").fetchall()
        out = []
        for obs, seq in rows:
            r = self.con.execute("SELECT seq,observation_id,state,actor,role,timestamp_utc,payload FROM log "
                                 "WHERE seq=?", (seq,)).fetchone()
            rec = dict(zip(["seq", "observation_id", "state", "actor", "role", "timestamp_utc", "payload"], r))
            rec["payload"] = json.loads(rec["payload"])
            if state is None or rec["state"] == state:
                out.append(rec)
        return out

    def verify_chain(self) -> tuple[bool, int | None]:
        prev = GENESIS
        for seq, obs, st, actor, role, ts, payload, ph, rh in self.con.execute(
                "SELECT seq,observation_id,state,actor,role,timestamp_utc,payload,prev_hash,record_hash "
                "FROM log ORDER BY seq"):
            if ph != prev or _hash(prev, obs, st, actor, role, ts, payload) != rh:
                return False, seq
            prev = rh
        return True, None
