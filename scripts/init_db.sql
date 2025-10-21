-- ============================================
-- REPORT GENERATION DATABASE SCHEMA v1.0.0
-- PostgreSQL 14+
-- ============================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm"; -- For fuzzy search

-- ============================================
-- DOMAIN TYPES
-- ============================================

CREATE TYPE report_type AS ENUM (
    'comprehensive',
    'executive',
    'targeted',
    'comparative'
);

CREATE TYPE report_status AS ENUM (
    'created',
    'analyzing',
    'researching',
    'generating',
    'quality_check',
    'needs_improvement',
    'completed',
    'failed',
    'cancelled'
);

CREATE TYPE content_type AS ENUM (
    'narrative',
    'tabular',
    'visual',
    'statistical',
    'code'
);

CREATE TYPE source_type AS ENUM (
    'web',
    'academic',
    'wikidata',
    'ontology_annotation'
);

CREATE TYPE feedback_status AS ENUM (
    'submitted',
    'processing',
    'processed',
    'failed'
);

CREATE TYPE export_format AS ENUM (
    'html',
    'pdf',
    'markdown',
    'json'
);

-- ============================================
-- USERS & AUTHENTICATION
-- ============================================

CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    organization VARCHAR(255),
    role VARCHAR(50) DEFAULT 'user',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE,
    preferences JSONB DEFAULT '{}',

    CONSTRAINT valid_email CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);

-- ============================================
-- REPORTS
-- ============================================

CREATE TABLE reports (
    report_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    report_type report_type NOT NULL,
    status report_status DEFAULT 'created',

    -- Ontology reference
    ontology_uri TEXT NOT NULL,
    ontology_format VARCHAR(10),
    ontology_file_path TEXT,

    -- Generation configuration
    config JSONB DEFAULT '{}',

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,

    -- Metrics
    quality_score DECIMAL(5,2),
    completeness_score DECIMAL(5,2),
    section_count INTEGER DEFAULT 0,
    total_word_count INTEGER DEFAULT 0,
    generation_time_seconds INTEGER,

    -- Version
    version VARCHAR(20) DEFAULT '1.0.0',
    parent_report_id UUID REFERENCES reports(report_id),

    -- Metadata
    metadata JSONB DEFAULT '{}',

    CONSTRAINT valid_quality_score CHECK (quality_score >= 0 AND quality_score <= 100),
    CONSTRAINT valid_completeness_score CHECK (completeness_score >= 0 AND completeness_score <= 100)
);

CREATE INDEX idx_reports_user_id ON reports(user_id);
CREATE INDEX idx_reports_status ON reports(status);
CREATE INDEX idx_reports_created_at ON reports(created_at DESC);
CREATE INDEX idx_reports_type ON reports(report_type);
CREATE INDEX idx_reports_quality ON reports(quality_score DESC);

-- Trigger to update modified_at
CREATE OR REPLACE FUNCTION update_modified_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.modified_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_reports_modified
BEFORE UPDATE ON reports
FOR EACH ROW
EXECUTE FUNCTION update_modified_timestamp();

-- ============================================
-- REPORT SECTIONS
-- ============================================

CREATE TABLE report_sections (
    section_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id UUID NOT NULL REFERENCES reports(report_id) ON DELETE CASCADE,
    parent_section_id UUID REFERENCES report_sections(section_id) ON DELETE CASCADE,

    section_number VARCHAR(50) NOT NULL,
    section_title VARCHAR(500) NOT NULL,
    section_description TEXT,

    hierarchy_level INTEGER NOT NULL,
    order_index INTEGER NOT NULL,

    -- Ontology mapping
    mapped_class_uri TEXT NOT NULL,
    mapped_class_label VARCHAR(255),

    -- Status
    status VARCHAR(50) DEFAULT 'pending',

    -- Metrics
    word_count INTEGER DEFAULT 0,
    content_count INTEGER DEFAULT 0,
    completeness_score DECIMAL(5,2),

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    metadata JSONB DEFAULT '{}',

    CONSTRAINT valid_hierarchy_level CHECK (hierarchy_level >= 1 AND hierarchy_level <= 10),
    CONSTRAINT unique_section_order UNIQUE (report_id, parent_section_id, order_index)
);

CREATE INDEX idx_sections_report_id ON report_sections(report_id);
CREATE INDEX idx_sections_parent_id ON report_sections(parent_section_id);
CREATE INDEX idx_sections_order ON report_sections(report_id, order_index);
CREATE INDEX idx_sections_mapped_class ON report_sections(mapped_class_uri);

-- ============================================
-- REPORT CONTENT
-- ============================================

CREATE TABLE report_content (
    content_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    section_id UUID NOT NULL REFERENCES report_sections(section_id) ON DELETE CASCADE,

    content_type content_type NOT NULL,
    order_index INTEGER NOT NULL,

    -- Content data (type-specific)
    content_data JSONB NOT NULL,

    -- Generation metadata
    generated_by VARCHAR(100),
    generation_config JSONB,

    -- Quality
    quality_score DECIMAL(5,2),

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Research reference
    research_result_id UUID,

    metadata JSONB DEFAULT '{}',

    CONSTRAINT unique_content_order UNIQUE (section_id, order_index)
);

CREATE INDEX idx_content_section_id ON report_content(section_id);
CREATE INDEX idx_content_type ON report_content(content_type);
CREATE INDEX idx_content_order ON report_content(section_id, order_index);
CREATE INDEX idx_content_research ON report_content(research_result_id);

-- ============================================
-- RESEARCH DATA
-- ============================================

CREATE TABLE research_results (
    research_result_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- What was researched
    concept_uri TEXT NOT NULL,
    concept_label VARCHAR(255) NOT NULL,

    -- Aggregated results
    aggregated_data JSONB NOT NULL,

    -- Metrics
    source_count INTEGER DEFAULT 0,
    fact_count INTEGER DEFAULT 0,
    confidence_score DECIMAL(5,2),

    -- Timestamps
    researched_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE,

    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_research_concept ON research_results(concept_uri);
CREATE INDEX idx_research_label ON research_results USING gin(concept_label gin_trgm_ops);
CREATE INDEX idx_research_expires ON research_results(expires_at);

-- ============================================
-- KNOWLEDGE SOURCES
-- ============================================

CREATE TABLE knowledge_sources (
    source_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_name VARCHAR(255) NOT NULL,
    source_type source_type NOT NULL,
    source_url TEXT,

    -- Quality metrics
    reliability_score DECIMAL(5,2),
    domain_authority DECIMAL(5,2),

    -- Access metadata
    last_accessed TIMESTAMP WITH TIME ZONE,
    access_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,

    is_active BOOLEAN DEFAULT TRUE,

    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_sources_type ON knowledge_sources(source_type);
CREATE INDEX idx_sources_reliability ON knowledge_sources(reliability_score DESC);
CREATE INDEX idx_sources_active ON knowledge_sources(is_active) WHERE is_active = TRUE;

-- ============================================
-- RESEARCH-SOURCE JUNCTION
-- ============================================

CREATE TABLE research_sources (
    research_result_id UUID NOT NULL REFERENCES research_results(research_result_id) ON DELETE CASCADE,
    source_id UUID NOT NULL REFERENCES knowledge_sources(source_id) ON DELETE CASCADE,

    -- Source-specific data
    extracted_facts JSONB,
    relevance_score DECIMAL(5,2),

    PRIMARY KEY (research_result_id, source_id)
);

CREATE INDEX idx_research_sources_research ON research_sources(research_result_id);
CREATE INDEX idx_research_sources_source ON research_sources(source_id);

-- ============================================
-- CITATIONS
-- ============================================

CREATE TABLE citations (
    citation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content_id UUID NOT NULL REFERENCES report_content(content_id) ON DELETE CASCADE,
    source_id UUID NOT NULL REFERENCES knowledge_sources(source_id),

    citation_number INTEGER NOT NULL,
    citation_text TEXT,

    -- Position in content
    start_position INTEGER,
    end_position INTEGER,

    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_citations_content ON citations(content_id);
CREATE INDEX idx_citations_source ON citations(source_id);

-- ============================================
-- FEEDBACK
-- ============================================

CREATE TABLE feedback (
    feedback_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id UUID NOT NULL REFERENCES reports(report_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(user_id),
    section_id UUID REFERENCES report_sections(section_id),

    feedback_text TEXT NOT NULL,
    feedback_status feedback_status DEFAULT 'submitted',

    -- Intent classification
    classified_intents JSONB,

    submitted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP WITH TIME ZONE,

    -- Processing result
    actions_taken JSONB,

    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_feedback_report ON feedback(report_id);
CREATE INDEX idx_feedback_user ON feedback(user_id);
CREATE INDEX idx_feedback_status ON feedback(feedback_status);
CREATE INDEX idx_feedback_submitted ON feedback(submitted_at DESC);

-- ============================================
-- EXPORTS
-- ============================================

CREATE TABLE exports (
    export_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id UUID NOT NULL REFERENCES reports(report_id) ON DELETE CASCADE,

    export_format export_format NOT NULL,
    file_path TEXT NOT NULL,
    file_size_bytes BIGINT,

    -- Export configuration
    export_config JSONB,

    -- Status
    status VARCHAR(50) DEFAULT 'pending',

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE,

    download_count INTEGER DEFAULT 0,
    last_downloaded TIMESTAMP WITH TIME ZONE,

    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_exports_report ON exports(report_id);
CREATE INDEX idx_exports_format ON exports(export_format);
CREATE INDEX idx_exports_expires ON exports(expires_at);

-- ============================================
-- QUALITY METRICS
-- ============================================

CREATE TABLE quality_assessments (
    assessment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id UUID NOT NULL REFERENCES reports(report_id) ON DELETE CASCADE,

    -- Overall scores
    overall_score DECIMAL(5,2) NOT NULL,
    completeness_score DECIMAL(5,2) NOT NULL,
    citation_coverage DECIMAL(5,2) NOT NULL,
    accessibility_score DECIMAL(5,2),
    performance_score DECIMAL(5,2),
    readability_score DECIMAL(5,2),

    -- Issues found
    issues JSONB DEFAULT '[]',

    -- Metadata
    assessed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    assessor_version VARCHAR(50),

    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_quality_report ON quality_assessments(report_id);
CREATE INDEX idx_quality_overall ON quality_assessments(overall_score DESC);
CREATE INDEX idx_quality_assessed ON quality_assessments(assessed_at DESC);

-- ============================================
-- LLM USAGE TRACKING
-- ============================================

CREATE TABLE llm_generations (
    generation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content_id UUID REFERENCES report_content(content_id),
    provider VARCHAR(50) NOT NULL,
    model VARCHAR(100) NOT NULL,
    prompt_hash VARCHAR(64),
    tokens_used INTEGER NOT NULL,
    cost DECIMAL(10,4) NOT NULL,
    latency_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_generations_provider ON llm_generations(provider);
CREATE INDEX idx_generations_cost ON llm_generations(cost DESC);
CREATE INDEX idx_generations_created ON llm_generations(created_at DESC);

-- ============================================
-- AUDIT LOG
-- ============================================

CREATE TABLE audit_log (
    log_id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(user_id),
    report_id UUID REFERENCES reports(report_id),

    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID,

    old_values JSONB,
    new_values JSONB,

    ip_address INET,
    user_agent TEXT,

    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_audit_user ON audit_log(user_id);
CREATE INDEX idx_audit_report ON audit_log(report_id);
CREATE INDEX idx_audit_action ON audit_log(action);
CREATE INDEX idx_audit_timestamp ON audit_log(timestamp DESC);
CREATE INDEX idx_audit_entity ON audit_log(entity_type, entity_id);

-- ============================================
-- INITIAL DATA
-- ============================================

-- Insert default knowledge sources
INSERT INTO knowledge_sources (source_name, source_type, source_url, reliability_score) VALUES
('Wikipedia', 'web', 'https://wikipedia.org', 85.0),
('Wikidata', 'wikidata', 'https://wikidata.org', 90.0),
('Semantic Scholar', 'academic', 'https://www.semanticscholar.org', 95.0),
('PubMed', 'academic', 'https://pubmed.ncbi.nlm.nih.gov', 95.0);

-- ============================================
-- FUNCTIONS
-- ============================================

-- Function to calculate report completeness
CREATE OR REPLACE FUNCTION calculate_report_completeness(p_report_id UUID)
RETURNS DECIMAL AS $$
DECLARE
    v_total_sections INTEGER;
    v_complete_sections INTEGER;
    v_completeness DECIMAL;
BEGIN
    SELECT COUNT(*) INTO v_total_sections
    FROM report_sections
    WHERE report_id = p_report_id;

    SELECT COUNT(*) INTO v_complete_sections
    FROM report_sections
    WHERE report_id = p_report_id
    AND content_count > 0;

    IF v_total_sections = 0 THEN
        RETURN 0;
    END IF;

    v_completeness := (v_complete_sections::DECIMAL / v_total_sections::DECIMAL) * 100;

    RETURN ROUND(v_completeness, 2);
END;
$$ LANGUAGE plpgsql;
