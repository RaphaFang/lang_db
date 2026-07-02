"""DB glue for the FSRS scheduler (widget_srs/fsrs.py).

  due_cards(conn)              -> what to review today (new + overdue)
  apply_review(conn, id, r)    -> run FSRS, update learning_t, log to review_log_t
  train(conn)                  -> fit weights on review_log_t, save weights.json

Weights load order: weights.json if present (your trained ones) else DEFAULT_W.
Uses the same psycopg connection settings as main.py.
"""

import os
import json
from datetime import datetime, timedelta, timezone

import psycopg
from . import fsrs

WEIGHTS_PATH = os.path.join(os.path.dirname(__file__), "weights.json")


def get_conn():
    return psycopg.connect(
        host="127.0.0.1",
        port=5432,
        dbname="lang",
        user=os.environ.get("PSQL_USER", ""),
        password=os.environ.get("DB_PASSWORD", ""),
    )


def load_weights():
    if os.path.isfile(WEIGHTS_PATH):
        with open(WEIGHTS_PATH) as f:
            return json.load(f)
    return fsrs.DEFAULT_W


def due_cards(conn, lang=None, limit=50):
    """Words to review now: never-reviewed (no learning_t row) or past due."""
    sql = """
        SELECT v.id, v.word, v.lang, l.next_review_date, l.stability
        FROM voc_t v
        LEFT JOIN learning_t l ON l.word_id = v.id
        WHERE (l.next_review_date IS NULL OR l.next_review_date <= CURRENT_DATE)
        {lang}
        ORDER BY l.next_review_date NULLS FIRST
        LIMIT %s
    """.format(lang="AND v.lang = %s" if lang else "")
    params = [lang, limit] if lang else [limit]
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def apply_review(conn, word_id, rating, request_retention=0.9, now=None):
    """Score one review and persist: learning_t (state) + review_log_t (history)."""
    now = now or datetime.now(timezone.utc)
    w = load_weights()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT difficulty, stability, state, last_review_at FROM learning_t WHERE word_id = %s",
            (word_id,),
        )
        row = cur.fetchone()
        if row and row[1]:
            d0, s0, state0, last = row
            elapsed = max(0, (now - last).days) if last else 0
            card = {"difficulty": d0, "stability": s0, "state": state0}
        else:
            elapsed, s0 = 0, None
            card = {}

        out = fsrs.review(
            card, rating, elapsed, w=w, request_retention=request_retention
        )
        next_date = now.date() + timedelta(days=out["interval"])

        cur.execute(
            """
            INSERT INTO learning_t (word_id, difficulty, stability, state,
                                    next_review_date, last_review_at, updated_time)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (word_id) DO UPDATE SET
                difficulty       = EXCLUDED.difficulty,
                stability        = EXCLUDED.stability,
                state            = EXCLUDED.state,
                next_review_date = EXCLUDED.next_review_date,
                last_review_at   = EXCLUDED.last_review_at,
                updated_time     = NOW()
            """,
            (
                word_id,
                out["difficulty"],
                out["stability"],
                out["state"],
                next_date,
                now,
            ),
        )
        cur.execute(
            """INSERT INTO review_log_t (word_id, rating, elapsed_days, stability_before, reviewed_at)
               VALUES (%s, %s, %s, %s, %s)""",
            (word_id, rating, elapsed, s0, now),
        )
    conn.commit()
    return out


def load_sequences(conn):
    """Per-card review history in order -> [[(rating, elapsed_days), ...], ...]."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT word_id, rating, elapsed_days FROM review_log_t ORDER BY word_id, reviewed_at"
        )
        rows = cur.fetchall()
    seqs, cur_id, cur_seq = [], None, []
    for wid, rating, elapsed in rows:
        if wid != cur_id:
            if cur_seq:
                seqs.append(cur_seq)
            cur_id, cur_seq = wid, []
        cur_seq.append((rating, elapsed))
    if cur_seq:
        seqs.append(cur_seq)
    return seqs


def train(conn, save=True):
    """Fit weights on your review history, save to weights.json. Returns (w, loss)."""
    seqs = load_sequences(conn)
    total = sum(len(s) for s in seqs)
    if total < 1000:
        print(
            f"WARN: only {total} reviews logged; FSRS wants ~1000+ before the fit is trustworthy."
        )
    w, loss = fsrs.optimize(seqs)
    if save:
        with open(WEIGHTS_PATH, "w") as f:
            json.dump(w, f)
    return w, loss
