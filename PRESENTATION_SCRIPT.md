# AI Tinkerers Presentation: Complete Script & Prep Guide
## Black-Box Web Intelligence | 10-15 Minute Technical Deep-Dive

---

# PART 1: YOUR TALK SCRIPT (Word-for-Word)

## OPENING (30 seconds)
> "How many of you have tried to understand an API without documentation? You open DevTools, click around, copy headers into Postman... it takes hours.
>
> I built a multi-agent system that does this automatically. It clicks through a website, captures traffic, infers schemas, and finds security issues—all autonomously.
>
> Let me show you how it works under the hood."

---

## THE PROBLEM (1 minute)
> "The problem I wanted to solve: **Black-box API reverse engineering.**
>
> Given just a URL—no source code, no docs, no server access—can an AI system figure out:
> - What endpoints exist?
> - What's the request/response schema?
> - What authentication is used?
> - Are there security vulnerabilities?
>
> Traditional tools like Burp Suite require manual configuration. I wanted something fully autonomous."

---

## ARCHITECTURE OVERVIEW (2 minutes)

> "Here's the end-to-end architecture..."

**Draw/Show this diagram:**
```
┌─────────────────────────────────────────────────────────────┐
│                    AGENTIC SCIENTIFIC LOOP                  │
│                                                             │
│   ┌─────────┐   ┌─────────┐   ┌─────────┐                  │
│   │ EXPLORE │──▶│ OBSERVE │──▶│  INFER  │                  │
│   │Navigator│   │Intercept│   │ Analyst │                  │
│   └─────────┘   └─────────┘   └─────────┘                  │
│        ▲                            │                       │
│        │                            ▼                       │
│   ┌─────────┐   ┌─────────┐   ┌─────────┐                  │
│   │ UPDATE  │◀──│  PROBE  │◀──│CRITIQUE │                  │
│   │ Memory  │   │Verifier │   │  Critic │                  │
│   └─────────┘   └─────────┘   └─────────┘                  │
│                                                             │
│              Loops until convergence                        │
└─────────────────────────────────────────────────────────────┘
```

> "Six phases, six specialized agents, orchestrated by LangGraph. It's basically the scientific method—form hypotheses, test them, update beliefs."

---

## TECHNICAL DEEP-DIVE: HOW EACH PART WORKS (6 minutes)

### 1. Browser Automation with CDP (1 min)
> "For the EXPLORE phase, I use Playwright with Chrome DevTools Protocol.
>
> The Navigator agent gets the accessibility tree—a semantic representation of the page—and uses an LLM to decide what to click."

**Show code:**
```python
# What the Navigator sees
accessibility_tree = await page.accessibility.snapshot()
# Returns: {"role": "button", "name": "Login", "children": [...]}

# LLM decides action
prompt = f"Given this page structure: {tree}, what should we click to discover APIs?"
action = await llm.invoke(prompt)  # Returns: {"action": "click", "element": "Login button"}
```

> "Key insight: I use the accessibility tree instead of raw HTML because it's what screen readers use—it's semantic, not just markup."

---

### 2. Network Interception (1 min)
> "The OBSERVE phase captures every HTTP request. But here's the gotcha—you can't just use Playwright's `page.on('response')`. You miss the request body.
>
> So I use CDP directly."

**Show code:**
```python
# Enable CDP network domain
cdp = await page.context.new_cdp_session(page)
await cdp.send("Network.enable")

# Capture response WITH body
cdp.on("Network.responseReceived", handle_response)

async def handle_response(event):
    body = await cdp.send("Network.getResponseBody", 
                          {"requestId": event["requestId"]})
    
    # Filter out noise
    if not is_api_call(event["response"]["url"]):
        return  # Skip .js, .css, tracking pixels
    
    observation = Observation(
        url=event["response"]["url"],
        status=event["response"]["status"],
        body=body["body"]
    )
    await store(observation)
```

> "Trade-off: CDP is Chrome-only. I chose browser compatibility over portability because most targets work in Chrome."

---

### 3. Schema Inference (1.5 min)
> "The INFER phase is where it gets interesting. Given multiple responses from the same endpoint pattern, how do we build a schema?"

**Show code:**
```python
# Step 1: Cluster URLs by pattern
"/api/pokemon/1"  →  "/api/pokemon/{id}"
"/api/pokemon/25" →  "/api/pokemon/{id}"

# Step 2: Statistical schema building with genson
from genson import SchemaBuilder
builder = SchemaBuilder()
builder.add_object({"id": 1, "name": "bulbasaur"})
builder.add_object({"id": 25, "name": "pikachu"})
schema = builder.to_schema()
# {"type": "object", "properties": {"id": {"type": "integer"}, "name": {"type": "string"}}}

# Step 3: LLM enrichment for semantics
enriched = await llm.invoke(f"""
Given schema: {schema}
And sample: {sample}
Add: descriptions, format hints (email, uri), examples
""")
```

> "Why `genson`? It handles type unions gracefully. If one response has `"count": 5` and another has `"count": null`, it correctly infers `{"type": ["integer", "null"]}`."

---

### 4. The Critic Agent (1 min)
> "Here's the novel part: I have an agent whose ONLY job is to challenge hypotheses.
>
> It asks: 'Are you SURE this field is always an integer? What about edge cases?'"

**Show code:**
```python
CRITIC_PROMPT = """
You are a skeptical security researcher.

Hypothesis: GET /api/users/{id} returns {schema}
Confidence: 75%
Evidence: 3 observations

Find weaknesses:
1. Could types be different for edge cases?
2. What happens with id=-1 or id=999999?
3. Is authentication really not required?

Propose probes to test.
"""

# Critic output:
{
    "weaknesses": ["Only tested positive IDs", "No auth header tested"],
    "proposed_probes": [
        {"url": "/api/users/-1", "expect": "4xx error"},
        {"url": "/api/users/1", "headers": {}, "expect": "401 if auth required"}
    ]
}
```

> "This is inspired by adversarial training. The Critic makes the system more robust."

---

### 5. Why 3 Storage Types? (30 sec)
> "You might ask: why SQLite AND ChromaDB AND in-memory stores?"

| Storage | Purpose | Why |
|---------|---------|-----|
| SQLite | Sessions, observations | ACID transactions, persistence |
| ChromaDB | Vector embeddings | Semantic search ("find similar responses") |
| In-memory | Confidence scores | Sub-millisecond updates during loop |

> "Each optimized for its access pattern. The hot loop runs thousands of confidence updates per session."

---

### 6. Security Analysis (30 sec)
> "As a bonus, I added security scanning. It checks headers, finds exposed data, analyzes JWTs."

**Show code:**
```python
# Pattern matching for exposed secrets
PATTERNS = {
    'api_keys': r'(?:api[_-]?key)["\s:=]+([a-zA-Z0-9_-]{20,})',
    'aws_keys': r'AKIA[0-9A-Z]{16}',
    'jwts': r'eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+'
}

# Findings mapped to OWASP Top 10
{
    "title": "Missing HSTS Header",
    "severity": "medium",
    "owasp": "A02",  # Cryptographic Failures
    "remediation": "Add Strict-Transport-Security header"
}
```

---

## LIVE DEMO (3 minutes)

> "Let me show you this running..."

1. **Open localhost:3000**
2. **Enter URL:** `https://pokeapi.co`
3. **Click Analyze**
4. **Show:**
   - Real-time phase transitions (Explore → Observe → Infer...)
   - API calls being captured
   - Schemas being inferred
   - Tech stack detection (nginx, Cloudflare)
   - Security findings

> "Notice the confidence scores updating in real-time as we get more evidence."

---

## WRAP-UP (30 seconds)

> "So that's Black-Box Web Intelligence:
> - 6 agents orchestrated by LangGraph
> - CDP for network interception
> - Bayesian confidence updates
> - Automatic security scanning
>
> Code is on my private GitHub—happy to share for those interested.
>
> Questions?"

---

# PART 2: ANTICIPATED Q&A

## Architecture Questions

**Q: Why LangGraph over AutoGen or CrewAI?**
> "LangGraph gives me fine-grained control over routing. I can say 'if confidence < 0.5, loop back to EXPLORE'. AutoGen is more about conversations between agents. I needed a state machine with conditional edges."

**Q: Why not just use Burp Suite or ZAP?**
> "Those require manual proxy configuration and human operation. My goal was ZERO human intervention. Point at URL, get report."

**Q: How do you handle JavaScript SPAs?**
> "Playwright renders JavaScript fully. The Navigator agent also detects client-side routing and can trigger navigation events. Still a challenge for heavily dynamic content."

---

## Technical Questions

**Q: How does the confidence scoring work?**
> "Bayesian-inspired. Start at 0.5. Confirmations push toward 1.0 with diminishing returns: `new = old + (1 - old) * 0.15`. Falsifications multiply by 0.7. Ensures it converges."

**Q: Why 3 different databases?**
> "Each optimized for its access pattern:
> - SQLite: ACID transactions for session integrity
> - ChromaDB: Vector similarity for 'find similar API responses'
> - In-memory: Sub-millisecond confidence updates in hot loop"

**Q: How do you avoid rate limiting?**
> "Configurable delays between requests. Exponential backoff on 429s. Guardrails limit max requests per domain. Still, aggressive exploration can trigger blocks."

**Q: What LLM do you use?**
> "Gemini 2.0 Flash by default, but it's provider-agnostic. I have adapters for OpenAI and Anthropic. The schema inference uses about 2-3 LLM calls per iteration."

---

## Security Questions

**Q: How do you detect JWTs?**
> "Regex for the format `eyJ...`, then base64 decode header and payload. Check for 'alg': 'none' vulnerability. Extract claims to understand the auth model."

**Q: Do you actually exploit vulnerabilities?**
> "No active exploitation. Passive observation only. The probes are GET requests to validate hypotheses, not SQL injection or anything destructive."

**Q: How accurate is the OWASP mapping?**
> "Conservative. I map based on what category the finding relates to. Missing HSTS → A02 (Cryptographic). CORS wildcard → A01 (Access Control). It's guidance, not CVE-level precision."

---

## Implementation Questions

**Q: How long does a full scan take?**
> "Depends on the site. PokeAPI takes about 3-5 minutes for 50 iterations. Larger sites with auth walls take longer because exploration is limited."

**Q: What's the token cost?**
> "Roughly $0.10-0.50 per session with Gemini. Most tokens go to the Navigator deciding what to click and the Analyst inferring schemas."

**Q: Can it handle authentication?**
> "Currently it detects auth mechanisms but doesn't bypass them. Future work: support session cookie injection and OAuth flow automation."

---

# PART 3: TECHNICAL DETAILS YOU SHOULD KNOW

## The Scientific Loop Explained

```
EXPLORE: Navigator uses LLM to decide what UI element to interact with
         Input: Accessibility tree, already-explored elements
         Output: Action (click button X, fill form Y)

OBSERVE: Interceptor captures network traffic via CDP
         Filters: Exclude .js, .css, .png, tracking pixels
         Stores: URL, method, headers, status, body

INFER:   Analyst clusters URLs, builds schemas with genson
         Business Logic agent detects patterns (rate limits, auth)
         Creates Hypothesis objects with confidence scores

CRITIQUE: Critic agent challenges hypotheses
          Proposes edge cases and probes
          Adjusts confidence based on evidence quality

PROBE:   Verifier executes HTTP requests
         Tests: existence, schema validation, boundaries
         Returns: success/failure with evidence

UPDATE:  Memory sync
         Confidence recalculation
         Persist to SQLite, update embeddings
```

## Key Files to Know

| File | Purpose |
|------|---------|
| `backend/agents/supervisor.py` | LangGraph orchestration, phase routing |
| `backend/agents/navigator.py` | LLM-based UI exploration |
| `backend/browser/manager.py` | Playwright lifecycle, CDP setup |
| `backend/inference/schema_merger.py` | JSON schema building |
| `backend/inference/security_analyzer.py` | OWASP detection |
| `backend/memory/hypothesis_store.py` | Confidence calculations |

## Numbers You Should Know

- **~8,600 lines of code** (Python + TypeScript)
- **6 agents** in the scientific loop
- **50+ API endpoints** on backend
- **3 storage systems** (SQLite, ChromaDB, in-memory)
- **5 security check categories** (headers, JWT, exposed data, CVEs, errors)

---

# PART 4: DEMO CHECKLIST

Before your talk:
- [ ] Kill any running processes: `pkill -f uvicorn; pkill -f next`
- [ ] Start fresh: `./start.sh` or manually start both servers
- [ ] Clear old sessions in the database (optional)
- [ ] Have PokeAPI URL ready to paste
- [ ] Open localhost:3000 in browser
- [ ] Have code editor open to key files for walkthrough

During demo:
- [ ] Enter URL, click Analyze
- [ ] Point out the scientific loop animation
- [ ] Show API calls appearing in real-time
- [ ] Click on "Schemas" tab to show inferred schemas
- [ ] Click on "Tech Stack" tab
- [ ] Click on "Security" tab
- [ ] Run AI Analysis to show LLM-powered findings

---

**You've got this! The project is technically impressive and fits perfectly with what AI Tinkerers wants to see. Go geek out! 🚀**
