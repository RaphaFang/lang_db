-- LLM 標註的近義/反義詞（跟 embedding 現查互補：embedding 分不出同義 vs 反義，這欄補上標籤）。
-- 執行身分：table owner (fangsiyu)。新欄位自動沿用 voc_t 現有 grant。
-- 格式： {"synonyms": ["..."], "antonyms": ["..."]}

ALTER TABLE voc_t ADD COLUMN IF NOT EXISTS relations JSONB DEFAULT '{}'::jsonb;
