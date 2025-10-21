# Architecture Documentation

## Overview

The Autonomous Report Generator follows Clean Architecture principles with clear separation between domain logic, infrastructure, and presentation layers.

## System Architecture

### Layered Architecture

```
┌─────────────────────────────────────────────────────────┐
│                 Presentation Layer                       │
│  ┌──────────────────┐  ┌──────────────────┐            │
│  │   FastAPI REST   │  │  Python API      │            │
│  │   API + OpenAPI  │  │  (Direct Usage)  │            │
│  └──────────────────┘  └──────────────────┘            │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│              Orchestration Layer                         │
│         ReportOrchestrator                              │
│  (Coordinates end-to-end workflow)                      │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│                   Domain Layer                           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │Ontology  │ │Structure │ │Research  │ │Generation│  │
│  │          │ │          │ │          │ │          │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │Citations │ │Assembly  │ │Quality   │ │Export    │  │
│  │          │ │          │ │          │ │          │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│              Infrastructure Layer                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │Exporters │ │  Cache   │ │Monitoring│ │  LLM     │  │
│  │(MD, HTML,│ │(L1 + L2) │ │(Metrics) │ │Providers │  │
│  │PDF, etc.)│ │          │ │          │ │          │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
└─────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Domain Layer

Pure business logic with no external dependencies.

#### Ontology Module
- **Purpose**: Parse and analyze domain ontologies
- **Key Classes**:
  - `OntologyParser`: Interface for parsing OWL/RDF
  - `Concept`: Represents ontology concepts
  - `DomainOntology`: Container for ontology data
- **Dependencies**: None (pure domain)

#### Structure Module
- **Purpose**: Extract report structure from ontology
- **Key Classes**:
  - `StructureExtractor`: Maps concepts to sections
  - `DomainReport`: Report aggregate root
  - `ReportSection`: Individual report sections
- **Dependencies**: Ontology models

#### Research Module
- **Purpose**: Aggregate knowledge from sources
- **Key Classes**:
  - `ResearchAggregator`: Combines multi-source results
  - `ConflictResolver`: Handles contradictions
  - `ResearchOrchestrator`: Coordinates research
- **Dependencies**: None (uses interfaces)

#### Generation Module
- **Purpose**: Generate content using LLMs
- **Key Classes**:
  - `ContentGenerator`: Orchestrates generation
  - `ILLMProvider`: Provider interface
  - `GenerationRequest/Response`: DTOs
- **Dependencies**: None (uses interfaces)

#### Citations Module
- **Purpose**: Manage citations and bibliography
- **Key Classes**:
  - `CitationFormatterFactory`: Creates formatters
  - `BibliographyBuilder`: Builds bibliography
  - `Citation`, `Author`: Domain entities
- **Dependencies**: None

#### Assembly Module
- **Purpose**: Assemble final report
- **Key Classes**:
  - `ReportAssembler`: Combines all components
- **Dependencies**: Citations, Report models

#### Quality Module
- **Purpose**: Assess report quality
- **Key Classes**:
  - `QualityAssessor`: Orchestrates assessment
  - `ContentQualityChecker`: Content analysis
  - `ReadabilityAnalyzer`: Readability metrics
- **Dependencies**: Report models

#### Export Module
- **Purpose**: Define export interfaces
- **Key Classes**:
  - `IExporter`: Exporter interface
  - `ExportOptions`: Configuration
  - `ExportResult`: Result DTO
- **Dependencies**: Report models

### 2. Infrastructure Layer

Implements interfaces defined in domain layer.

#### Exporters
- `MarkdownExporter`: GitHub Flavored Markdown
- `HTMLExporter`: Responsive HTML5
- `PDFExporter`: ReportLab integration
- `DOCXExporter`: MS Word (python-docx)
- `XLSXExporter`: MS Excel (openpyxl)
- `ExportManager`: Coordinates exporters

#### Cache
- `InMemoryCache`: L1 fast cache (LRU)
- `FileCache`: L2 persistent cache
- `CacheManager`: Multi-level coordination

#### Monitoring
- `MetricsCollector`: Collects metrics
- `Counter`, `Gauge`, `Histogram`, `Timer`: Metric types
- Prometheus-compatible export

#### LLM Providers
- `OpenAIProvider`: OpenAI GPT integration
- `AnthropicProvider`: Anthropic Claude integration

### 3. Orchestration Layer

Coordinates domain workflows.

#### ReportOrchestrator
```python
class ReportOrchestrator:
    async def generate_report(config):
        # 1. Parse ontology
        ontology = await parse_ontology(config)

        # 2. Extract structure
        report = await extract_structure(ontology)

        # 3. Conduct research (optional)
        research_data = await conduct_research(config)

        # 4. Generate content
        report = await generate_content(report, research_data)

        # 5. Assemble with citations
        report = await assemble_report(report)

        # 6. Assess quality
        assessment = await assess_quality(report)

        return report, assessment
```

### 4. API Layer

REST API implementation with FastAPI.

#### Routes
- **Reports** (`/reports/`):
  - POST `/` - Create report
  - GET `/{id}` - Get report
  - GET `/` - List reports
  - DELETE `/{id}` - Delete report

- **Quality** (`/quality/`):
  - POST `/assess` - Assess quality
  - GET `/{report_id}` - Get assessment
  - GET `/{report_id}/issues` - Get issues

- **Export** (`/export/`):
  - POST `/` - Export report
  - GET `/{id}` - Get export status
  - GET `/{id}/download` - Download file
  - DELETE `/{id}` - Delete export

## Design Patterns

### 1. Facade Pattern
**Used in**: `OntologyAnalyzer`, `QualityAssessor`

Provides simplified interface to complex subsystems.

```python
class QualityAssessor:
    def __init__(self):
        self.content_checker = ContentQualityChecker()
        self.citation_checker = CitationQualityChecker()
        self.structure_checker = StructureQualityChecker()
        self.readability_analyzer = ReadabilityAnalyzer()

    async def assess(self, report):
        # Orchestrates all checkers
        ...
```

### 2. Strategy Pattern
**Used in**: Exporters, LLM Providers, Citation Formatters

Allows interchangeable algorithms.

```python
class IExporter(ABC):
    @abstractmethod
    async def export(self, report, path, options):
        pass

# Implementations: MarkdownExporter, HTMLExporter, etc.
```

### 3. Factory Pattern
**Used in**: `CitationFormatterFactory`, `ExportManager`

Creates objects without specifying exact class.

```python
class CitationFormatterFactory:
    def create_formatter(self, style: str):
        if style == "apa":
            return APAFormatter()
        elif style == "mla":
            return MLAFormatter()
        # ...
```

### 4. Builder Pattern
**Used in**: `BibliographyBuilder`, Report construction

Constructs complex objects step by step.

```python
class BibliographyBuilder:
    def add_citation(self, citation, sections):
        # ...

    def build(self) -> Bibliography:
        # ...
```

### 5. Template Method Pattern
**Used in**: Quality checkers, Exporters

Defines algorithm skeleton, subclasses override steps.

```python
class BaseQualityChecker(ABC):
    def check(self, report):
        # Template method
        self._validate_input(report)
        result = self._perform_check(report)
        self._log_result(result)
        return result

    @abstractmethod
    def _perform_check(self, report):
        pass
```

### 6. Observer Pattern
**Used in**: Metrics collection

Notifies observers of state changes.

```python
# Metrics automatically tracked
counter("reports_generated").increment()
```

### 7. Adapter Pattern
**Used in**: LLM provider integrations

Adapts external interfaces to domain interfaces.

```python
class OpenAIProvider(ILLMProvider):
    def __init__(self, client):
        self._client = client  # Adapts OpenAI client

    async def generate(self, request):
        # Adapts request/response
        ...
```

## Data Flow

### Report Generation Flow

```
User Request
     ↓
API Endpoint (FastAPI)
     ↓
ReportOrchestrator
     ↓
┌────────────────────────────────────┐
│ 1. OntologyParser                  │
│    └→ DomainOntology               │
└────────────────────────────────────┘
     ↓
┌────────────────────────────────────┐
│ 2. StructureExtractor              │
│    └→ DomainReport (skeleton)      │
└────────────────────────────────────┘
     ↓
┌────────────────────────────────────┐
│ 3. ResearchAggregator (optional)   │
│    └→ ResearchData                 │
└────────────────────────────────────┘
     ↓
┌────────────────────────────────────┐
│ 4. ContentGenerator                │
│    └→ DomainReport (with content)  │
└────────────────────────────────────┘
     ↓
┌────────────────────────────────────┐
│ 5. ReportAssembler                 │
│    └→ DomainReport (with citations)│
└────────────────────────────────────┘
     ↓
┌────────────────────────────────────┐
│ 6. QualityAssessor                 │
│    └→ QualityAssessment            │
└────────────────────────────────────┘
     ↓
Return: (Report, Assessment)
```

### Export Flow

```
Export Request
     ↓
ExportManager
     ↓
ExportManager.export()
     ↓
┌─────────────────────┐
│ Select Exporter     │
│ (based on format)   │
└─────────────────────┘
     ↓
Specific Exporter (MD, HTML, PDF, etc.)
     ↓
┌─────────────────────┐
│ Generate Content    │
│ Apply Templates     │
│ Format Output       │
└─────────────────────┘
     ↓
Write to File
     ↓
ExportResult
```

## Quality Assurance

### Testing Strategy

1. **Unit Tests**: Test individual components in isolation
   - Coverage target: 90%+
   - Mocking external dependencies
   - Fast execution (<1s)

2. **Integration Tests**: Test component interactions
   - End-to-end workflows
   - Real implementations
   - Moderate execution time

3. **Performance Tests**: Measure performance
   - Benchmarks for key operations
   - Load testing
   - Resource usage monitoring

### Quality Dimensions

Reports are assessed across 7 dimensions:

1. **Content**: Completeness, depth, coherence
2. **Structure**: Organization, hierarchy
3. **Citations**: Coverage, diversity
4. **Readability**: Flesch scores, grade level
5. **Completeness**: Section coverage
6. **Consistency**: Style, terminology
7. **Accuracy**: Factual correctness

## Performance Optimization

### Caching Strategy

```
Request
  ↓
L1 Cache (Memory) ──── Hit → Return
  ↓ Miss
L2 Cache (File) ──── Hit → Promote to L1 → Return
  ↓ Miss
Generate/Fetch
  ↓
Store in L1 + L2
  ↓
Return
```

### Metrics Collection

- **Counters**: Events (requests, errors)
- **Gauges**: Values (active connections)
- **Histograms**: Distributions (latencies)
- **Timers**: Durations (operations)

## Security Considerations

1. **Input Validation**: Pydantic models validate all inputs
2. **Error Handling**: No sensitive data in errors
3. **API Rate Limiting**: Prevent abuse
4. **File Access**: Controlled directory access
5. **LLM API Keys**: Environment variables only

## Scalability

### Horizontal Scaling
- Stateless API design
- Shared cache (Redis)
- Database connection pooling

### Vertical Scaling
- Async/await throughout
- Non-blocking I/O
- Memory-efficient caching

## Deployment

### Docker
```dockerfile
FROM python:3.10
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY src/ ./src/
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0"]
```

### Kubernetes
- Deployment for API
- Service for load balancing
- ConfigMap for configuration
- Secret for API keys

## Monitoring

### Metrics Endpoints
- `/metrics` - Prometheus metrics
- `/health` - Health check
- `/stats` - Cache statistics

### Logging
- Structured logging (JSON)
- Different log levels
- Request/response logging
- Error tracking

## Future Enhancements

1. **Async Task Queue**: Celery for background jobs
2. **Real-time Updates**: WebSocket for progress
3. **User Authentication**: JWT-based auth
4. **Multi-tenancy**: Tenant isolation
5. **Advanced Analytics**: Usage dashboards
6. **Plugin System**: Custom exporters/checkers

---

**Last Updated**: 2024
**Version**: 1.0.0
