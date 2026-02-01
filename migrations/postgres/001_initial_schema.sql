-- Create developer table (VersionedModel) - Rococo format
CREATE TABLE IF NOT EXISTS developer (
    entity_id VARCHAR(32) PRIMARY KEY,
    version VARCHAR(32) NOT NULL,
    previous_version VARCHAR(32),
    active BOOLEAN DEFAULT TRUE,
    changed_by_id VARCHAR(32),
    changed_on TIMESTAMP,
    latest BOOLEAN DEFAULT TRUE,
    api_key_id VARCHAR(255) NOT NULL,
    name VARCHAR(100) NOT NULL,
    registered_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    extra JSONB
);

CREATE INDEX IF NOT EXISTS idx_developer_api_key_id ON developer(api_key_id);
CREATE INDEX IF NOT EXISTS idx_developer_active ON developer(active);

-- Audit table for developer (required by Rococo VersionedModel)
CREATE TABLE IF NOT EXISTS developer_audit (
    entity_id VARCHAR(32) NOT NULL,
    version VARCHAR(32) NOT NULL,
    previous_version VARCHAR(32),
    active BOOLEAN DEFAULT TRUE,
    changed_by_id VARCHAR(32),
    changed_on TIMESTAMP,
    latest BOOLEAN DEFAULT TRUE,
    api_key_id VARCHAR(255) NOT NULL,
    name VARCHAR(100) NOT NULL,
    registered_at TIMESTAMP NOT NULL,
    extra JSONB,
    PRIMARY KEY (entity_id, version)
);

CREATE INDEX IF NOT EXISTS idx_developer_audit_entity_id ON developer_audit(entity_id);

-- Create usage_snapshot table (BaseModel) - Rococo format
-- Note: BaseModel tables also need Big 6 columns for PostgreSQL adapter compatibility
CREATE TABLE IF NOT EXISTS usage_snapshot (
    entity_id VARCHAR(32) PRIMARY KEY,
    version VARCHAR(32),
    previous_version VARCHAR(32),
    active BOOLEAN DEFAULT TRUE,
    changed_by_id VARCHAR(32),
    changed_on TIMESTAMP,
    latest BOOLEAN DEFAULT TRUE,
    api_key_id VARCHAR(255) NOT NULL,
    snapshot_date DATE NOT NULL,
    model VARCHAR(100) NOT NULL DEFAULT 'unknown',
    uncached_input_tokens BIGINT NOT NULL DEFAULT 0,
    cache_read_input_tokens BIGINT NOT NULL DEFAULT 0,
    cache_creation_5m_tokens BIGINT NOT NULL DEFAULT 0,
    cache_creation_1h_tokens BIGINT NOT NULL DEFAULT 0,
    output_tokens BIGINT NOT NULL DEFAULT 0,
    web_search_requests INTEGER NOT NULL DEFAULT 0,
    fetched_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    extra JSONB
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_usage_snapshot_api_key_date_model
    ON usage_snapshot(api_key_id, snapshot_date, model);

CREATE INDEX IF NOT EXISTS idx_usage_snapshot_snapshot_date
    ON usage_snapshot(snapshot_date);

CREATE INDEX IF NOT EXISTS idx_usage_snapshot_model
    ON usage_snapshot(model);
