"""Paste-mode import: $0 API, uses your web subscription.

Workflow:
  1. jot new words in words.txt (one per line)
  2. build the prompt:   python3 -m widget_srs.paste_import --prompt
     -> copy the printed prompt into Claude.ai / ChatGPT (web, your subscription)
  3. copy the model's JSON reply into  paste.json
  4. import it:          python3 -m widget_srs.paste_import
     -> validates, dedups against voc_t, inserts, clears words.txt

Reuses the schema, DB insert, and dedup from add_words — only the "where the
cards come from" differs (pasted file vs API call).
"""

import os
import re
import json

from pydantic import ValidationError
from . import add_words, review

PASTE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "paste.json")

JSON_SPEC = """

輸出格式（很重要）：只輸出一個 JSON 陣列，不要任何解釋文字、不要 markdown。
每個元素的 key 必須完全是：word, pronunciation, definition, daily_sentence, academic_sentence。
範例：
[
  {"word": "disregard", "pronunciation": "/ˌdɪsrɪˈɡɑːd/", "definition": "…繁體中文解釋…",
   "daily_sentence": "…", "academic_sentence": "…"}
]

單字清單："""


def build_prompt():
    words = add_words.read_words()
    if not words:
        return None
    listing = "\n".join(f"{i + 1}. {w}" for i, w in enumerate(words))
    return add_words.SYSTEM + JSON_SPEC + "\n" + listing


def parse(text):
    """Lenient: tolerate markdown fences / surrounding prose. Returns (cards, errors)."""
    t = text.strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", t, re.S)
    if m:
        t = m.group(1).strip()
    i, j = t.find("["), t.rfind("]")
    if i == -1 or j == -1:
        raise ValueError("在貼上的內容裡找不到 JSON 陣列（[ ... ]）。")
    data = json.loads(t[i : j + 1])

    cards, errors = [], []
    for n, obj in enumerate(data, 1):
        try:
            cards.append(add_words.Card(**obj))
        except (ValidationError, TypeError) as e:
            errors.append(f"第 {n} 筆: {str(e).splitlines()[0]}")
    return cards, errors


def main():
    if not os.path.isfile(PASTE_FILE):
        print(f"找不到 {PASTE_FILE} 。把網頁模型回覆的 JSON 存進這個檔案再跑。")
        return
    with open(PASTE_FILE, encoding="utf-8") as f:
        text = f.read()
    if not text.strip():
        print(f"{PASTE_FILE} 是空的。先把 JSON 貼進去。")
        return

    cards, errors = parse(text)
    for e in errors:
        print(f"⚠️ 略過 {e}")
    if not cards:
        print("沒有可用的卡片。paste.json 與 words.txt 保留原樣。")
        return

    conn = review.get_conn()
    known = add_words.existing_words(conn, [c.word for c in cards])
    new = [c for c in cards if c.word.lower() not in known]
    if known:
        print(f"跳過 {len(known)} 個已在 voc_t 的字。")
    if not new:
        print("沒有新字要寫入。")
        conn.close()
        return

    inserted = add_words.insert(conn, new)
    conn.close()
    print(f"✓ 寫入 voc_t {inserted} 筆。")
    if not errors:  # ponytail: only drain both inboxes on a fully clean paste
        open(add_words.WORDS_FILE, "w").close()
        open(PASTE_FILE, "w").close()
        print("words.txt 與 paste.json 已清空。")
    else:
        print("有略過的筆數，words.txt / paste.json 都保留，修好後可重跑。")


def _selfcheck():
    text = """好的，這是你的 JSON：
```json
[
  {"word": "disregard", "pronunciation": "/x/", "definition": "d", "daily_sentence": "a", "academic_sentence": "b"},
  {"word": "overlook", "definition": "d2", "daily_sentence": "a2", "academic_sentence": "b2"},
  {"word": "bad", "definition": "missing sentences"}
]
```
希望有幫助！"""
    cards, errors = parse(text)
    assert len(cards) == 2, cards  # 3rd is missing sentences -> skipped
    assert len(errors) == 1, errors
    assert cards[0].word == "disregard"
    assert cards[1].pronunciation == ""  # default when web output omits IPA
    print("OK  paste_import.parse (fences + prose + bad-item skip).")


if __name__ == "__main__":
    import sys

    if "--selfcheck" in sys.argv:
        _selfcheck()
    elif "--prompt" in sys.argv:
        p = build_prompt()
        print(p if p else "words.txt 是空的，先丟幾個生字進去。")
    else:
        main()
