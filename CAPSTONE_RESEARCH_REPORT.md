# Black-Box Web Intelligence: Autonomous Multi-Agent API Reverse Engineering

## Capstone Research Report | January 2026

---

## Abstract

This research presents **Black-Box Web Intelligence**, a novel autonomous multi-agent system that reverse-engineers backend API specifications through dynamic UI analysis. Operating as a "black box" observer, the system interacts with web applications solely through their user interfaces while passively capturing network traffic.

The system implements the **Agentic Scientific Method**—a six-phase iterative loop: **Explore → Observe → Infer → Critique → Probe → Update**. This methodology mirrors human scientific inquiry, where hypotheses about API behavior are continuously formed, challenged, and refined.

**Keywords:** API Reverse Engineering, Multi-Agent Systems, Web Security, LLMs, Schema Inference

---

## 1. Introduction

### 1.1 Problem Statement

Given a web application URL with no source code, documentation, or server access:

> **Autonomously discover and document the complete backend API surface, including endpoint patterns, schemas, authentication mechanisms, and security vulnerabilities.**

### 1.2 Research Contributions

1. **Agentic Scientific Method**: Novel six-phase exploration loop
2. **Multi-Agent Orchestration**: Specialized agents via LangGraph
3. **Hypothesis Confidence Scoring**: Evidence-based updates
4. **Real-Time Visualization**: Live phase tracking dashboard
5. **Comprehensive Security Analysis**: OWASP mapping, CVE detection, JWT analysis

---

## 2. System Architecture

### 2.1 High-Level Design

```
┌────────────────────────────────────────────────────────────┐
│                  BLACK-BOX WEB INTELLIGENCE                │
├────────────────────────────────────────────────────────────┤
│  ┌──────────┐    ┌──────────┐    ┌──────────┐            │
│  │ FastAPI  │────│ LangGraph│────│ Next.js  │            │
│  │ Backend  │    │Supervisor│    │Dashboard │            │
│  └──────────┘    └──────────┘    └──────────┘            │
│                        │                                   │
│  ┌─────────────────────────────────────────────────────┐  │
│  │                   AGENT LAYER                       │  │
│  │ Navigator│Interceptor│Analyst│Critic│Verifier       │  │
│  └─────────────────────────────────────────────────────┘  │
│                        │                                   │
│  ┌─────────────────────────────────────────────────────┐  │
│  │                  MEMORY LAYER                       │  │
│  │     SQLite │ ChromaDB │ Hypothesis Store            │  │
│  └─────────────────────────────────────────────────────┘  │
│                        │                                   │
│  ┌─────────────────────────────────────────────────────┐  │
│  │                 BROWSER LAYER                       │  │
│  │   Playwright Stealth │ Network Interception         │  │
│  └─────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
```

### 2.2 Directory Structure

```
black_box_web_intel/
├── backend/
│   ├── agents/           # LangGraph agents
│   │   ├── supervisor.py # Orchestration
│   │   ├── navigator.py  # UI exploration
│   │   ├── interceptor.py# Traffic capture
│   │   ├── analyst.py    # Schema inference
│   │   ├── critic.py     # Hypothesis challenger
│   │   └── verifier.py   # Probe execution
│   ├── api/routes/       # REST endpoints
│   ├── inference/        # Analysis modules
│   │   ├── tech_intel.py
│   │   ├── security_analyzer.py
│   │   └── report_generator.py
│   ├── browser/          # Playwright automation
│   └── memory/           # Persistence layer
├── frontend/
│   ├── app/              # Next.js pages
│   └── components/       # React components
└── start.sh              # One-command startup
```

---

## 3. The Agentic Scientific Method

### 3.1 Six-Phase Loop

```
    ┌─────────┐    ┌─────────┐    ┌─────────┐
    │ EXPLORE │───▶│ OBSERVE │───▶│  INFER  │
    └─────────┘    └─────────┘    └─────────┘
         ▲                              │
         │                              ▼
    ┌─────────┐    ┌─────────┐    ┌─────────┐
    │ UPDATE  │◀───│  PROBE  │◀───│CRITIQUE │
    └─────────┘    └─────────┘    └─────────┘
```

### 3.2 Phase Details

| Phase | Agent | Purpose |
|-------|-------|---------|
| **EXPLORE** | Navigator | Click buttons, fill forms, discover UI |
| **OBSERVE** | Interceptor | Capture network traffic, filter API calls |
| **INFER** | Analyst | Generate hypotheses, infer JSON schemas |
| **CRITIQUE** | Critic | Challenge hypotheses, propose edge cases |
| **PROBE** | Verifier | Execute HTTP tests, validate hypotheses |
| **UPDATE** | Memory | Update confidence scores, persist findings |

### 3.3 Termination Conditions

- Max iterations reached (default: 50)
- Convergence (no new discoveries for N iterations)
- User cancellation

---

## 4. Agent Specifications

### 4.1 Navigator Agent
- **Type**: LLM-Driven
- **Input**: Accessibility tree, exploration history
- **Output**: Action decision (click, type, scroll)
- **Capabilities**: Form detection, intelligent filling, pagination

### 4.2 Interceptor Agent
- **Type**: Deterministic
- **Input**: Raw network traffic
- **Output**: Filtered API observations
- **Filtering**: Excludes static assets, tracking pixels

### 4.3 Analyst Agent
- **Type**: Hybrid (Statistical + LLM)
- **Input**: Observations
- **Output**: Hypotheses with JSON schemas
- **Method**: URL clustering + genson schema building + LLM enrichment

### 4.4 Critic Agent
- **Type**: LLM-Driven
- **Input**: Hypotheses
- **Output**: Reviews, proposed probes
- **Critique Dimensions**: Completeness, type accuracy, edge cases

### 4.5 Verifier Agent
- **Type**: Deterministic + HTTP
- **Input**: Probes from Critic
- **Output**: Test results
- **Probes**: Existence, schema validation, auth testing

---

## 5. Security Analysis Module

### 5.1 Capabilities

| Feature | Description |
|---------|-------------|
| **Header Analysis** | HSTS, CSP, CORS, X-Frame-Options |
| **JWT Analysis** | Algorithm detection, claim extraction |
| **OWASP Mapping** | Findings mapped to Top 10 categories |
| **CVE Detection** | Known vulnerabilities by version |
| **Exposed Data** | Emails, IPs, API keys, tokens |
| **LLM Analysis** | AI-powered deep vulnerability scan |

### 5.2 Security Headers Checked

```python
REQUIRED_HEADERS = [
    'Strict-Transport-Security',  # HSTS
    'Content-Security-Policy',    # CSP
    'X-Frame-Options',            # Clickjacking
    'X-Content-Type-Options',     # MIME sniffing
]
```

### 5.3 Exposed Data Patterns

```python
SENSITIVE_PATTERNS = {
    'emails': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
    'ips': r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
    'api_keys': r'(?:api[_-]?key)["\s:=]+([a-zA-Z0-9_-]{20,})',
    'aws_keys': r'AKIA[0-9A-Z]{16}',
}
```

---

## 6. Technology Stack Detection

### 6.1 Fingerprinting Methods

- **Header Analysis**: `Server`, `X-Powered-By`
- **Error Messages**: Stack traces, database errors
- **Cookie Names**: `PHPSESSID`, `connect.sid`, `csrftoken`
- **Response Patterns**: Framework-specific structures

### 6.2 Detected Categories

| Category | Examples |
|----------|----------|
| Framework | Django, Express, Rails, FastAPI, Spring |
| Database | PostgreSQL, MySQL, MongoDB, Redis |
| Server | nginx, Apache, Gunicorn, Uvicorn |
| CDN | Cloudflare, AWS CloudFront |
| Auth | JWT, Session, OAuth, API Key |

---

## 7. Frontend Dashboard

### 7.1 Components

| Component | Purpose |
|-----------|---------|
| `WorkflowGraph` | Scientific loop visualization |
| `TechStack` | Technology detection display |
| `SecurityPanel` | Vulnerability findings |
| `SchemaViewer` | JSON schema explorer |
| `ExplorationMap` | FSM state diagram |
| `HypothesisCard` | Individual hypothesis details |

### 7.2 Real-Time Updates

- WebSocket connection for live phase transitions
- Auto-refreshing observation counts
- Live confidence score updates

---

## 8. API Reference

### 8.1 Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/sessions` | GET, POST | Session management |
| `/api/control/start/{id}` | POST | Start exploration |
| `/api/control/stop/{id}` | POST | Stop exploration |
| `/api/control/status/{id}` | GET | Current phase/iteration |
| `/api/observations/{id}` | GET | Network observations |
| `/api/hypotheses/{id}` | GET | Inferred hypotheses |
| `/api/tech/{id}` | GET | Tech stack fingerprints |

### 8.2 Security Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/security/{id}/vulnerabilities` | GET | Security findings |
| `/api/security/{id}/jwt` | GET | JWT token analysis |
| `/api/security/{id}/exposed-data` | GET | Exposed sensitive data |
| `/api/security/{id}/llm-analysis` | POST | AI vulnerability scan |
| `/api/security/{id}/report/markdown` | GET | Full security report |
| `/api/security/{id}/report/openapi` | GET | Generated OpenAPI spec |

---

## 9. Experimental Results

### 9.1 Test Target: PokeAPI

| Metric | Value |
|--------|-------|
| API Calls Captured | 47 |
| Unique Endpoints | 12 |
| Schemas Inferred | 8 |
| Technologies Detected | 3 |
| Security Issues | 2 |

### 9.2 Performance

| Metric | Value |
|--------|-------|
| Average iteration time | 4.2 seconds |
| LLM calls per iteration | 2-3 |
| Memory usage | ~250 MB |

---

## 10. Future Work

1. **Authentication Handling**: OAuth, session management
2. **GraphQL Introspection**: Full schema extraction
3. **WebSocket Analysis**: Real-time protocol support
4. **Distributed Execution**: Scale across instances
5. **Cloud Deployment**: Kubernetes orchestration

---

## 11. Conclusions

This research demonstrates the viability of **autonomous API reverse engineering** through the **Agentic Scientific Method**. The system successfully:

1. Navigated web applications without prior knowledge
2. Captured and analyzed API traffic patterns
3. Inferred accurate schemas with high confidence
4. Detected security vulnerabilities mapped to OWASP
5. Generated comprehensive reports including OpenAPI specs

The multi-agent architecture proved effective for separation of concerns, with each agent contributing specialized capabilities.

---

## Appendix: Startup

```bash
# One-command startup
cd black_box_web_intel
./start.sh

# Manual
python -m uvicorn backend.api.main:app --port 8000 &
cd frontend && npm run dev
```

---

*© 2026 Black-Box Web Intelligence Project*
