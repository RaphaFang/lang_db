CREATE TABLE learning_t (
    -- 1
    word_id UUID PRIMARY KEY REFERENCES voc_t(id) ON DELETE CASCADE,

    -- 2
    difficulty REAL NOT NULL DEFAULT 0,
    stability REAL NOT NULL DEFAULT 0,
    state INT NOT NULL DEFAULT 0,
    
    -- 3.
    next_review_date DATE NOT NULL DEFAULT CURRENT_DATE,

    -- 4
    listening_count INT DEFAULT 0,
    speaking_count  INT DEFAULT 0,
    reading_count   INT DEFAULT 0,
    writing_count   INT DEFAULT 0,

    -- 5.
    last_review_at TIMESTAMPTZ,
    failure_count INT DEFAULT 0,
    
    updated_time TIMESTAMPTZ DEFAULT NOW() 
);
CREATE INDEX idx_learning_next_review ON learning_t (next_review_date);