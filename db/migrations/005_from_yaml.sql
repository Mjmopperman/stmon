-- Auto-generated database migration from schema/database.yaml
-- Tables: chess_moves

-- Table to store chess moves
CREATE TABLE IF NOT EXISTS chess_moves (
    id UUID NOT NULL PRIMARY KEY DEFAULT gen_random_uuid(),
    move_notation TEXT NOT NULL UNIQUE,
    score DECIMAL NOT NULL
);
