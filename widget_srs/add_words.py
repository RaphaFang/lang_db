"""Import new vocabulary via Claude, straight into voc_t.

Workflow (the words.txt inbox):
  1. jot new words in words.txt, one per line (blank lines / #comments ignored)
  2. run:  python3 -m widget_srs.add_words
     -> skips words already in voc_t
     -> asks Claude for definition + 2 example sentences per word
     -> inserts into voc_t (ON CONFLICT (word,lang) DO NOTHING)
     -> on full success, clears words.txt

Model is configurable via LANG_LLM_MODEL (default Haiku — plenty for this).
Needs ANTHROPIC_API_KEY in the environment.
"""

import os
import json

from pydantic import BaseModel
from . import review  # reuse the DB connection

WORDS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "words.txt")
MODEL = os.environ.get("LANG_LLM_MODEL", "claude-haiku-4-5")
LANG = (
    "en"  # ponytail: single language; add a per-line "word\tlang" tag if you add more
)

SYSTEM = """你是英文單字學習助手。使用者會給你一批英文單字或片語，你要為每一個產出學習卡片。

每張卡片欄位：
- word：更正拼字後的標準英文形式（若輸入有錯字，用正確拼法）
- pronunciation：英文 IPA 音標，例如 /dɪsˈkɑːd/
- definition：用繁體中文解釋語意、細微差異與典型用法，2~4 句；若輸入是錯字，開頭註明原字
- daily_sentence：一句偏「日常生活」的英文例句
- academic_sentence：一句偏「專業／學術」的英文例句
- synonyms：2~4 個同語言、意思相近的詞（純詞，不要解釋）
- antonyms：反義詞；沒有就給空陣列 []

例句要求：
- 難度中高、實用。不要太簡單（避免 "I have a cat." 這種），也不要艱澀到日常與學術都用不到。
- 每句自然、完整，能示範這個詞的典型用法。

務必依輸入順序輸出，且卡片數量與輸入單字數量完全相同。"""


class Card(BaseModel):
    word: str
    pronunciation: str = ""
    definition: str
    daily_sentence: str
    academic_sentence: str
    synonyms: list[str] = []
    antonyms: list[str] = []


class Batch(BaseModel):
    cards: list[Card]


def read_words(path=WORDS_FILE):
    """Non-empty, non-comment lines from the inbox."""
    if not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [
            ln.strip() for ln in f if ln.strip() and not ln.lstrip().startswith("#")
        ]


def existing_words(conn, words):
    """Subset of `words` (case-insensitive) already in voc_t."""
    if not words:
        return set()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT lower(word) FROM voc_t WHERE lang = %s AND lower(word) = ANY(%s)",
            (LANG, [w.lower() for w in words]),
        )
        return {r[0] for r in cur.fetchall()}


def generate(words):
    """Ask Claude for a card per word. Returns list[Card] (same order/count)."""
    import anthropic

    client = anthropic.Anthropic()
    prompt = "為以下單字各產生一張卡片：\n" + "\n".join(
        f"{i + 1}. {w}" for i, w in enumerate(words)
    )
    resp = client.messages.parse(
        model=MODEL,
        max_tokens=16000,
        system=SYSTEM,
        messages=[{"role": "user", "content": prompt}],
        output_format=Batch,
    )
    return resp.parsed_output.cards


def insert(conn, cards):
    from .embed import embed_word, _vec_literal  # 延後 import，--selfcheck 不必載模型

    rows = [
        (
            c.word.lower(),
            c.pronunciation,
            LANG,
            1,
            c.definition,
            json.dumps([c.daily_sentence, c.academic_sentence]),
            json.dumps({"synonyms": c.synonyms, "antonyms": c.antonyms}),
            _vec_literal(embed_word(c.word.lower())),  # 向量：進 DB 時算一次
        )
        for c in cards
    ]
    sql = """INSERT INTO voc_t (word, pronunciation, lang, mastery_level, definition, sentences, relations, embedding)
             VALUES (%s, %s, %s, %s, %s, %s, %s, %s::vector)
             ON CONFLICT (word, lang) DO NOTHING"""
    with conn.cursor() as cur:
        cur.executemany(sql, rows)
        inserted = cur.rowcount
    conn.commit()
    return inserted


def main():
    words = read_words()
    if not words:
        print(f"words.txt 是空的（{WORDS_FILE}）。丟幾個生字進去再跑。")
        return

    conn = review.get_conn()
    known = existing_words(conn, words)
    todo = [w for w in words if w.lower() not in known]
    if known:
        print(f"跳過 {len(known)} 個已在 voc_t 的字。")
    if not todo:
        print("沒有新字要處理。清空 words.txt。")
        open(WORDS_FILE, "w").close()
        conn.close()
        return

    print(f"用 {MODEL} 為 {len(todo)} 個新字產生卡片…")
    cards = generate(todo)
    if len(cards) != len(todo):
        print(
            f"⚠️ Claude 回了 {len(cards)} 張卡片，但輸入 {len(todo)} 個字，數量對不上。"
            f"沒有寫入，words.txt 保留原樣，請重跑。"
        )
        conn.close()
        return

    inserted = insert(conn, cards)
    conn.close()
    # ponytail: all-or-nothing — full batch succeeded, so the inbox is drained.
    open(WORDS_FILE, "w").close()
    print(
        f"✓ 寫入 voc_t {inserted} 筆（{len(cards) - inserted} 筆撞到既有字被 skip）。words.txt 已清空。"
    )


def _selfcheck():
    # read_words parsing (no API / DB needed)
    import tempfile

    p = tempfile.mktemp()
    with open(p, "w") as f:
        f.write("# a comment\n\ndisregard\n  overlook  \n\n# skip me\npivot\n")
    assert read_words(p) == ["disregard", "overlook", "pivot"], read_words(p)
    # schema round-trips
    b = Batch(
        cards=[
            Card(
                word="x",
                pronunciation="/x/",
                definition="d",
                daily_sentence="a",
                academic_sentence="b",
            )
        ]
    )
    assert b.cards[0].word == "x"
    os.remove(p)
    print("OK  add_words helpers (read_words + schema).")


if __name__ == "__main__":
    import sys

    if "--selfcheck" in sys.argv:
        _selfcheck()
    else:
        main()
