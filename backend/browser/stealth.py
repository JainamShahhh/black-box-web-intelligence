"""
Stealth configuration for Playwright.
Masks automation signatures to avoid bot detection.
"""

from typing import Any


# JavaScript to inject for stealth mode
STEALTH_JS = """
// Mask webdriver property
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined
});

// Mask automation-related properties
Object.defineProperty(navigator, 'languages', {
    get: () => ['en-US', 'en']
});

Object.defineProperty(navigator, 'plugins', {
    get: () => [
        {
            0: {type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format"},
            description: "Portable Document Format",
            filename: "internal-pdf-viewer",
            length: 1,
            name: "Chrome PDF Plugin"
        }
    ]
});

// Mask Chrome-specific properties
window.chrome = {
    runtime: {}
};

// Mask permissions
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications' ?
        Promise.resolve({ state: Notification.permission }) :
        originalQuery(parameters)
);

// Add missing functions that bots typically don't have
if (!window.Notification) {
    window.Notification = {
        permission: 'default'
    };
}

// Mask iframe contentWindow
const originalContentWindow = Object.getOwnPropertyDescriptor(HTMLIFrameElement.prototype, 'contentWindow');
Object.defineProperty(HTMLIFrameElement.prototype, 'contentWindow', {
    get: function() {
        const win = originalContentWindow.get.call(this);
        if (win) {
            try {
                // Attempt to access cross-origin - will throw if blocked
                win.document;
            } catch (e) {
                return win;
            }
        }
        return win;
    }
});

// Console.debug cleanup (some detectors check this)
const originalDebug = console.debug;
console.debug = function(...args) {
    if (args[0] && typeof args[0] === 'string' && args[0].includes('puppeteer')) {
        return;
    }
    return originalDebug.apply(console, args);
};
"""


def get_stealth_config() -> dict[str, Any]:
    """
    Get browser launch configuration for stealth mode.
    
    Returns:
        Configuration dictionary for browser launch
    """
    return {
        "headless": True,
        "args": [
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--disable-infobars",
            "--disable-setuid-sandbox",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
            "--no-sandbox",
            "--window-size=1920,1080",
            "--start-maximized",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
        ],
        "ignore_default_args": [
            "--enable-automation",
        ],
    }


def get_context_config() -> dict[str, Any]:
    """
    Get browser context configuration for stealth mode.
    
    Returns:
        Configuration dictionary for context creation
    """
    return {
        "viewport": {"width": 1920, "height": 1080},
        "user_agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "locale": "en-US",
        "timezone_id": "America/New_York",
        "geolocation": {"latitude": 40.7128, "longitude": -74.0060},
        "permissions": ["geolocation"],
        "color_scheme": "light",
        "device_scale_factor": 1,
        "is_mobile": False,
        "has_touch": False,
    }


async def apply_stealth(page) -> None:
    """
    Apply stealth modifications to a page.
    
    Args:
        page: Playwright page object
    """
    # Add initialization script that runs before any page script
    await page.add_init_script(STEALTH_JS)


class HumanBehavior:
    """
    Simulates human-like behavior to avoid detection.
    """
    
    @staticmethod
    async def random_delay(page, min_ms: int = 100, max_ms: int = 500) -> None:
        """Add a random delay to simulate human timing."""
        import random
        delay = random.randint(min_ms, max_ms)
        await page.wait_for_timeout(delay)
    
    @staticmethod
    async def human_type(page, selector: str, text: str) -> None:
        """Type text with human-like delays between keystrokes."""
        import random
        
        element = page.locator(selector)
        await element.click()
        
        for char in text:
            await element.type(char)
            # Random delay between 50-150ms per character
            await page.wait_for_timeout(random.randint(50, 150))
    
    @staticmethod
    async def human_click(page, selector: str) -> None:
        """Click with slight randomization of position."""
        import random
        
        element = page.locator(selector)
        box = await element.bounding_box()
        
        if box:
            # Click somewhere within the element, not exactly center
            x = box['x'] + random.uniform(box['width'] * 0.3, box['width'] * 0.7)
            y = box['y'] + random.uniform(box['height'] * 0.3, box['height'] * 0.7)
            await page.mouse.click(x, y)
        else:
            await element.click()
    
    @staticmethod
    async def scroll_like_human(page, direction: str = "down") -> None:
        """Scroll with human-like behavior."""
        import random
        
        # Random scroll amount
        scroll_amount = random.randint(300, 700)
        
        if direction == "up":
            scroll_amount = -scroll_amount
        
        await page.mouse.wheel(0, scroll_amount)
        
        # Small pause after scrolling
        await page.wait_for_timeout(random.randint(200, 500))
