"""Today's review session. Run:  python3 -m widget_srs.run_review [lang] [limit]

Shows each due word, you rate 1-4, FSRS schedules the next date and logs it.
  1=Again(forgot)  2=Hard  3=Good  4=Easy   (q=quit, Enter=skip)
"""

import sys
from . import review, embed

RATINGS = {"1", "2", "3", "4"}


def main(lang=None, limit=50):
    conn = review.get_conn()
    cards = review.due_cards(conn, lang=lang, limit=limit)
    if not cards:
        print("今天沒有要複習的 🎉")
        return

    print(f"今天要複習 {len(cards)} 個字。 1=Again 2=Hard 3=Good 4=Easy, q=結束\n")
    done = 0
    for word_id, word, wlang, *_ in cards:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT definition, sentences, relations FROM voc_t WHERE id=%s",
                (word_id,),
            )
            definition, sentences, relations = cur.fetchone()

        print(f"\n─── {word}  [{wlang}] ───")
        ans = input("  先回想，按 Enter 看解釋… ")
        if ans.strip().lower() == "q":
            break
        print(f"  {definition}")
        for s in sentences or []:
            print(f"    · {s}")
        syn = (relations or {}).get("synonyms") or []
        ant = (relations or {}).get("antonyms") or []
        if syn:
            print("  近義: " + ", ".join(syn))  # LLM 標註
        if ant:
            print("  反義: " + ", ".join(ant))  # LLM 標註（embedding 給不出）
        sims = embed.similar(conn, word_id)  # embedding 現查，跨語言、無標籤
        if sims:
            print("  語意相近: " + ", ".join(w for w, _ in sims))

        rating = input("  你的評分 (1-4, q=結束, Enter=跳過): ").strip().lower()
        if rating == "q":
            break
        if rating not in RATINGS:
            print("  跳過。")
            continue

        out = review.apply_review(conn, word_id, int(rating))
        done += 1
        print(
            f"  ✓ 下次複習：+{out['interval']} 天  (stability={out['stability']:.1f})"
        )

    print(f"\n本次複習了 {done} 個字。收工。")
    conn.close()


if __name__ == "__main__":
    lang = sys.argv[1] if len(sys.argv) > 1 else None
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 50
    main(lang, limit)
