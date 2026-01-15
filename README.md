# Black-Box Web Intelligence

An autonomous multi-agent system for reverse-engineering backend API specifications through dynamic UI analysis using the **Agentic Scientific Method**.

## Overview

This system treats web applications as "black boxes" and discovers their backend APIs by:
1. **Exploring** the UI through automated browser interaction
2. **Observing** network traffic triggered by UI actions
3. **Inferring** API schemas and business rules from observations
4. **Critiquing** hypotheses to prevent hallucination
5. **Probing** to validate inferences experimentally
6. **Updating** knowledge with confidence-weighted evidence

## Scientific Loop

```
┌─────────────────────────────────────────────────────────────────┐
│                    AGENTIC SCIENTIFIC LOOP                      │
│                                                                 │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐                 │
│   │ EXPLORE  │───▶│ OBSERVE  │───▶│  INFER   │                 │
│   │Navigator │    │Interceptor│    │ Analyst  │                 │
│   └──────────┘    └──────────┘    └────┬─────┘                 │
│        ▲                               │                        │
│        │                               ▼                        │
│   ┌────┴─────┐    ┌──────────┐    ┌──────────┐                 │
│   │  UPDATE  │◀───│  PROBE   │◀───│ CRITIQUE │                 │
│   │  Memory  │    │ Verifier │    │  Critic  │                 │
│   └──────────┘    └──────────┘    └──────────┘                 │
│                                                                 │
│   Loop terminates when: confidence ≥ threshold for all         │
│   hypotheses AND frontier is exhausted AND critic approves     │
└─────────────────────────────────────────────────────────────────┘
```

## Features

- **6 Specialized Agents**: Navigator, Interceptor, Analyst, Business Logic, Critic, Verifier
- **Hypothesis-Driven**: Every inference is a hypothesis with confidence scores
- **Adversarial Critic**: Actively challenges inferences to prevent hallucination
- **Dual LLM Support**: Works with both OpenAI GPT-4 and Anthropic Claude
- **Real-time Dashboard**: Monitor exploration progress with WebSocket updates
- **OpenAPI Export**: Generate Swagger specifications from discovered APIs
- **Business Rule Detection**: Infers state machines, permissions, rate limits

## Architecture

```
black_box_web_intel/
├── backend/
│   ├── agents/           # 6 specialized agents
│   ├── browser/          # Playwright automation
│   ├── memory/           # Global memory & hypothesis store
│   ├── inference/        # Schema merging & URL clustering
│   ├── llm/              # OpenAI & Anthropic clients
│   ├── api/              # FastAPI REST & WebSocket
│   └── core/             # Config, models, guardrails
├── frontend/             # Next.js dashboard
└── requirements.txt
```

## Installation

### Prerequisites

- Python 3.11+
- Node.js 18+
- An OpenAI or Anthropic API key

### Backend Setup

```bash
cd black_box_web_intel

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Configure environment (IMPORTANT: Add your API keys!)
cp env.template .env
# Edit .env with your API keys (see Configuration section below)
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Build for production (optional)
npm run build
```

## Usage

### Start the Backend

```bash
cd black_box_web_intel
source venv/bin/activate

# Run the API server
uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Start the Frontend

```bash
cd frontend
npm run dev
```

### Access the Dashboard

Open http://localhost:3000 in your browser.

### API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Configuration

### Setting Up API Keys

1. **Copy the template file:**
   ```bash
   cd black_box_web_intel
   cp env.template .env
   ```

2. **Edit `.env` and add your API key:**
   ```bash
   # Open in your editor
   nano .env   # or: code .env
   ```

3. **Get your API key:**
   - **OpenAI**: Get from https://platform.openai.com/api-keys
   - **Anthropic**: Get from https://console.anthropic.com/

### Configuration Options

```bash
# LLM Provider - choose "openai" or "anthropic"
LLM_PROVIDER=openai

# API Keys - add YOUR key here
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxx
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxx

# Models
OPENAI_MODEL=gpt-4o
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022

# Safety
MAX_REQUESTS_PER_MINUTE=60
MAX_LOOP_ITERATIONS=1000
CONFIDENCE_THRESHOLD=0.7

# Probing
ENABLE_PROBING=true
ENABLE_FUZZING=false  # Disabled by default for safety
```

## Agents

### Navigator (The Explorer)
Autonomously explores the web UI using ReAct reasoning. Prioritizes actions likely to trigger API calls.

### Interceptor (The Observer)
Captures all network traffic and correlates requests to UI actions.

### Analyst (The Theorist)
Infers API schemas from observed traffic using genson for schema merging.

### Business Logic Agent (The Workflow Detective)
Detects state machines, enforced sequences, permissions, and rate limits.

### Critic (The Skeptic)
**Critical for preventing hallucination.** Challenges every hypothesis, enumerates alternatives, and penalizes overconfidence.

### Verifier (The Experimentalist)
Validates hypotheses through controlled API probing. NOT for exploitation.

## Hypothesis System

Every inference is tracked as a hypothesis:

```python
{
    "id": "hyp_endpoint_users_001",
    "type": "endpoint_schema",
    "description": "GET /api/users/{id} returns user profile",
    "confidence": 0.65,
    "supporting_evidence": [...],
    "competing_explanations": [...],
    "untested_assumptions": [...],
    "confidence_history": [
        {"event": "initial_inference", "confidence": 0.35},
        {"event": "evidence_added", "confidence": 0.55},
        {"event": "probe_confirmed", "confidence": 0.65}
    ]
}
```

## Ethics & Guardrails

**This system is for AUTHORIZED USE ONLY.**

- Users must have explicit permission to analyze target systems
- The system performs validation probing, NOT exploitation
- Rate limiting prevents overwhelming targets
- Blocked patterns prevent dangerous actions (logout, delete, etc.)
- External tracking domains are automatically filtered

## API Endpoints

### Sessions
- `POST /api/sessions` - Create new exploration session
- `GET /api/sessions` - List all sessions
- `GET /api/sessions/{id}` - Get session details
- `DELETE /api/sessions/{id}` - Delete session

### Hypotheses
- `GET /api/hypotheses/{session_id}` - List hypotheses
- `GET /api/hypotheses/{session_id}/{id}` - Get hypothesis details
- `GET /api/hypotheses/{session_id}/disagreements` - Get contested hypotheses

### Schemas
- `GET /api/schemas/{session_id}/openapi` - Export OpenAPI spec
- `GET /api/schemas/{session_id}/endpoints` - List discovered endpoints
- `GET /api/schemas/{session_id}/business-rules` - List business rules

### Control
- `POST /api/control/start` - Start exploration
- `POST /api/control/stop` - Stop exploration
- `GET /api/control/status/{session_id}` - Get exploration status

### WebSocket
- `WS /ws/{session_id}` - Real-time event stream

## License

This project is for educational and authorized security research purposes only.

## Acknowledgments

Built with:
- [LangGraph](https://github.com/langchain-ai/langgraph) - Agent orchestration
- [Playwright](https://playwright.dev/) - Browser automation
- [FastAPI](https://fastapi.tiangolo.com/) - API framework
- [Next.js](https://nextjs.org/) - Frontend framework
- [genson](https://github.com/wolverdude/GenSON) - JSON schema generation
- [ChromaDB](https://www.trychroma.com/) - Vector storage
