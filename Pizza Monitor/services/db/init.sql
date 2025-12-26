-- services/db/init.sql
CREATE TABLE IF NOT EXISTS violations (
    id SERIAL PRIMARY KEY,
    video_name VARCHAR(255) NOT NULL,
    frame_id INTEGER NOT NULL,
    timestamp BIGINT NOT NULL,
    violation_type VARCHAR(50) NOT NULL,
    bounding_boxes JSONB,
    detected_objects JSONB,
    confidence JSONB, 
    frame_path VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_violations_video_name ON violations(video_name);
CREATE INDEX IF NOT EXISTS idx_violations_timestamp ON violations(timestamp);