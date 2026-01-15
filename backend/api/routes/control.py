"""
Control API - Start, stop, and control exploration.
"""

from typing import Any
import asyncio
import json
import time
import hashlib
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel

from ...core.state import create_initial_state
from ...core.config import settings
from ...core.models import HypothesisType, HypothesisStatus
from ..websocket import (
    emit_phase_change, emit_observation, emit_hypothesis_created,
    emit_confidence_change, emit_critic_review, emit_probe_result, emit_error
)


router = APIRouter()

# Track running explorations
running_tasks: dict[str, asyncio.Task] = {}

# Track current phase per session (key: session_id, value: phase name)
session_phases: dict[str, str] = {}


def compute_page_hash(url: str, elements: list, title: str = "") -> str:
    """Compute a hash of the current page state for FSM tracking."""
    # Create a normalized representation
    element_sigs = []
    for el in elements[:50]:  # Limit for performance
        sig = f"{el.get('tag', '')}-{el.get('id', '')}-{el.get('text', '')[:20]}"
        element_sigs.append(sig)
    
    state_str = f"{url}|{title}|{'|'.join(sorted(element_sigs))}"
    return hashlib.md5(state_str.encode()).hexdigest()[:16]


def is_duplicate_hypothesis(new_hypo: dict, existing: list) -> bool:
    """Check if a hypothesis already exists (semantic deduplication)."""
    new_pattern = new_hypo.get("endpoint_pattern", "")
    new_method = new_hypo.get("method", "")
    
    for existing_hypo in existing:
        # Check for exact pattern match
        if (existing_hypo.endpoint_pattern == new_pattern and 
            existing_hypo.method == new_method):
            return True
        
        # Check for similar description (first 50 chars)
        new_desc = new_hypo.get("description", "")[:50].lower()
        existing_desc = (existing_hypo.description or "")[:50].lower()
        if new_desc and existing_desc and new_desc == existing_desc:
            return True
    
    return False


class StartExplorationRequest(BaseModel):
    """Request to start exploration."""
    session_id: str


class ExplorationStatus(BaseModel):
    """Exploration status response."""
    session_id: str
    running: bool
    loop_iteration: int
    current_phase: str
    current_url: str


@router.post("/start")
async def start_exploration(
    request: StartExplorationRequest,
    req: Request,
    background_tasks: BackgroundTasks
) -> dict[str, Any]:
    """Start exploration for a session."""
    session_id = request.session_id
    memory_manager = req.app.state.memory_manager
    
    if not memory_manager:
        raise HTTPException(status_code=500, detail="Memory manager not initialized")
    
    session = await memory_manager.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session_id in running_tasks and not running_tasks[session_id].done():
        raise HTTPException(status_code=400, detail="Exploration already running")
    
    # Start exploration in background
    async def run_exploration():
        try:
            await _run_exploration_loop(session_id, memory_manager)
        except Exception as e:
            print(f"Exploration error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if session_id in running_tasks:
                del running_tasks[session_id]
            if session_id in session_phases:
                del session_phases[session_id]
    
    task = asyncio.create_task(run_exploration())
    running_tasks[session_id] = task
    
    return {
        "status": "started",
        "session_id": session_id,
        "message": "Exploration started in background"
    }


@router.post("/stop")
async def stop_exploration(
    request: StartExplorationRequest,
    req: Request
) -> dict[str, Any]:
    """Stop exploration for a session."""
    session_id = request.session_id
    
    if session_id not in running_tasks:
        raise HTTPException(status_code=400, detail="Exploration not running")
    
    task = running_tasks[session_id]
    task.cancel()
    
    return {
        "status": "stopping",
        "session_id": session_id,
        "message": "Exploration stop requested"
    }


@router.get("/status/{session_id}", response_model=ExplorationStatus)
async def get_exploration_status(
    session_id: str,
    req: Request
) -> ExplorationStatus:
    """Get exploration status for a session."""
    memory_manager = req.app.state.memory_manager
    
    if not memory_manager:
        raise HTTPException(status_code=500, detail="Memory manager not initialized")
    
    session = await memory_manager.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    running = session_id in running_tasks and not running_tasks[session_id].done()
    
    # Get the actual current phase from tracked state
    current_phase = session_phases.get(session_id, "idle")
    if not running:
        current_phase = "idle"
    
    return ExplorationStatus(
        session_id=session_id,
        running=running,
        loop_iteration=session.loop_iteration,
        current_phase=current_phase,
        current_url=session.current_url
    )


@router.get("/guardrails")
async def get_guardrails(req: Request) -> dict[str, Any]:
    """Get current guardrail configuration."""
    from ...core.guardrails import Guardrails
    
    guardrails = Guardrails()
    return guardrails.get_scope_declaration()


# ============================================================================
# EXPLORATION LOOP - The Heart of the System
# ============================================================================

async def _run_exploration_loop(session_id: str, memory_manager) -> None:
    """
    Run the full scientific exploration loop.
    
    Phases: Explore → Observe → Infer → Critique → Probe → Update → Repeat
    """
    from ...browser.manager import BrowserManager
    from ...browser.accessibility import AccessibilityExtractor
    from ...browser.set_of_marks import SetOfMarksOverlay
    from ...llm.provider import get_llm_provider
    from ...inference.schema_merger import SchemaMerger
    from ...inference.url_clustering import URLClusterer
    from ...inference.tech_intel import get_tech_intel, clear_tech_intel
    from ...memory.fsm_store import FSMStore
    
    session = await memory_manager.get_session(session_id)
    if not session:
        return
    
    # Get LLM provider
    llm = get_llm_provider()
    
    # Initialize browser
    browser = BrowserManager(headless=session.config.headless)
    
    # Use the global FSM store from app state (passed via memory_manager)
    fsm_store = memory_manager.fsm_store if hasattr(memory_manager, 'fsm_store') else None
    
    # If no global store, create session-specific one
    if not fsm_store:
        fsm_store = FSMStore(f"data/fsm_{session_id}.db")
        await fsm_store.initialize()
    
    try:
        await fsm_store.create_session(session_id, session.target_url, {})
    except:
        pass  # Session may already exist
    
    # Phase tracking
    phases = ["explore", "observe", "infer", "critique", "probe", "update"]
    current_phase_idx = 0
    previous_phase = None
    
    # FSM State tracking
    current_state_hash = None
    states_visited = set()
    
    # Data accumulators
    all_observations = []
    pending_hypotheses = []
    url_clusterer = URLClusterer()
    schema_merger = SchemaMerger()
    
    # Technology intelligence analyzer
    tech_intel = get_tech_intel(session_id)
    
    try:
        page = await browser.start()
        
        # Navigate to target
        await browser.navigate(session.target_url)
        await asyncio.sleep(2)  # Wait for initial load
        
        # Initialize page analysis tools
        accessibility = AccessibilityExtractor(page)
        som = SetOfMarksOverlay(page)
        
        # Inject SoM overlay
        elements = await som.inject()
        
        # Capture initial state for FSM
        initial_title = await page.title()
        current_state_hash = compute_page_hash(page.url, elements, initial_title)
        states_visited.add(current_state_hash)
        await fsm_store.add_state(
            current_state_hash, session_id, page.url, initial_title
        )
        # Sync states count to session
        await memory_manager.update_session(session_id, {"states_visited": len(states_visited)})
        print(f"[fsm] Initial state: {current_state_hash}")
        
        # Get initial observations from page load
        initial_obs = browser.get_pending_observations()
        for obs in initial_obs:
            obs.session_id = session_id
            await memory_manager.add_observation(session_id, obs)
            all_observations.append(obs)
            # Analyze for technology fingerprints
            tech_intel.analyze_observation({
                'url': obs.url,
                'method': obs.method,
                'status_code': obs.status_code,
                'request_headers': obs.request_headers,
                'response_headers': obs.response_headers,
                'response_body': obs.response_body
            })
            # Emit WebSocket event
            try:
                await emit_observation(session_id, {"method": obs.method, "url": obs.url, "status_code": obs.status_code})
            except:
                pass
        
        print(f"[control] Initial page load captured {len(initial_obs)} API calls")
        
        # Run exploration loop
        max_iterations = min(session.config.max_iterations, 100)  # Cap at 100 for safety
        explored_elements = set()
        consecutive_no_new = 0
        
        for iteration in range(max_iterations):
            # Check cancellation
            if asyncio.current_task().cancelled():
                print(f"[control] Exploration cancelled at iteration {iteration}")
                break
            
            # Update session
            await memory_manager.increment_loop(session_id)
            session.loop_iteration = iteration
            
            # Get current phase
            phase = phases[current_phase_idx % len(phases)]
            print(f"[control] Iteration {iteration} - Phase: {phase}")
            
            # Update the global phase tracker so status endpoint can return it
            session_phases[session_id] = phase
            
            # Emit phase change via WebSocket
            if phase != previous_phase:
                try:
                    await emit_phase_change(session_id, previous_phase or "init", phase, iteration)
                except:
                    pass
                previous_phase = phase
            
            try:
                if phase == "explore":
                    # ========================================================
                    # EXPLORE PHASE: Aggressive UI exploration + Form filling
                    # ========================================================
                    
                    # Refresh the SoM overlay with timeout
                    try:
                        elements = await asyncio.wait_for(som.refresh(), timeout=10.0)
                    except asyncio.TimeoutError:
                        print(f"[navigator] SoM refresh timed out, using fallback")
                        elements = []
                    
                    # ---- FORM DETECTION AND FILLING ----
                    try:
                        forms = await accessibility.get_forms()
                        if forms:
                            for form in forms[:2]:  # Process up to 2 forms
                                fields = form.get('fields', [])
                                if not fields:
                                    continue
                                
                                print(f"[navigator] Found form with {len(fields)} fields")
                                
                                for field in fields:
                                    field_type = field.get('type', 'text').lower()
                                    field_name = field.get('name', field.get('id', '')).lower()
                                    selector = f"input[name='{field.get('name')}']" if field.get('name') else f"#{field.get('id')}"
                                    
                                    # Generate synthetic data based on field type/name
                                    synthetic_value = None
                                    if 'email' in field_name or field_type == 'email':
                                        synthetic_value = f"test{iteration}@example.com"
                                    elif 'password' in field_name or field_type == 'password':
                                        synthetic_value = "TestPassword123!"
                                    elif 'name' in field_name or 'user' in field_name:
                                        synthetic_value = "Test User"
                                    elif 'phone' in field_name or field_type == 'tel':
                                        synthetic_value = "+1555123456"
                                    elif 'search' in field_name or field_type == 'search':
                                        synthetic_value = "test search query"
                                    elif field_type in ('text', 'textarea'):
                                        synthetic_value = f"test_value_{iteration}"
                                    elif field_type == 'number':
                                        synthetic_value = "42"
                                    
                                    if synthetic_value and selector:
                                        try:
                                            await page.fill(selector, synthetic_value)
                                            print(f"[navigator] Filled {field_name} with synthetic data")
                                            await asyncio.sleep(0.3)
                                        except:
                                            pass
                                
                                # Try to submit the form
                                submit_btn = await page.query_selector('button[type="submit"], input[type="submit"], button:has-text("Submit"), button:has-text("Send")')
                                if submit_btn:
                                    try:
                                        await submit_btn.click()
                                        print(f"[navigator] Submitted form")
                                        await asyncio.sleep(2)
                                        
                                        # Capture any resulting API calls
                                        new_obs = browser.get_pending_observations()
                                        for obs in new_obs:
                                            obs.session_id = session_id
                                            await memory_manager.add_observation(session_id, obs)
                                            all_observations.append(obs)
                                            print(f"[interceptor] Form submission captured: {obs.method} {obs.url[:50]}")
                                    except:
                                        pass
                    except Exception as form_err:
                        pass  # Form handling is optional
                    
                    # ---- ELEMENT CLICKING ----
                    # If SoM returned no elements, try direct DOM query
                    if not elements:
                        try:
                            elements = await page.evaluate("""
                                () => {
                                    const results = [];
                                    document.querySelectorAll('a, button, [onclick]').forEach((el, idx) => {
                                        results.push({
                                            id: idx,
                                            tag: el.tagName.toLowerCase(),
                                            text: (el.textContent || '').trim().substring(0, 50),
                                            href: el.href || ''
                                        });
                                    });
                                    return results;
                                }
                            """)
                            print(f"[navigator] Fallback found {len(elements)} elements")
                        except:
                            elements = []
                    
                    # Filter to links and buttons primarily
                    clickable = [e for e in elements if e.get('tag') in ('a', 'button', 'input') or e.get('role') in ('button', 'link', 'menuitem', 'tab')]
                    
                    # If no buttons/links, try ANY element
                    if not clickable:
                        clickable = elements
                    
                    new_clickable = [e for e in clickable if e.get("id") not in explored_elements]
                    
                    print(f"[navigator] Found {len(elements)} elements, {len(new_clickable)} unexplored")
                    
                    if new_clickable and len(new_clickable) > 0:
                        # AGGRESSIVE MODE: Click multiple elements per iteration
                        # Prioritize links and API-triggering elements
                        # Pick up to 5 elements to click
                        elements_to_click = new_clickable[:5]
                        
                        for elem in elements_to_click:
                            element_id = elem.get('id')
                            if element_id is None:
                                continue
                            
                            elem_text = elem.get('text', elem.get('ariaLabel', elem.get('name', '')))[:30]
                            elem_tag = elem.get('tag', 'unknown')
                            elem_href = elem.get('href', '')
                            
                            # Skip external links
                            if elem_href and ('://' in elem_href) and session.target_url not in elem_href:
                                explored_elements.add(element_id)
                                continue
                            
                            # Skip logout/signout
                            if any(x in elem_text.lower() for x in ['logout', 'sign out', 'signout', 'log out']):
                                explored_elements.add(element_id)
                                continue
                            
                            print(f"[navigator] Clicking [{element_id}] {elem_tag}: {elem_text}")
                            
                            try:
                                previous_state = current_state_hash
                                
                                # Click the element - try SoM first, then direct selector
                                clicked = False
                                try:
                                    await browser.click_element_by_id(element_id)
                                    clicked = True
                                except:
                                    # Fallback to direct click
                                    try:
                                        if elem_href:
                                            await page.click(f'a[href="{elem_href}"]')
                                            clicked = True
                                        elif elem_tag:
                                            els = await page.query_selector_all(elem_tag)
                                            if element_id < len(els):
                                                await els[element_id].click()
                                                clicked = True
                                    except:
                                        pass
                                
                                explored_elements.add(element_id)
                                
                                # Wait for network activity
                                await asyncio.sleep(1.0)
                                
                                # Track FSM state transition with timeout
                                try:
                                    new_elements = await asyncio.wait_for(som.refresh(), timeout=5.0)
                                    new_title = await asyncio.wait_for(page.title(), timeout=2.0)
                                    new_state_hash = compute_page_hash(page.url, new_elements, new_title)
                                    
                                    if new_state_hash != current_state_hash:
                                        is_new = await fsm_store.add_state(
                                            new_state_hash, session_id, page.url, new_title
                                        )
                                        if is_new:
                                            states_visited.add(new_state_hash)
                                            # Sync states count to session
                                            await memory_manager.update_session(session_id, {"states_visited": len(states_visited)})
                                            print(f"[fsm] NEW STATE: {new_state_hash} ({page.url})")
                                        
                                        await fsm_store.add_transition(
                                            session_id=session_id,
                                            from_state_hash=previous_state,
                                            to_state_hash=new_state_hash,
                                            action_type="click",
                                            action_target=str(element_id),
                                            triggered_apis=[]
                                        )
                                        current_state_hash = new_state_hash
                                except:
                                    pass
                                
                                # Capture observations
                                new_obs = browser.get_pending_observations()
                                for obs in new_obs:
                                    obs.session_id = session_id
                                    await memory_manager.add_observation(session_id, obs)
                                    all_observations.append(obs)
                                    print(f"[interceptor] Captured: {obs.method} {obs.url[:50]}")
                                
                                if new_obs:
                                    consecutive_no_new = 0
                                
                            except Exception as click_err:
                                explored_elements.add(element_id)
                                # Don't print every error - some elements can't be clicked
                        
                        # Small delay between clicks
                        await asyncio.sleep(0.5)
                    else:
                        consecutive_no_new += 1
                        
                        # Try scrolling to find more elements
                        try:
                            await browser.scroll("down")
                            await asyncio.sleep(0.5)
                            
                            # Also try clicking any links we can find directly
                            links = await page.query_selector_all('a[href]')
                            for i, link in enumerate(links[:5]):
                                href = await link.get_attribute('href')
                                if href and session.target_url.split('/')[2] in href:
                                    try:
                                        await link.click()
                                        await asyncio.sleep(1)
                                        new_obs = browser.get_pending_observations()
                                        for obs in new_obs:
                                            obs.session_id = session_id
                                            await memory_manager.add_observation(session_id, obs)
                                            all_observations.append(obs)
                                        break
                                    except:
                                        pass
                        except:
                            pass
                    
                    # Update states visited count
                    try:
                        await memory_manager.update_session(session_id, {"states_visited": len(states_visited)})
                    except:
                        pass
                    
                    if consecutive_no_new > 15:
                        print(f"[control] Exploration exhausted after {len(explored_elements)} elements")
                        current_phase_idx = 1
                        continue
                
                elif phase == "observe":
                    # ========================================================
                    # OBSERVE PHASE: Process captured network traffic
                    # ========================================================
                    
                    # Get recent observations
                    recent_obs = await memory_manager.get_observations(session_id, limit=100)
                    
                    # Be lenient - accept ANY API-like traffic
                    api_calls = []
                    for obs in recent_obs:
                        url = obs.url.lower()
                        content_type = (obs.response_headers or {}).get("content-type", "").lower()
                        
                        # Check if it's likely an API call
                        is_api = False
                        
                        # JSON responses
                        if "json" in content_type:
                            is_api = True
                        # JavaScript that might be JSONP
                        elif "javascript" in content_type and obs.response_body:
                            is_api = True
                        # Looks like JSON
                        elif obs.response_body and obs.response_body.strip().startswith(("{", "[")):
                            is_api = True
                        # Has /api/ in URL
                        elif "/api/" in url or "/v1/" in url or "/v2/" in url:
                            is_api = True
                        # Is a data endpoint
                        elif any(x in url for x in ['.json', '/graphql', '/rest/', '/data/']):
                            is_api = True
                        
                        if is_api and obs.status_code != 204:  # Skip 204 No Content
                            api_calls.append(obs)
                    
                    print(f"[interceptor] Found {len(api_calls)} API calls")
                    
                    # Store for next phase
                    pending_hypotheses = []
                    for obs in api_calls:
                        pending_hypotheses.append({
                            "observation": obs,
                            "url": obs.url,
                            "method": obs.method,
                            "status": obs.status_code,
                        })
                
                elif phase == "infer":
                    # ========================================================
                    # INFER PHASE: Generate hypotheses from observations
                    # ========================================================
                    
                    if not pending_hypotheses:
                        print(f"[analyst] No observations to analyze")
                        current_phase_idx += 1
                        continue
                    
                    print(f"[analyst] Analyzing {len(pending_hypotheses)} observations")
                    
                    # Cluster URLs
                    urls = [h["url"] for h in pending_hypotheses]
                    clusters = url_clusterer.cluster(urls)
                    
                    # For each cluster, create a hypothesis
                    hypo_store = await memory_manager.get_hypothesis_store(session_id)
                    
                    for pattern, urls_in_cluster in clusters.items():
                        # Get a sample observation for this cluster
                        sample_obs = None
                        for h in pending_hypotheses:
                            if h["url"] in urls_in_cluster:
                                sample_obs = h["observation"]
                                break
                        
                        if not sample_obs:
                            continue
                        
                        # Try to parse the response as JSON
                        response_schema = None
                        if sample_obs.response_body:
                            try:
                                response_data = json.loads(sample_obs.response_body)
                                inferred = schema_merger.infer_schema(response_data)
                                # Ensure the schema is JSON serializable
                                response_schema = json.loads(json.dumps(inferred, default=str))
                            except Exception as schema_err:
                                print(f"[analyst] Schema inference error: {schema_err}")
                                response_schema = None
                        
                        # Create hypothesis - keep it simple
                        hypo_data = {
                            "type": HypothesisType.ENDPOINT_SCHEMA,
                            "description": f"API endpoint discovered: {sample_obs.method} {pattern}",
                            "endpoint_pattern": pattern,
                            "method": sample_obs.method,
                            "response_schema": response_schema or {},  # Must be dict, not None
                            "confidence": 0.6,
                            "status": HypothesisStatus.ACTIVE,
                            "created_by": "analyst",
                        }
                        
                        # Use LLM to enrich the hypothesis
                        try:
                            if response_schema:
                                enrich_prompt = f"""Analyze this API endpoint:
URL Pattern: {pattern}
Method: {sample_obs.method}
Status: {sample_obs.status_code}
Response Schema: {json.dumps(response_schema, indent=2)[:1000]}

Provide a brief description of what this API endpoint likely does.
Respond with ONLY the description, 1-2 sentences."""

                                enrich_response = await llm.invoke(
                                    messages=enrich_prompt,
                                    system_prompt="You are an API analyst. Provide concise descriptions.",
                                    temperature=0.3
                                )
                                
                                hypo_data["description"] = enrich_response.content.strip()
                                hypo_data["confidence"] = 0.75  # Higher confidence with LLM enrichment
                        except Exception as enrich_err:
                            print(f"[analyst] LLM enrichment failed: {enrich_err}")
                        
                        # Store hypothesis (with deduplication)
                        if hypo_store:
                            try:
                                # Check for duplicates
                                existing_hypotheses = await hypo_store.list()
                                if is_duplicate_hypothesis(hypo_data, existing_hypotheses):
                                    print(f"[analyst] Skipping duplicate hypothesis for {pattern}")
                                else:
                                    hypothesis = await hypo_store.create(**hypo_data)
                                    print(f"[analyst] Created hypothesis for {pattern}")
                                    # Emit WebSocket event
                                    try:
                                        await emit_hypothesis_created(session_id, {
                                            "id": hypothesis.id if hypothesis else None,
                                            "type": str(hypo_data["type"].value),
                                            "description": hypo_data["description"][:100],
                                            "confidence": hypo_data["confidence"]
                                        })
                                    except:
                                        pass
                            except Exception as store_err:
                                print(f"[analyst] Failed to store hypothesis: {store_err}")
                    
                    pending_hypotheses = []  # Clear after processing
                
                elif phase == "critique":
                    # ========================================================
                    # CRITIQUE PHASE: Challenge ALL hypotheses aggressively
                    # ========================================================
                    
                    hypo_store = await memory_manager.get_hypothesis_store(session_id)
                    if not hypo_store:
                        current_phase_idx += 1
                        continue
                    
                    hypotheses = await hypo_store.list()
                    
                    # Review ALL active hypotheses, not just low confidence
                    to_review = [h for h in hypotheses if h.status == HypothesisStatus.ACTIVE]
                    
                    print(f"[critic] Reviewing {len(to_review)} hypotheses")
                    
                    for hypo in to_review[:3]:  # Review up to 3 per iteration
                        # Use LLM to critique
                        try:
                            critique_prompt = f"""Review this API hypothesis:
Endpoint: {hypo.endpoint_pattern}
Method: {hypo.method}
Description: {hypo.description}
Current Confidence: {hypo.confidence}

What could be wrong with this hypothesis? List potential issues or alternative explanations.
Be brief - 2-3 bullet points max."""

                            critique_response = await llm.invoke(
                                messages=critique_prompt,
                                system_prompt="You are a skeptical API analyst. Find potential issues.",
                                temperature=0.5
                            )
                            
                            # Update hypothesis with critique
                            old_confidence = hypo.confidence
                            new_confidence = max(0.3, hypo.confidence - 0.1)  # Reduce confidence
                            await hypo_store.update(
                                hypo.id,
                                confidence=new_confidence,
                                competing_explanations=[critique_response.content.strip()],
                                status=HypothesisStatus.CHALLENGED
                            )
                            print(f"[critic] Challenged hypothesis {hypo.id}")
                            
                            # Emit WebSocket events
                            try:
                                await emit_confidence_change(
                                    session_id, hypo.id, old_confidence, new_confidence,
                                    "Critic identified potential issues"
                                )
                                await emit_critic_review(session_id, {
                                    "hypothesis_id": hypo.id,
                                    "verdict": "challenged",
                                    "original_confidence": old_confidence,
                                    "recommended_confidence": new_confidence,
                                    "alternative_explanations": [critique_response.content.strip()]
                                })
                            except:
                                pass
                            
                        except Exception as critique_err:
                            print(f"[critic] Critique failed: {critique_err}")
                
                elif phase == "probe":
                    # ========================================================
                    # PROBE PHASE: Verify ALL hypotheses with real requests
                    # ========================================================
                    
                    hypo_store = await memory_manager.get_hypothesis_store(session_id)
                    if not hypo_store:
                        current_phase_idx += 1
                        continue
                    
                    # Verify ANY hypothesis that has an endpoint pattern
                    hypotheses = await hypo_store.list()
                    to_verify = [h for h in hypotheses if h.status in (HypothesisStatus.CHALLENGED, HypothesisStatus.ACTIVE) and h.confidence < 0.9]
                    
                    print(f"[verifier] Probing {len(to_verify)} hypotheses")
                    
                    for hypo in to_verify[:5]:  # Probe up to 5 per iteration
                        if not hypo.endpoint_pattern:
                            continue
                        
                        # Try to make a request to verify
                        try:
                            from urllib.parse import urljoin
                            test_url = urljoin(session.target_url, hypo.endpoint_pattern)
                            
                            # Use browser to make request (inherits cookies/auth)
                            result = await page.evaluate(f"""
                                async () => {{
                                    try {{
                                        const resp = await fetch('{test_url}');
                                        return {{
                                            status: resp.status,
                                            ok: resp.ok,
                                            contentType: resp.headers.get('content-type')
                                        }};
                                    }} catch (e) {{
                                        return {{ error: e.message }};
                                    }}
                                }}
                            """)
                            
                            old_confidence = hypo.confidence
                            
                            if result.get("ok"):
                                # Hypothesis confirmed!
                                new_confidence = min(0.95, hypo.confidence + 0.2)
                                await hypo_store.update(
                                    hypo.id,
                                    confidence=new_confidence,
                                    status=HypothesisStatus.CONFIRMED,
                                    supporting_evidence=hypo.supporting_evidence + [
                                        f"Verified: probe returned status {result.get('status')}"
                                    ]
                                )
                                print(f"[verifier] CONFIRMED hypothesis {hypo.id}")
                                
                                # Emit WebSocket events
                                try:
                                    await emit_confidence_change(
                                        session_id, hypo.id, old_confidence, new_confidence,
                                        "Probe verified endpoint"
                                    )
                                    await emit_probe_result(session_id, {
                                        "hypothesis_id": hypo.id,
                                        "probe_type": "http_get",
                                        "outcome": "confirmed",
                                        "confidence_delta": new_confidence - old_confidence
                                    })
                                except:
                                    pass
                            else:
                                # Lower confidence
                                new_confidence = max(0.1, hypo.confidence - 0.15)
                                await hypo_store.update(
                                    hypo.id,
                                    confidence=new_confidence,
                                    status=HypothesisStatus.NEEDS_REVISION
                                )
                                print(f"[verifier] Probe failed for {hypo.id}")
                                
                                try:
                                    await emit_confidence_change(
                                        session_id, hypo.id, old_confidence, new_confidence,
                                        "Probe failed to verify"
                                    )
                                    await emit_probe_result(session_id, {
                                        "hypothesis_id": hypo.id,
                                        "probe_type": "http_get",
                                        "outcome": "failed",
                                        "confidence_delta": new_confidence - old_confidence
                                    })
                                except:
                                    pass
                                
                        except Exception as probe_err:
                            print(f"[verifier] Probe error: {probe_err}")
                
                elif phase == "update":
                    # ========================================================
                    # UPDATE PHASE: Consolidate and prepare for next cycle
                    # ========================================================
                    
                    # Get current stats
                    obs_count = len(await memory_manager.get_observations(session_id, 1000))
                    hypo_store = await memory_manager.get_hypothesis_store(session_id)
                    hypo_count = len(await hypo_store.list()) if hypo_store else 0
                    states_count = len(states_visited)
                    
                    print(f"[update] Cycle complete - {obs_count} observations, {hypo_count} hypotheses, {states_count} states")
                    
                    # Update session with states_visited count
                    try:
                        session.states_visited = states_count
                    except:
                        pass
                    
                    # Check termination conditions
                    if consecutive_no_new > 15:
                        print(f"[control] Exploration exhausted - stopping")
                        break
                    
                    if hypo_count > 0:
                        hypotheses = await hypo_store.list()
                        confirmed = [h for h in hypotheses if h.status == HypothesisStatus.CONFIRMED]
                        avg_confidence = sum(h.confidence for h in hypotheses) / len(hypotheses)
                        
                        if len(confirmed) > 5 and avg_confidence > 0.8:
                            print(f"[control] High confidence achieved - stopping")
                            break
                
                # Move to next phase
                current_phase_idx += 1
                
                # Small delay between phases
                await asyncio.sleep(0.3)
                
            except Exception as phase_err:
                print(f"[control] Error in {phase} phase: {phase_err}")
                import traceback
                traceback.print_exc()
                current_phase_idx += 1  # Continue to next phase
        
        print(f"[control] Exploration loop finished after {iteration + 1} iterations")
        
    except Exception as e:
        print(f"[control] Fatal error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Cleanup
        try:
            await fsm_store.update_session_status(session_id, "completed")
            await fsm_store.close()
        except:
            pass
        await browser.stop()
