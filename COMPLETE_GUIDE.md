# Complete Guide to Black-Box Web Intelligence

**Everything You Need to Know - Explained for Beginners**

---

## Table of Contents

1. [What Does This Project Do?](#1-what-does-this-project-do)
2. [Key Concepts & Definitions](#2-key-concepts--definitions)
3. [The Architecture - How It All Fits Together](#3-the-architecture)
4. [The Scientific Loop - Step by Step](#4-the-scientific-loop)
5. [The 6 AI Agents - What Each One Does](#5-the-6-ai-agents)
6. [Network Interception - How We Capture Traffic](#6-network-interception)
7. [Schema Inference - Building API Specs](#7-schema-inference)
8. [Security Analysis - Finding Vulnerabilities](#8-security-analysis)
9. [Storage Systems - Why 3 Databases?](#9-storage-systems)
10. [The Frontend Dashboard](#10-the-frontend-dashboard)
11. [Code Walkthrough - Key Files](#11-code-walkthrough)
12. [Common Questions & Answers](#12-common-questions)

---

## 1. What Does This Project Do?

### The Problem

Imagine you want to understand how a website's backend works, but you don't have:
- Access to the source code
- Any documentation
- Server access

All you have is the URL. How do you figure out what API endpoints exist? What data they return? What security issues they have?

### The Solution

This project creates **autonomous AI agents** that:

1. **Click through websites** like a human would
2. **Capture all network traffic** (API calls)
3. **Analyze the patterns** to understand the API structure
4. **Generate documentation** (OpenAPI specs)
5. **Find security vulnerabilities** (OWASP Top 10)

### Real-World Use Cases

- **Security Audits**: Test web applications for vulnerabilities
- **API Documentation**: Reverse-engineer undocumented APIs
- **Reconnaissance**: Understand a target system's architecture
- **Quality Assurance**: Verify API behavior matches expectations

---

## 2. Key Concepts & Definitions

### What is an API?

**API (Application Programming Interface)** = A way for programs to talk to each other.

When you use a website:
1. You click a button
2. Your browser sends a **request** to a server
3. The server sends back a **response**
4. The website shows you the result

Example:
```
Request:  GET https://api.pokemon.co/pokemon/pikachu
Response: {"name": "pikachu", "id": 25, "type": "electric"}
```

### What is Reverse Engineering?

**Reverse Engineering** = Figuring out how something works by examining its behavior, not its blueprints.

Like figuring out a recipe by tasting a dish, instead of reading the cookbook.

### What is Black-Box Testing?

**Black-Box** = You can't see inside. You only interact with inputs and outputs.

Opposite of **White-Box** = You have full access to source code.

### What is an AI Agent?

**Agent** = An AI that can take actions, not just answer questions.

Regular AI: "You should click the login button"
Agent AI: *actually clicks the login button*

### What is a Multi-Agent System?

**Multi-Agent System** = Multiple specialized AI agents working together.

Like a team where:
- One person navigates
- One person takes notes
- One person analyzes
- One person critiques

### What is a Hypothesis?

**Hypothesis** = An educated guess that can be tested.

Example: "I think GET /api/users returns a list of users"
- If we test it and get users back → hypothesis confirmed
- If we get an error → hypothesis falsified

### What is Confidence Scoring?

**Confidence** = How sure are we that something is true? (0% to 100%)

- See an endpoint once → 50% confidence
- See it work 5 times → 85% confidence
- See it fail → confidence drops

---

## 3. The Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         FRONTEND                            │
│                    (Next.js Dashboard)                      │
│          localhost:3000 - Real-time visualization           │
└───────────────────────────┬─────────────────────────────────┘
                            │ WebSocket + REST API
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                         BACKEND                             │
│                    (FastAPI + LangGraph)                    │
│                      localhost:8000                         │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                  AGENTIC LOOP                         │  │
│  │                                                       │  │
│  │   Navigator ──► Interceptor ──► Analyst               │  │
│  │       ▲                              │                │  │
│  │       │                              ▼                │  │
│  │   Memory   ◄── Verifier ◄── Critic                   │  │
│  │                                                       │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐          │
│  │   SQLite    │ │  ChromaDB   │ │  In-Memory  │          │
│  │  (Sessions) │ │  (Vectors)  │ │   (Cache)   │          │
│  └─────────────┘ └─────────────┘ └─────────────┘          │
└───────────────────────────┬─────────────────────────────────┘
                            │ Chrome DevTools Protocol
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    HEADLESS BROWSER                         │
│                 (Playwright + Chrome)                       │
│        Automated clicking, typing, navigation               │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTP/HTTPS
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    TARGET WEBSITE                           │
│              (The site being analyzed)                      │
└─────────────────────────────────────────────────────────────┘
```

### Technology Stack Explained

| Technology | What It Does | Why We Use It |
|------------|--------------|---------------|
| **FastAPI** | Python web framework | Fast, async, automatic API docs |
| **LangGraph** | Agent orchestration | Controls agent flow and state |
| **Playwright** | Browser automation | Click, type, navigate programmatically |
| **CDP** | Chrome DevTools Protocol | Capture network traffic with bodies |
| **Next.js** | React framework | Modern dashboard with SSR |
| **SQLite** | Database | Store sessions, observations |
| **ChromaDB** | Vector database | Semantic similarity search |
| **Gemini/OpenAI** | LLM providers | Power the AI agents |

---

## 4. The Scientific Loop

The core innovation is treating API discovery like a **scientific experiment**.

### The 6 Phases

```
Phase 1: EXPLORE    "What should I do next?"
Phase 2: OBSERVE    "What happened?"
Phase 3: INFER      "What does this mean?"
Phase 4: CRITIQUE   "Are we sure about that?"
Phase 5: PROBE      "Let's test edge cases"
Phase 6: UPDATE     "Record what we learned"
         ↓
    (Loop back to Phase 1)
```

### Why a Loop?

Because one observation isn't enough. Consider:

**First loop:**
- Click login button
- See: POST /api/auth/login
- Hypothesis: "This endpoint handles login"
- Confidence: 50%

**Second loop:**
- Try with wrong password
- See: POST /api/auth/login → 401 error
- Hypothesis confirmed: It does auth!
- Confidence: 70%

**Third loop:**
- Try with correct password
- See: POST /api/auth/login → 200 + JWT token
- Hypothesis refined: "Returns JWT on success"
- Confidence: 85%

Each loop **increases confidence** through evidence.

### When Does It Stop?

The loop stops when:
1. Confidence on all hypotheses > 85%
2. Maximum iterations reached (default: 50)
3. No new discoveries for several loops
4. User manually stops

---

## 5. The 6 AI Agents

### Agent 1: Navigator

**Job:** Click through the website to trigger API calls

**How it works:**
1. Gets the page's accessibility tree (like what screen readers see)
2. LLM decides what to click/type next
3. Avoids clicking the same thing twice
4. Prioritizes unexplored areas

**Key file:** `backend/agents/navigator.py`

**Example decision:**
```
Input: "Page has: [Login button], [Sign up button], [About link]"
Output: "Click Login button - likely to trigger auth API calls"
```

### Agent 2: Interceptor

**Job:** Capture all network traffic

**How it works:**
1. Uses Chrome DevTools Protocol (CDP)
2. Intercepts every request and response
3. Extracts: URL, method, headers, body, status
4. Filters out noise (images, CSS, tracking pixels)

**Key file:** `backend/agents/interceptor.py`

**Example capture:**
```python
{
    "url": "https://api.example.com/users",
    "method": "GET",
    "status": 200,
    "headers": {"content-type": "application/json"},
    "body": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
}
```

### Agent 3: Analyst

**Job:** Make sense of the captured data

**How it works:**
1. Clusters similar URLs: `/users/1`, `/users/2` → `/users/{id}`
2. Builds JSON schemas from examples
3. Detects patterns (pagination, auth, rate limits)
4. Creates hypotheses about API structure

**Key file:** `backend/agents/analyst.py`

**Example inference:**
```
Observations:
  - GET /users/1 → {"id": 1, "name": "Alice"}
  - GET /users/2 → {"id": 2, "name": "Bob"}

Hypothesis:
  - Endpoint: GET /users/{id}
  - Schema: {"id": integer, "name": string}
```

### Agent 4: Critic

**Job:** Challenge hypotheses (devil's advocate)

**How it works:**
1. Finds weaknesses in current hypotheses
2. Proposes edge cases to test
3. Adjusts confidence scores
4. Prevents false confidence

**Key file:** `backend/agents/critic.py`

**Example critique:**
```
Hypothesis: "GET /users/{id} always returns 200"

Critic says:
- "What about id=-1?"
- "What about id=999999?"
- "What if not authenticated?"

Proposed probes:
- GET /users/-1 → expect 4xx
- GET /users/999999 → expect 404
```

### Agent 5: Verifier

**Job:** Actually test the edge cases

**How it works:**
1. Executes HTTP requests suggested by Critic
2. Compares actual vs expected results
3. Reports success/failure
4. Provides evidence for confidence updates

**Key file:** `backend/agents/verifier.py`

**Example probe:**
```
Test: GET /api/users/-1
Expected: 4xx error
Actual: 400 Bad Request
Result: SUCCESS ✓
```

### Agent 6: BusinessLogic (Bonus)

**Job:** Detect high-level patterns

**How it works:**
1. Identifies rate limiting patterns
2. Detects authentication flows
3. Maps user workflows
4. Understands business rules

**Key file:** `backend/agents/business_logic.py`

**Example detection:**
```
Pattern: Rate Limiting
Evidence: 
  - 429 response after 100 requests
  - Retry-After header: 60 seconds
  - X-RateLimit-Remaining header decreasing
```

---

## 6. Network Interception

### The Problem

Playwright's built-in methods don't give us everything:

```python
# This works, but...
page.on('response', handle_response)
# ...we can't get the response BODY easily
```

### The Solution: Chrome DevTools Protocol (CDP)

CDP gives us direct access to Chrome's internals.

```python
# Create CDP session
cdp = await page.context.new_cdp_session(page)

# Enable network monitoring
await cdp.send("Network.enable")

# Listen for responses
cdp.on("Network.responseReceived", handle_response)

async def handle_response(event):
    # Get the body (CDP-specific method)
    body = await cdp.send("Network.getResponseBody", 
                          {"requestId": event["requestId"]})
    # Now we have EVERYTHING
```

### What We Filter Out

Not every request is an API call:

| Type | Example | Keep? |
|------|---------|-------|
| API | `/api/users` | ✅ Yes |
| HTML | `/index.html` | ❌ No |
| CSS | `/styles.css` | ❌ No |
| JavaScript | `/app.js` | ❌ No |
| Images | `/logo.png` | ❌ No |
| Fonts | `/font.woff` | ❌ No |
| Analytics | `google-analytics.com` | ❌ No |

Filter code:
```python
def is_api_call(url, content_type):
    # Skip static assets
    if any(ext in url for ext in ['.js', '.css', '.png', '.jpg']):
        return False
    # Skip tracking
    if 'analytics' in url or 'tracking' in url:
        return False
    # Keep JSON responses
    if 'application/json' in content_type:
        return True
    return False
```

---

## 7. Schema Inference

### Step 1: URL Clustering

Raw URLs:
```
/api/pokemon/1
/api/pokemon/25
/api/pokemon/150
/api/users/alice
/api/users/bob
```

Clustered:
```
/api/pokemon/{id}     (id is integer)
/api/users/{username} (username is string)
```

### Step 2: Schema Building with Genson

```python
from genson import SchemaBuilder

builder = SchemaBuilder()
builder.add_object({"id": 1, "name": "Bulbasaur", "hp": 45})
builder.add_object({"id": 25, "name": "Pikachu", "hp": 35})
builder.add_object({"id": 150, "name": "Mewtwo", "hp": null})

schema = builder.to_schema()
# Result:
# {
#   "type": "object",
#   "properties": {
#     "id": {"type": "integer"},
#     "name": {"type": "string"},
#     "hp": {"type": ["integer", "null"]}  # Handles nulls!
#   }
# }
```

### Step 3: LLM Enrichment

The schema is correct but not helpful. LLM adds meaning:

Before:
```json
{"type": "string"}
```

After:
```json
{
  "type": "string",
  "format": "email",
  "description": "User's email address",
  "example": "user@example.com"
}
```

### Step 4: OpenAPI Generation

Final output is a complete OpenAPI 3.0 spec:

```yaml
openapi: 3.0.0
info:
  title: Inferred API
  version: 1.0.0
paths:
  /api/pokemon/{id}:
    get:
      summary: Get Pokemon by ID
      parameters:
        - name: id
          in: path
          schema:
            type: integer
      responses:
        200:
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Pokemon'
```

---

## 8. Security Analysis

### What We Check

**1. Security Headers**

| Header | Purpose | Finding if Missing |
|--------|---------|-------------------|
| Strict-Transport-Security | Force HTTPS | Downgrade attack risk |
| Content-Security-Policy | Prevent XSS | Script injection risk |
| X-Frame-Options | Prevent clickjacking | UI redress attack |
| X-Content-Type-Options | Prevent MIME sniffing | Content confusion |

**2. CORS Configuration**

```
Access-Control-Allow-Origin: *   ← BAD (allows any site)
Access-Control-Allow-Origin: https://trusted.com   ← GOOD
```

**3. JWT Analysis**

We base64-decode JWT tokens and check:

```python
# Dangerous patterns
if header["alg"] == "none":       # No signature!
    report_vulnerability("JWT accepts 'none' algorithm")

if header["alg"] == "HS256":
    # Check if symmetric key might be weak
    pass
```

**4. Exposed Secrets**

Pattern matching for leaked credentials:

```python
PATTERNS = {
    'api_key': r'["\']?api[_-]?key["\']?\s*[:=]\s*["\']?([a-zA-Z0-9]{20,})',
    'aws_key': r'AKIA[0-9A-Z]{16}',
    'private_key': r'-----BEGIN (RSA|EC|OPENSSH) PRIVATE KEY-----',
    'password': r'password\s*=\s*["\']([^"\']+)["\']'
}
```

**5. Error Message Leakage**

Bad error response (leaks info):
```json
{
  "error": "MySQL syntax error near 'SELECT * FROM users WHERE id=1'"
}
```

Good error response:
```json
{
  "error": "An error occurred"
}
```

### OWASP Top 10 Mapping

Every finding is mapped to OWASP categories:

| Code | Category | Example Finding |
|------|----------|-----------------|
| A01 | Broken Access Control | CORS wildcard |
| A02 | Cryptographic Failures | Missing HSTS, weak JWT |
| A03 | Injection | SQLi in error messages |
| A05 | Security Misconfiguration | Missing headers |
| A09 | Logging Failures | No rate limiting |

---

## 9. Storage Systems

### Why 3 Different Databases?

Each is optimized for different access patterns:

### SQLite - Relational Data

**What it stores:**
- Sessions (metadata, status, timestamps)
- Observations (captured requests/responses)
- Hypotheses (endpoint, schema, confidence)
- FSM states (current phase, transitions)

**Why SQLite:**
- ACID transactions (data integrity)
- Complex queries with JOINs
- Persistent across restarts
- No external dependencies

**Example query:**
```sql
SELECT * FROM observations 
WHERE session_id = 'abc123' 
AND status_code = 200 
ORDER BY timestamp DESC;
```

### ChromaDB - Vector Search

**What it stores:**
- Embeddings of API responses
- Semantic representations of patterns

**Why ChromaDB:**
- Find "similar" responses
- Enable queries like "show responses like this one"
- Cluster related endpoints

**Example use:**
```python
# Find similar responses
results = collection.query(
    query_texts=["user authentication response"],
    n_results=5
)
```

### In-Memory - Hot Data

**What it stores:**
- Current confidence scores
- Active agent states
- Temporary calculations

**Why in-memory:**
- Sub-millisecond access
- Updated thousands of times per session
- Don't need persistence (can recalculate)

**Example:**
```python
# Fast lookup
confidence = memory.get_confidence("hypothesis_123")  # <1ms

# vs. database
confidence = db.query("SELECT confidence FROM hypotheses WHERE id=?", id)  # ~10ms
```

---

## 10. The Frontend Dashboard

### Main Page (localhost:3000)

Shows:
- **Stats cards**: Sessions, observations, iterations, active agents
- **Scientific Loop visualization**: Current phase highlighted
- **URL input**: Start new analysis
- **Active sessions list**: Click to view details

### Session Page (localhost:3000/session/[id])

Shows:
- **Hypothesis cards**: Each discovered endpoint with confidence
- **Schema viewer**: JSON schemas with syntax highlighting
- **Tech stack**: Detected technologies
- **Security panel**: Vulnerabilities found
- **Workflow graph**: Mermaid diagram of API flows

### Real-Time Updates

Uses WebSocket for live updates:
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/session/abc123');
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    updateDashboard(data);
};
```

---

## 11. Code Walkthrough

### Backend Structure

```
backend/
├── agents/
│   ├── base.py          # Base class all agents inherit
│   ├── navigator.py     # UI exploration
│   ├── interceptor.py   # Network capture
│   ├── analyst.py       # Pattern analysis
│   ├── critic.py        # Hypothesis challenging
│   ├── verifier.py      # Edge case testing
│   ├── business_logic.py # Pattern detection
│   └── supervisor.py    # LangGraph orchestration
│
├── api/
│   ├── main.py          # FastAPI app entry point
│   ├── websocket.py     # Real-time updates
│   └── routes/
│       ├── sessions.py  # Session CRUD
│       ├── hypotheses.py # Hypothesis management
│       ├── schemas.py   # Schema endpoints
│       └── security.py  # Security scan results
│
├── browser/
│   ├── manager.py       # Playwright lifecycle
│   ├── stealth.py       # Anti-detection
│   └── accessibility.py # Accessibility tree parsing
│
├── inference/
│   ├── schema_merger.py # Combine schemas
│   ├── security_analyzer.py # Find vulnerabilities
│   ├── report_generator.py  # Create reports
│   └── url_clustering.py    # Group similar URLs
│
├── memory/
│   ├── hypothesis_store.py  # Confidence calculations
│   ├── chroma_store.py      # Vector storage
│   └── fsm_store.py         # State machine
│
└── llm/
    ├── provider.py      # Abstract LLM interface
    ├── openai_client.py # OpenAI adapter
    └── anthropic_client.py # Anthropic adapter
```

### Key Code Patterns

**1. Agent Base Class**
```python
class BaseAgent:
    async def run(self, state: AgentState) -> AgentState:
        """All agents implement this"""
        raise NotImplementedError
```

**2. LangGraph State**
```python
class AgentState(TypedDict):
    session_id: str
    current_phase: str
    observations: List[Observation]
    hypotheses: List[Hypothesis]
    confidence_scores: Dict[str, float]
```

**3. Confidence Update**
```python
def update_confidence(current: float, success: bool) -> float:
    if success:
        # Asymptotic approach to 1.0
        return current + (1.0 - current) * 0.15
    else:
        # Significant drop on failure
        return current * 0.7
```

---

## 12. Common Questions

### Q: Why LangGraph over AutoGen or CrewAI?

**A:** LangGraph gives fine-grained control over routing logic. We can say "if confidence < 0.5, loop back to EXPLORE". AutoGen is more for agent conversations. We needed a state machine with conditional edges.

### Q: Why not just use Burp Suite?

**A:** Burp requires manual proxy configuration and human operation. Our goal was ZERO human intervention. Point at a URL, get a report.

### Q: How accurate is the security scanning?

**A:** Conservative. We only report what we can verify. No false positives are better than many false positives. We map to OWASP categories as guidance, not as CVE-level precision.

### Q: What's the LLM token cost?

**A:** Roughly $0.10-0.50 per session with Gemini 2.0 Flash. Most tokens go to Navigator (deciding what to click) and Analyst (inferring schemas).

### Q: Can it handle authentication?

**A:** Currently it detects auth mechanisms (JWT, sessions, API keys) but doesn't bypass them. Future work: session cookie injection and OAuth automation.

### Q: What about rate limiting?

**A:** Configurable delays between requests. Exponential backoff on 429 errors. Guardrails limit max requests per domain.

### Q: Does it work on SPAs (Single Page Applications)?

**A:** Yes! Playwright fully renders JavaScript. The Navigator detects client-side routing and can trigger navigation events.

---

## Final Notes

This project demonstrates:

1. **Multi-agent orchestration** with LangGraph
2. **Browser automation** with Playwright + CDP
3. **Schema inference** from observed data
4. **Security analysis** aligned with OWASP
5. **Real-time visualization** with WebSocket

The key insight is treating API discovery like a **scientific experiment**: form hypotheses, test them, update beliefs. This is more robust than simple traffic capture because it actively verifies assumptions.

---

*© 2026 Jainam Shah. All Rights Reserved.*
