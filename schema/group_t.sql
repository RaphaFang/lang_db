CREATE TABLE group_t (
    -- 1.
    id SERIAL PRIMARY KEY,

    -- 2.
    group_name VARCHAR(100), 
    
    -- 3.
    word_ids UUID[],

    algo_version VARCHAR(50) NOT NULL,

    -- 4.
    low5  UUID[],
    high5 UUID[],

    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_group_t_algo ON group_t(algo_version);