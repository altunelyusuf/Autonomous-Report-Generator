# Autonomous Report Generator

**Version:** 1.0.0
**Status:** In Development
**Architecture:** Ontology-Driven Report Generation with LLM Integration

## Overview

The Autonomous Report Generator is a comprehensive system for generating high-quality, research-backed reports from OWL/RDF ontologies. The system uses semantic web technologies to analyze ontologies, conduct automated research, and generate professional documentation using Large Language Models (LLMs).

### Key Features

- **Ontology Processing**: Parse and analyze OWL, RDF, Turtle, and N3 ontologies
- **Automated Research**: Multi-source knowledge gathering (Web, Academic APIs, Wikidata)
- **LLM-Powered Generation**: Generate narrative content using OpenAI, Anthropic, or local models
- **Multiple Export Formats**: HTML, PDF, Markdown, and JSON
- **Quality Validation**: Automated quality assessment and citation verification
- **RESTful API**: Complete FastAPI-based REST API
- **Web Interface**: React-based user interface

## Architecture

The system follows a layered architecture with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                     Presentation Layer                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Web UI     │  │  REST API    │  │  CLI Tool    │      │
│  │  (React)     │  │  (FastAPI)   │  │  (Click)     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                         │
│       Report Generation Orchestrator                         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                      Domain Layer                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Ontology    │  │   Research   │  │   Content    │      │
│  │  Analyzer    │  │  Orchestrator│  │  Generator   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   Infrastructure Layer                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Ontology    │  │  Web Scraper │  │  LLM Service │      │
│  │  Parser      │  │  Service     │  │  Gateway     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

## Project Structure

```
Autonomous-Report-Generator/
├── src/
│   ├── api/                    # FastAPI REST API
│   │   ├── routes/            # API route handlers
│   │   └── models/            # Pydantic request/response models
│   ├── domain/                # Core business logic
│   │   ├── ontology/          # Ontology processing (Sprint 1) ✅
│   │   │   ├── parsers/       # RDFLib, OWLReady2 parsers
│   │   │   ├── extractors/    # Metadata, Class extractors
│   │   │   ├── builders/      # Hierarchy builder
│   │   │   ├── analyzer.py    # Main ontology analyzer facade
│   │   │   └── models.py      # Domain models
│   │   ├── research/          # Research orchestration
│   │   ├── generation/        # Content generation
│   │   └── refinement/        # Feedback processing
│   ├── infrastructure/        # External integrations
│   │   ├── cache/            # Redis caching
│   │   ├── database/         # PostgreSQL models
│   │   ├── llm/              # LLM provider integrations
│   │   └── external_services/ # Web search, academic APIs
│   ├── config/               # Configuration management ✅
│   └── utils/                # Shared utilities
├── tests/
│   ├── unit/                 # Unit tests
│   ├── integration/          # Integration tests
│   └── fixtures/             # Test fixtures (sample ontologies)
├── docs/                     # Documentation
├── scripts/                  # Utility scripts
│   └── init_db.sql          # Database initialization ✅
├── migrations/               # Database migrations (Alembic)
├── requirements.txt          # Python dependencies ✅
├── pyproject.toml           # Project configuration ✅
├── .env.example             # Environment configuration template ✅
└── README.md                # This file
```

## Installation

### Prerequisites

- Python 3.10 or higher
- PostgreSQL 14+
- Redis 5+
- Node.js 18+ (for Web UI)

### Backend Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/altunelyusuf/Autonomous-Report-Generator.git
   cd Autonomous-Report-Generator
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   # Or using Poetry
   poetry install
   ```

4. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Initialize database:**
   ```bash
   # Create PostgreSQL database
   createdb reportgen

   # Run initialization script
   psql -d reportgen -f scripts/init_db.sql

   # Run migrations
   alembic upgrade head
   ```

6. **Start Redis:**
   ```bash
   redis-server
   ```

### Configuration

Edit `.env` file with your settings:

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/reportgen

# Redis
REDIS_URL=redis://localhost:6379/0

# LLM API Keys
OPENAI_API_KEY=sk-your-key-here
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Research APIs
WEB_SEARCH_API_KEY=your-search-api-key
ACADEMIC_API_KEY=your-academic-api-key
```

## Usage

### Python API

```python
from pathlib import Path
from src.domain.ontology.analyzer import OntologyAnalyzer

# Initialize analyzer
analyzer = OntologyAnalyzer()

# Analyze ontology
ontology_file = Path("examples/wine.owl")
structure = analyzer.analyze_ontology(ontology_file)

# Access results
print(f"Title: {structure.metadata.title}")
print(f"Classes: {structure.statistics.class_count}")
print(f"Max Hierarchy Depth: {structure.hierarchy.max_depth}")

# Access class hierarchy
for root_class in structure.hierarchy.roots:
    print(f"Root Class: {root_class.label}")
    for child in root_class.children:
        print(f"  - {child.label}")
```

## Sprint Implementation Status

Following Agile SCRUM methodology with 12 sprints:

### ✅ Sprint 1: Ontology Parsing Foundation (COMPLETED)
- [x] IOntologyParser interface
- [x] RDFLibParser implementation
- [x] MetadataExtractor
- [x] ClassExtractor
- [x] ClassHierarchyBuilder
- [x] OntologyAnalyzer facade
- [x] Domain models (OntologyStructure, OntologyClass, etc.)
- [x] Exception handling
- [x] Logging

### ✅ Sprint 2: Structure Extraction (COMPLETED)
- [x] Report domain models (DomainReport, ReportSection)
- [x] StructureExtractor - maps ontology classes to report sections
- [x] SectionNumberGenerator - hierarchical numbering (1, 1.1, 1.2, etc.)
- [x] Section hierarchy management
- [x] Configurable max depth
- [x] Section statistics and queries
- [x] Comprehensive unit tests
- [x] Demo script showing end-to-end flow

### ✅ Sprint 3: Research Services Integration (COMPLETED)
- [x] Research domain models (ResearchResult, KnowledgeSource, Fact, etc.)
- [x] IResearchService interface - abstract interface for research sources
- [x] Web Search service - web content search with mock implementation
- [x] Wikidata client - structured knowledge from Wikidata
- [x] Academic API service - scholarly article search (Semantic Scholar, PubMed)
- [x] Research Orchestrator - coordinates multi-source parallel research
- [x] Caching system for research results
- [x] Exception handling for research failures
- [x] 20+ comprehensive unit tests

### ⏳ Sprint 4-12: In Progress

See project documentation for detailed sprint breakdown.

## Quality Metrics

Target quality scores (out of 100):

- **Overall Quality**: > 95
- **Scope Coverage**: 100 (based on UML ontology)
- **Comprehensiveness**: > 95
- **Correctness**: 100
- **Readability**: 95
- **Agile Artifacts**: 100
- **UML Coverage**: 95

Current code coverage: Target 90%+

## Design Patterns Used

1. **Facade Pattern**: OntologyAnalyzer
2. **Strategy Pattern**: Multiple parsers (RDFLib, OWLReady2)
3. **Factory Pattern**: Parser instantiation
4. **Template Method**: Research process
5. **Observer Pattern**: Progress notifications
6. **Repository Pattern**: Data access
7. **Adapter Pattern**: External service integrations
8. **Builder Pattern**: Report construction

## Technologies

### Core
- **Python 3.10+**: Primary language
- **FastAPI**: REST API framework
- **SQLAlchemy 2.0**: ORM and database toolkit
- **Pydantic**: Data validation

### Ontology Processing
- **RDFLib**: RDF parsing and manipulation
- **OWLReady2**: OWL ontology processing

### LLM Integration
- **OpenAI API**: GPT-4 integration
- **Anthropic API**: Claude integration

### Data Storage
- **PostgreSQL**: Primary database
- **Redis**: Caching layer

### Testing
- **pytest**: Testing framework
- **pytest-asyncio**: Async test support
- **pytest-cov**: Coverage reporting

### Code Quality
- **black**: Code formatting
- **isort**: Import sorting
- **mypy**: Static type checking
- **flake8**: Linting
- **bandit**: Security analysis

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Based on Agile SCRUM methodology
- Implements UML ontology for semantic modeling
- Follows enterprise software architecture patterns

---

**Built with ❤️ following Agile SCRUM and Clean Architecture principles**
