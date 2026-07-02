"""multilingual-e5-small 向量：voc_t 的字轉語意向量 + 相似詞現查。
pip install sentence-transformers

核心觀念：一個字的向量只取決於「字本身 + 模型」，跟表裡有沒有別的字無關。
所以向量進 DB 時算一次就固定，永遠不用因為新增別的字而重算。
唯一要重跑 backfill() 的情況：換掉 MODEL（等於換座標系）。
相似詞不預存，用 similar() 對當下整張表現查，永遠最新。
"""

import functools

MODEL = "intfloat/multilingual-e5-small"  # 384 維、多語言，跨語言相似詞免費附送
DIM = 384


@functools.lru_cache(maxsize=1)
def _model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(MODEL)


def embed_word(word: str) -> list[float]:
    """一個字 -> 384 個 float。e5 要求 'query:' 前綴。"""
    v = _model().encode(f"query: {word}", normalize_embeddings=True)
    return v.tolist()


def _vec_literal(vec) -> str:
    """轉成 pgvector 文字字面值 '[a,b,c]'，配 %s::vector 使用（免裝 pgvector-python）。"""
    return "[" + ",".join(map(str, vec)) + "]"


def similar(conn, word_id, k=5):
    """跟 word_id 最近的 k 個字，餘弦距離，對當下整張表現查。回傳 [(word, lang), ...]。"""
    with conn.cursor() as cur:
        cur.execute(
            """SELECT word, lang FROM voc_t
               WHERE id != %s AND embedding IS NOT NULL
               ORDER BY embedding <=> (SELECT embedding FROM voc_t WHERE id = %s)
               LIMIT %s""",
            (word_id, word_id, k),
        )
        return cur.fetchall()


def backfill(conn):
    """把還沒有向量的 row 補算。加完欄位後跑一次；或換 MODEL 後（先清空 embedding 再跑）。"""
    with conn.cursor() as cur:
        cur.execute("SELECT id, word FROM voc_t WHERE embedding IS NULL")
        rows = cur.fetchall()
        for wid, word in rows:
            cur.execute(
                "UPDATE voc_t SET embedding = %s::vector WHERE id = %s",
                (_vec_literal(embed_word(word)), wid),
            )
    conn.commit()
    return len(rows)


def _selfcheck():
    # 純函式：pgvector 字面值格式正確（不需模型/DB）
    assert _vec_literal([0.5, -1.0, 2.0]) == "[0.5,-1.0,2.0]"
    assert _vec_literal([1, 2, 3]) == "[1,2,3]"
    print("OK  embed._vec_literal")
    # 模型測試很重（會下載 ~470MB），要驗跨語言就手動跑下面：
    # v_cat, v_gato = embed_word("cat"), embed_word("gato")
    # import numpy as np; assert np.dot(v_cat, v_gato) > 0.8  # 跨語言應該很近


if __name__ == "__main__":
    _selfcheck()
