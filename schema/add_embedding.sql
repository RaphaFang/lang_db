-- 為 voc_t 加語意向量欄位（multilingual-e5-small = 384 維）。
-- 前置：Postgres 要先裝好 pgvector（macOS: `brew install pgvector`，或你的 PG 發行版對應套件）。
-- 執行身分：CREATE EXTENSION 需 superuser；ALTER TABLE 需 table owner (fangsiyu)。
-- 新欄位自動沿用 voc_t 現有的 grant，app 角色 (rapha) 不用另外授權。

CREATE EXTENSION IF NOT EXISTS vector;

ALTER TABLE voc_t ADD COLUMN IF NOT EXISTS embedding vector(384);

-- ponytail: 個人字庫幾千筆，seq scan 比較距離就是 sub-ms，先不建 index。
--           破萬筆再加： CREATE INDEX ON voc_t USING hnsw (embedding vector_cosine_ops);
