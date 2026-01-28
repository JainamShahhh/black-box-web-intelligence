# Black-Box Web Intelligence

**Autonomous Multi-Agent System for API Reverse Engineering & Security Analysis**

[![License: Proprietary](https://img.shields.io/badge/License-Proprietary-red.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![Next.js 14](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org)

> 🔬 **AI Tinkerers Demo Project** - Built by Jainam Shah

---

## What is This?

Black-Box Web Intelligence is a tool that **automatically discovers APIs and security vulnerabilities** by watching how a website works—without needing any source code or documentation.

**Think of it like this:** Instead of reading a restaurant's menu (documentation), you watch what other customers order and figure out what's available.

---

## Features

- 🔍 **Autonomous Exploration** - AI agents click through websites automatically
- 📡 **API Discovery** - Captures and analyzes network traffic
- 📋 **Schema Inference** - Generates OpenAPI specs from observed data
- 🔐 **Security Scanning** - Detects OWASP Top 10 vulnerabilities
- 🧠 **Multi-Agent System** - 6 specialized AI agents working together
- 📊 **Real-Time Dashboard** - Watch the analysis happen live

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Chrome browser

### Installation

```bash
# Clone the repository
git clone https://github.com/JainamShahhh/black-box-web-intelligence.git
cd black-box-web-intelligence

# Set up Python environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Set up frontend
cd frontend
npm install
cd ..

# Configure API keys
cp env.template .env
# Edit .env and add your API keys (GEMINI_API_KEY or OPENAI_API_KEY)
```

### Running

```bash
# Start the backend (in one terminal)
source venv/bin/activate
python -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8000

# Start the frontend (in another terminal)
cd frontend
npm run dev
```

Then open http://localhost:3000 in your browser.

---

## How It Works

The system uses a **Scientific Loop** with 6 phases:

```
EXPLORE → OBSERVE → INFER → CRITIQUE → PROBE → UPDATE
   ↑                                              ↓
   └──────────── (repeat until confident) ←───────┘
```

1. **EXPLORE** - Navigator agent clicks through the UI
2. **OBSERVE** - Interceptor captures network traffic
3. **INFER** - Analyst builds API schemas from data
4. **CRITIQUE** - Critic challenges hypotheses
5. **PROBE** - Verifier tests edge cases
6. **UPDATE** - Memory stores validated findings

---

## Project Structure

```
black_box_web_intel/
├── backend/
│   ├── agents/          # AI agents (Navigator, Analyst, Critic...)
│   ├── api/             # FastAPI endpoints
│   ├── browser/         # Playwright automation
│   ├── inference/       # Schema merging, security analysis
│   ├── llm/             # LLM provider adapters
│   └── memory/          # SQLite, ChromaDB, in-memory stores
├── frontend/
│   ├── app/             # Next.js pages
│   └── components/      # React components
├── PRESENTATION.html    # Visual demo presentation
└── COMPLETE_GUIDE.md    # Detailed technical documentation
```

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Python, FastAPI, LangGraph |
| Frontend | Next.js 14, React, TailwindCSS |
| Browser Automation | Playwright with CDP |
| Database | SQLite, ChromaDB |
| AI/LLM | Gemini 2.0 Flash, OpenAI (configurable) |

---

## Documentation

- **[COMPLETE_GUIDE.md](COMPLETE_GUIDE.md)** - Comprehensive technical documentation for beginners
- **[PRESENTATION.html](PRESENTATION.html)** - Visual presentation (open in browser)
- **[PRESENTATION_SCRIPT.md](PRESENTATION_SCRIPT.md)** - Talk script and Q&A prep

---

## License

This project is **proprietary software**. All rights reserved.  
See [LICENSE](LICENSE) for details.

---

## Author

**Jainam Shah** - Machine Learning Engineer

---

*Built for AI Tinkerers Edmonton 2026*
