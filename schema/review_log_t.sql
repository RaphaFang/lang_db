-- One row per review. This is both the audit trail and the TRAINING DATA
-- that widget_srs/fsrs.optimize() fits the weights on.
CREATE TABLE review_log_t (
    id BIGSERIAL PRIMARY KEY,
    word_id UUID NOT NULL REFERENCES voc_t(id) ON DELETE CASCADE,
    rating SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 4),  -- 1=Again 2=Hard 3=Good 4=Easy
    elapsed_days INT NOT NULL DEFAULT 0,                      -- days since previous review
    stability_before REAL,                                   -- state at review time (for debugging)
    reviewed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_review_log_word ON review_log_t (word_id, reviewed_at);
