CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE voc_t (
    -- col 0
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- col 1
    word TEXT NOT NULL,
    
    -- col 2
    pronunciation TEXT, 
    
    -- col 3
    lang VARCHAR(5) NOT NULL,

    -- col 4
    mastery_level SMALLINT DEFAULT 1,
    
    -- col 5
    definition TEXT,
    
    -- col 6
    sentences JSONB DEFAULT '[]'::jsonb,

    -- col 7
    last_reviewed TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    -- col 8
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_word_lang UNIQUE (word, lang),  -- this automatically make an index on both col

    CONSTRAINT chk_mastery_range CHECK (mastery_level >= 1 AND mastery_level <= 10)
);

CREATE INDEX idx_lang ON voc_t(lang);