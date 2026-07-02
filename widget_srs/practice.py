"""主動產出練習：一次給 10 個「語意相近」的字，你造句或寫成一段，$0 批改。

跟 run_review 的被動回想互補 —— 這裡是自己寫。用法：

  python3 -m widget_srs.practice [lang]
    1. 抓一個語意群集（種子字 + embedding 最近的 9 個）—— 相近才寫得成通順段落
    2. 秀出 10 個字 + 解釋
    3. 你選模式：s=每字造一句 / p=全部寫成一段
    4. 你把寫作打進去（空一行結束）
    5. 印出一段批改 prompt -> 貼到 Claude.ai / ChatGPT（網頁訂閱，$0）讀回饋

選字復用 embed 的 <=> 相似度；連線復用 review.get_conn。不寫 DB。
"""

import sys

from . import review

SYSTEM_GRADE = """你是英文寫作老師，學生正在練習指定的一批英文單字。針對學生的寫作：
1. 逐字檢查每個「目標單字」是否用對（語意、搭配、詞性）；用錯就指出並改正。
2. 修文法與不自然處，給出更道地的英文版本。
3. 沒用到的目標單字要點名。
4. 給整體分數（1-10）與一句總評。
用繁體中文講解，改寫與例句用英文。"""

MODES = {
    "s": "每個目標單字各造一句獨立的句子",
    "p": "把所有目標單字組合成一小段連貫的英文短文，每個字都要用到",
}


def pick_cluster(conn, n=10, lang=None):
    """種子字（優先今天要複習的，否則隨機）+ embedding 最近的 n-1 個。
    回傳 [(id, word, definition), ...]，種子在第一個。"""
    due = review.due_cards(conn, lang=lang, limit=1)
    if due:
        seed_id = due[0][0]
    else:
        with conn.cursor() as cur:
            q = "SELECT id FROM voc_t WHERE embedding IS NOT NULL"
            q += " AND lang=%s" if lang else ""
            q += " ORDER BY random() LIMIT 1"
            cur.execute(q, (lang,) if lang else ())
            r = cur.fetchone()
        if not r:
            return []
        seed_id = r[0]

    # 同 embed.similar 的 <=> 查法，但這裡要 id（好抓解釋）且要含種子本身
    with conn.cursor() as cur:
        cur.execute(
            """SELECT id FROM voc_t
               WHERE id != %s AND embedding IS NOT NULL
               ORDER BY embedding <=> (SELECT embedding FROM voc_t WHERE id = %s)
               LIMIT %s""",
            (seed_id, seed_id, n - 1),
        )
        ids = [seed_id] + [r[0] for r in cur.fetchall()]
        cur.execute("SELECT id, word, definition FROM voc_t WHERE id = ANY(%s)", (ids,))
        by_id = {r[0]: (r[1], r[2]) for r in cur.fetchall()}
    return [(i, *by_id[i]) for i in ids if i in by_id]


def build_grade_prompt(cluster, mode, answer):
    listing = "\n".join(f"{i + 1}. {w} — {d}" for i, (_, w, d) in enumerate(cluster))
    return (
        SYSTEM_GRADE
        + f"\n\n目標單字（{len(cluster)} 個，語意相近）：\n{listing}"
        + f"\n\n練習模式：{MODES[mode]}"
        + f"\n\n學生的寫作：\n{answer}"
    )


def read_answer():
    print("\n開始寫（空一行結束輸入）：")
    lines = []
    while True:
        try:
            ln = input()
        except EOFError:
            break
        if ln == "":
            break
        lines.append(ln)
    return "\n".join(lines).strip()


def main(lang=None):
    conn = review.get_conn()
    cluster = pick_cluster(conn, lang=lang)
    conn.close()
    if not cluster:
        print("voc_t 裡沒有帶 embedding 的字，先跑 add_words / embed.backfill。")
        return

    print(f"\n=== 今天練這 {len(cluster)} 個語意相近的字 ===")
    for i, (_, w, d) in enumerate(cluster, 1):
        print(f"{i}. {w} — {d}")

    mode = ""
    while mode not in MODES:
        mode = input("\n模式 s=每字造一句 / p=組合成一段 (q=結束): ").strip().lower()
        if mode == "q":
            return

    answer = read_answer()
    if not answer:
        print("沒寫東西，這次不批改。")
        return

    print("\n" + "=" * 60)
    print("把下面整段複製到 Claude.ai / ChatGPT（網頁訂閱）讀批改：")
    print("=" * 60 + "\n")
    print(build_grade_prompt(cluster, mode, answer))


def _selfcheck():
    cluster = [
        (1, "disregard", "忽視"),
        (2, "overlook", "略過"),
        (3, "dismiss", "駁回"),
    ]
    p = build_grade_prompt(cluster, "p", "I disregard the rules.")
    assert "disregard" in p and "overlook" in p and "dismiss" in p
    assert MODES["p"] in p  # 模式說明有帶進去
    assert "I disregard the rules." in p  # 學生答案有帶進去
    assert build_grade_prompt(cluster, "s", "x").count(" — ") == 3  # 逐字列出
    print("OK  practice.build_grade_prompt")


if __name__ == "__main__":
    if "--selfcheck" in sys.argv:
        _selfcheck()
    else:
        main(sys.argv[1] if len(sys.argv) > 1 else None)
