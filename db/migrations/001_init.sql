-- Database initialization script
-- Runs automatically when PostgreSQL container starts for the first time

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS posts (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    content TEXT,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_posts_user ON posts(user_id);
CREATE INDEX IF NOT EXISTS idx_posts_created ON posts(created_at);

-- Insert sample data
INSERT INTO users (email, name) VALUES 
    ('john@example.com', 'John Doe'),
    ('jane@example.com', 'Jane Smith'),
    ('marinus.opperman@gmail.com','Marinus Opperman')
ON CONFLICT (email) DO NOTHING;

INSERT INTO posts (title, content, user_id) VALUES 
    ('First Post', 'This is my first post!', 1),
    ('Second Post', 'Another interesting post.', 2)
ON CONFLICT DO NOTHING;
