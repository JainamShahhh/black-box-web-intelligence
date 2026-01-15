"""
Playwright Browser Manager.
Manages browser lifecycle, pages, and network interception.
"""

import asyncio
import time
from typing import Any, Callable, Awaitable
from uuid import uuid4

from playwright.async_api import (
    async_playwright,
    Browser,
    BrowserContext,
    Page,
    Route,
    Request,
    Response,
    Playwright,
)

from ..core.config import settings
from ..core.models import NetworkObservation, ActionRecord
from .stealth import get_stealth_config, get_context_config, apply_stealth, HumanBehavior


class BrowserManager:
    """
    Manages Playwright browser instances for web exploration.
    Handles stealth configuration, network interception, and page lifecycle.
    """
    
    def __init__(
        self,
        headless: bool | None = None,
        on_observation: Callable[[NetworkObservation], Awaitable[None]] | None = None
    ):
        """
        Initialize browser manager.
        
        Args:
            headless: Run in headless mode (defaults to config)
            on_observation: Callback for network observations
        """
        self.headless = headless if headless is not None else settings.headless
        self.on_observation = on_observation
        
        self.playwright: Playwright | None = None
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None
        
        # Tracking
        self.current_interaction_id: str = ""
        self.last_action: ActionRecord | None = None
        self.observations: list[NetworkObservation] = []
        
        # Rate limiting
        self.last_request_time: float = 0
        self.min_request_interval: float = 60.0 / settings.max_requests_per_minute
    
    async def start(self) -> Page:
        """
        Start browser and return page.
        
        Returns:
            Playwright Page object
        """
        self.playwright = await async_playwright().start()
        
        # Get stealth configuration
        launch_config = get_stealth_config()
        launch_config["headless"] = self.headless
        
        # Launch browser
        self.browser = await self.playwright.chromium.launch(**launch_config)
        
        # Create context with stealth settings
        context_config = get_context_config()
        self.context = await self.browser.new_context(**context_config)
        
        # Create page
        self.page = await self.context.new_page()
        
        # Apply stealth modifications
        await apply_stealth(self.page)
        
        # Set up network interception
        await self._setup_interception()
        
        return self.page
    
    async def stop(self) -> None:
        """Stop browser and cleanup."""
        if self.page:
            await self.page.close()
            self.page = None
        
        if self.context:
            await self.context.close()
            self.context = None
        
        if self.browser:
            await self.browser.close()
            self.browser = None
        
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
    
    async def _setup_interception(self) -> None:
        """Set up network interception for API traffic capture."""
        if not self.page:
            return
        
        # Intercept all requests
        await self.page.route("**/*", self._intercept_request)
    
    async def _intercept_request(self, route: Route) -> None:
        """
        Intercept and log network requests.
        
        Args:
            route: Playwright route object
        """
        request = route.request
        
        # Check rate limiting
        await self._enforce_rate_limit()
        
        # Capture request details
        timestamp = time.time()
        
        try:
            # Get request data before sending
            request_data = {
                "method": request.method,
                "url": request.url,
                "headers": dict(request.headers),
                "body": request.post_data,
            }
            
            # Continue with request and get response
            response = await route.fetch()
            
            # Check if this is API traffic worth capturing
            if self._is_api_request(request, response):
                # Get response body
                try:
                    body = await response.text()
                except Exception:
                    body = None
                
                # Create observation
                observation = NetworkObservation(
                    id=str(uuid4()),
                    session_id="",  # Will be set by caller
                    interaction_id=self.current_interaction_id,
                    method=request.method,
                    url=request.url,
                    request_headers=request_data["headers"],
                    request_body=request_data["body"],
                    status_code=response.status,
                    response_headers=dict(response.headers),
                    response_body=body,
                    ui_action=self.last_action,
                    page_url=self.page.url if self.page else "",
                )
                
                self.observations.append(observation)
                
                # Notify callback
                if self.on_observation:
                    await self.on_observation(observation)
            
            # Fulfill request
            await route.fulfill(response=response)
            
        except Exception as e:
            # On error, continue the request normally
            try:
                await route.continue_()
            except Exception:
                pass
    
    def _is_api_request(self, request: Request, response: Response) -> bool:
        """
        Determine if a request/response is API traffic worth capturing.
        SMART MODE - capture actual API calls, exclude CDN/library files.
        
        Args:
            request: Request object
            response: Response object
            
        Returns:
            True if this is API traffic
        """
        url = request.url.lower()
        
        # EXCLUDE static assets
        static_extensions = [
            '.css', '.png', '.jpg', '.jpeg', '.gif', '.svg',
            '.woff', '.woff2', '.ttf', '.eot', '.ico', '.webp',
            '.mp4', '.mp3', '.wav', '.pdf', '.zip'
        ]
        for ext in static_extensions:
            if url.endswith(ext) or f"{ext}?" in url:
                return False
        
        # EXCLUDE CDN, trackers, and external services (NOT the target's actual API)
        cdn_patterns = [
            'cloudflareinsights.com', 'cloudflare-static', '/cdn-cgi/',
            'swagger-ui', 'beacon.min.js', 'rocket-loader',
            'google-analytics', 'googletagmanager', 'facebook.com',
            'doubleclick', 'googlesyndication', '/rum?',
            'stripe.com', 'stripe.js', 'tailwindcss.com',
            'unpkg.com', 'jsdelivr.net', 'cdnjs.cloudflare',
            'bootstrapcdn', 'fontawesome', 'jquery',
            'fundingchoicesmessages.google', 'adtrafficquality.google',
            'pagead2.googlesyndication', 'tpc.googlesyndication',
            'google.com/recaptcha', 'gstatic.com', 'googleads',
            'youtube.com', 'twitter.com', 'facebook.net',
            'e.visitors.now', 'carbonads.net', 'srv.carbonads',
            'clarity.ms', 'matomo.php', 'analytics.'
        ]
        for pattern in cdn_patterns:
            if pattern in url:
                return False
        
        # EXCLUDE JavaScript library files (but not .json!)
        if url.endswith('.js') and '.json' not in url:
            # Check if it's from a different domain (CDN)
            if 'static.' in url or 'cdn.' in url or 'assets.' in url:
                return False
        
        # Get content type
        content_type = response.headers.get("content-type", "").lower()
        
        # INCLUDE: JSON responses (this is the real API data!)
        if "application/json" in content_type:
            return True
        
        # INCLUDE: XML responses
        if "xml" in content_type:
            return True
        
        # INCLUDE: API path patterns
        if any(x in url for x in ['/api/', '/v1/', '/v2/', '/v3/', '/graphql', '/rest/']):
            return True
        
        # INCLUDE: .json endpoints
        if '.json' in url:
            return True
        
        # INCLUDE: POST/PUT/DELETE/PATCH (usually API operations)
        if request.method in ('POST', 'PUT', 'DELETE', 'PATCH'):
            # Exclude tracking posts
            if '/rum' not in url and '/beacon' not in url:
                return True
        
        return False
    
    async def _enforce_rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        
        if elapsed < self.min_request_interval:
            await asyncio.sleep(self.min_request_interval - elapsed)
        
        self.last_request_time = time.time()
    
    # =========================================================================
    # Navigation Actions
    # =========================================================================
    
    async def navigate(self, url: str) -> None:
        """
        Navigate to a URL.
        
        Args:
            url: URL to navigate to
        """
        if not self.page:
            raise RuntimeError("Browser not started")
        
        self.current_interaction_id = str(uuid4())
        self.last_action = ActionRecord(
            action_type="navigate",
            target=url,
        )
        
        # Use domcontentloaded for faster navigation, with extended timeout
        try:
            await self.page.goto(url, wait_until="domcontentloaded", timeout=60000)
            # Additional wait for dynamic content
            await self.page.wait_for_timeout(2000)
        except Exception as e:
            print(f"[browser] Navigation warning: {e}")
            # Continue even if timeout - page may still be usable
    
    async def click(self, selector: str, human_like: bool = True) -> None:
        """
        Click an element.
        
        Args:
            selector: Element selector
            human_like: Use human-like clicking
        """
        if not self.page:
            raise RuntimeError("Browser not started")
        
        self.current_interaction_id = str(uuid4())
        self.last_action = ActionRecord(
            action_type="click",
            target=selector,
        )
        
        if human_like:
            await HumanBehavior.random_delay(self.page)
            await HumanBehavior.human_click(self.page, selector)
        else:
            await self.page.click(selector)
        
        # Wait for network to settle
        try:
            await self.page.wait_for_load_state("networkidle", timeout=5000)
        except Exception:
            pass
    
    async def click_element_by_id(self, element_id: int) -> None:
        """
        Click an element by its Set-of-Marks ID.
        
        Args:
            element_id: Set-of-Marks element ID
        """
        await self.click(f"[data-som-id='{element_id}']")
    
    async def type_text(
        self, 
        selector: str, 
        text: str, 
        human_like: bool = True
    ) -> None:
        """
        Type text into an element.
        
        Args:
            selector: Element selector
            text: Text to type
            human_like: Use human-like typing
        """
        if not self.page:
            raise RuntimeError("Browser not started")
        
        self.current_interaction_id = str(uuid4())
        self.last_action = ActionRecord(
            action_type="type",
            target=selector,
            data={"text": text},
        )
        
        if human_like:
            await HumanBehavior.random_delay(self.page)
            await HumanBehavior.human_type(self.page, selector, text)
        else:
            await self.page.fill(selector, text)
    
    async def select_option(self, selector: str, value: str) -> None:
        """
        Select an option from a dropdown.
        
        Args:
            selector: Select element selector
            value: Option value to select
        """
        if not self.page:
            raise RuntimeError("Browser not started")
        
        self.current_interaction_id = str(uuid4())
        self.last_action = ActionRecord(
            action_type="select",
            target=selector,
            data={"value": value},
        )
        
        await self.page.select_option(selector, value)
    
    async def scroll(self, direction: str = "down") -> None:
        """
        Scroll the page.
        
        Args:
            direction: "up" or "down"
        """
        if not self.page:
            raise RuntimeError("Browser not started")
        
        self.current_interaction_id = str(uuid4())
        self.last_action = ActionRecord(
            action_type="scroll",
            target=direction,
        )
        
        await HumanBehavior.scroll_like_human(self.page, direction)
    
    async def go_back(self) -> None:
        """Go back in browser history."""
        if not self.page:
            raise RuntimeError("Browser not started")
        
        self.current_interaction_id = str(uuid4())
        self.last_action = ActionRecord(
            action_type="back",
            target="",
        )
        
        await self.page.go_back(wait_until="networkidle", timeout=settings.browser_timeout)
    
    async def hover(self, selector: str) -> None:
        """
        Hover over an element.
        
        Args:
            selector: Element selector
        """
        if not self.page:
            raise RuntimeError("Browser not started")
        
        self.current_interaction_id = str(uuid4())
        self.last_action = ActionRecord(
            action_type="hover",
            target=selector,
        )
        
        await self.page.hover(selector)
    
    # =========================================================================
    # State Capture
    # =========================================================================
    
    async def get_current_url(self) -> str:
        """Get current page URL."""
        if not self.page:
            return ""
        return self.page.url
    
    async def get_page_title(self) -> str:
        """Get current page title."""
        if not self.page:
            return ""
        return await self.page.title()
    
    async def take_screenshot(self) -> bytes:
        """
        Take a screenshot of the current page.
        
        Returns:
            Screenshot as bytes
        """
        if not self.page:
            raise RuntimeError("Browser not started")
        return await self.page.screenshot(full_page=False)
    
    async def take_screenshot_base64(self) -> str:
        """
        Take a screenshot and return as base64.
        
        Returns:
            Screenshot as base64 string
        """
        import base64
        screenshot = await self.take_screenshot()
        return base64.b64encode(screenshot).decode()
    
    def get_pending_observations(self) -> list[NetworkObservation]:
        """
        Get and clear pending observations.
        
        Returns:
            List of observations since last call
        """
        observations = self.observations.copy()
        self.observations = []
        return observations
