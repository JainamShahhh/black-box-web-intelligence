"""
Set-of-Marks (SoM) Overlay.
Injects visual markers and data attributes for element identification.
"""

from typing import Any


# JavaScript to inject Set-of-Marks overlay
SOM_INJECTION_SCRIPT = """
(function() {
    // Remove existing SoM markers
    const existingMarkers = document.querySelectorAll('.som-marker');
    existingMarkers.forEach(m => m.remove());
    
    // Remove existing data attributes
    const existingElements = document.querySelectorAll('[data-som-id]');
    existingElements.forEach(el => el.removeAttribute('data-som-id'));
    
    // Interactive element selectors
    const interactiveSelectors = [
        'button',
        'a[href]',
        'input',
        'select',
        'textarea',
        '[role="button"]',
        '[role="link"]',
        '[role="checkbox"]',
        '[role="radio"]',
        '[role="menuitem"]',
        '[role="tab"]',
        '[role="option"]',
        '[role="switch"]',
        '[onclick]',
        '[tabindex]:not([tabindex="-1"])'
    ];
    
    // Find all interactive elements
    const selector = interactiveSelectors.join(', ');
    const elements = document.querySelectorAll(selector);
    
    // Create style for markers
    if (!document.getElementById('som-styles')) {
        const style = document.createElement('style');
        style.id = 'som-styles';
        style.textContent = `
            .som-marker {
                position: absolute;
                background: rgba(255, 0, 0, 0.8);
                color: white;
                font-size: 10px;
                font-weight: bold;
                padding: 1px 4px;
                border-radius: 3px;
                z-index: 10000;
                pointer-events: none;
                font-family: monospace;
                box-shadow: 0 1px 3px rgba(0,0,0,0.3);
            }
            .som-marker.som-input {
                background: rgba(0, 100, 255, 0.8);
            }
            .som-marker.som-link {
                background: rgba(0, 150, 0, 0.8);
            }
        `;
        document.head.appendChild(style);
    }
    
    // Create container for markers
    let container = document.getElementById('som-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'som-container';
        document.body.appendChild(container);
    }
    
    const results = [];
    let idCounter = 0;
    
    elements.forEach(el => {
        // Skip hidden elements
        const style = window.getComputedStyle(el);
        if (style.display === 'none' || style.visibility === 'hidden') {
            return;
        }
        
        // Skip elements outside viewport
        const rect = el.getBoundingClientRect();
        if (rect.width === 0 || rect.height === 0) {
            return;
        }
        if (rect.bottom < 0 || rect.top > window.innerHeight) {
            return;
        }
        if (rect.right < 0 || rect.left > window.innerWidth) {
            return;
        }
        
        // Assign ID
        const somId = idCounter++;
        el.setAttribute('data-som-id', somId);
        
        // Create marker
        const marker = document.createElement('div');
        marker.className = 'som-marker';
        marker.textContent = somId;
        
        // Position marker
        const scrollX = window.scrollX || document.documentElement.scrollLeft;
        const scrollY = window.scrollY || document.documentElement.scrollTop;
        marker.style.left = (rect.left + scrollX) + 'px';
        marker.style.top = (rect.top + scrollY - 14) + 'px';
        
        // Color by type
        const tag = el.tagName.toLowerCase();
        if (tag === 'input' || tag === 'textarea' || tag === 'select') {
            marker.classList.add('som-input');
        } else if (tag === 'a') {
            marker.classList.add('som-link');
        }
        
        container.appendChild(marker);
        
        // Collect element info
        results.push({
            id: somId,
            tag: tag,
            type: el.type || null,
            role: el.getAttribute('role'),
            text: (el.textContent || '').trim().substring(0, 100),
            placeholder: el.placeholder,
            ariaLabel: el.getAttribute('aria-label'),
            name: el.name,
            href: el.href,
            rect: {
                x: rect.x,
                y: rect.y,
                width: rect.width,
                height: rect.height
            }
        });
    });
    
    return results;
})();
"""

# JavaScript to remove Set-of-Marks overlay
SOM_REMOVAL_SCRIPT = """
(function() {
    // Remove markers
    const markers = document.querySelectorAll('.som-marker');
    markers.forEach(m => m.remove());
    
    // Remove container
    const container = document.getElementById('som-container');
    if (container) container.remove();
    
    // Remove data attributes
    const elements = document.querySelectorAll('[data-som-id]');
    elements.forEach(el => el.removeAttribute('data-som-id'));
    
    // Remove styles
    const styles = document.getElementById('som-styles');
    if (styles) styles.remove();
})();
"""


class SetOfMarksOverlay:
    """
    Manages Set-of-Marks overlay for element identification.
    Assigns numeric IDs to interactive elements for LLM grounding.
    """
    
    def __init__(self, page):
        """
        Initialize overlay.
        
        Args:
            page: Playwright page object
        """
        self.page = page
        self.elements: list[dict[str, Any]] = []
        self.is_active = False
    
    async def inject(self) -> list[dict[str, Any]]:
        """
        Inject Set-of-Marks overlay into the page.
        
        Returns:
            List of marked elements with their IDs
        """
        try:
            self.elements = await self.page.evaluate(SOM_INJECTION_SCRIPT)
            self.is_active = True
            return self.elements
        except Exception as e:
            print(f"Error injecting SoM: {e}")
            return []
    
    async def remove(self) -> None:
        """Remove Set-of-Marks overlay from the page."""
        try:
            await self.page.evaluate(SOM_REMOVAL_SCRIPT)
            self.is_active = False
            self.elements = []
        except Exception:
            pass
    
    async def refresh(self) -> list[dict[str, Any]]:
        """
        Refresh overlay (remove and re-inject).
        
        Returns:
            Updated list of marked elements
        """
        await self.remove()
        return await self.inject()
    
    def get_element_by_id(self, som_id: int) -> dict[str, Any] | None:
        """
        Get element info by SoM ID.
        
        Args:
            som_id: Set-of-Marks ID
            
        Returns:
            Element info or None
        """
        for element in self.elements:
            if element.get('id') == som_id:
                return element
        return None
    
    async def click_element(self, som_id: int) -> bool:
        """
        Click an element by its SoM ID.
        
        Args:
            som_id: Set-of-Marks ID
            
        Returns:
            True if click succeeded
        """
        try:
            await self.page.click(f'[data-som-id="{som_id}"]')
            return True
        except Exception:
            return False
    
    async def type_into_element(self, som_id: int, text: str) -> bool:
        """
        Type text into an element by its SoM ID.
        
        Args:
            som_id: Set-of-Marks ID
            text: Text to type
            
        Returns:
            True if typing succeeded
        """
        try:
            await self.page.fill(f'[data-som-id="{som_id}"]', text)
            return True
        except Exception:
            return False
    
    def get_elements_text(self) -> str:
        """
        Get text representation of marked elements for LLM.
        
        Returns:
            Formatted text listing all elements
        """
        if not self.elements:
            return "No interactive elements found"
        
        lines = []
        for el in self.elements:
            parts = [f"[{el['id']}]"]
            
            # Element type
            tag = el.get('tag', '').upper()
            el_type = el.get('type')
            role = el.get('role')
            
            if role:
                parts.append(role.upper())
            elif el_type:
                parts.append(f"{tag}({el_type})")
            else:
                parts.append(tag)
            
            # Label/text
            label = (
                el.get('ariaLabel') or 
                el.get('placeholder') or 
                el.get('text') or 
                el.get('name') or
                ''
            ).strip()
            
            if label:
                # Truncate long labels
                if len(label) > 50:
                    label = label[:50] + "..."
                parts.append(f'"{label}"')
            
            # Link href
            href = el.get('href')
            if href and not href.startswith('javascript:'):
                # Show just the path, not full URL
                if '://' in href:
                    try:
                        from urllib.parse import urlparse
                        parsed = urlparse(href)
                        href_display = parsed.path or '/'
                    except Exception:
                        href_display = href[:50]
                else:
                    href_display = href[:50]
                parts.append(f"-> {href_display}")
            
            lines.append(" ".join(parts))
        
        return "\n".join(lines)
    
    async def get_element_selector(self, som_id: int) -> str:
        """
        Get CSS selector for element by SoM ID.
        
        Args:
            som_id: Set-of-Marks ID
            
        Returns:
            CSS selector string
        """
        return f'[data-som-id="{som_id}"]'
    
    async def take_screenshot_with_markers(self) -> bytes:
        """
        Take screenshot with SoM markers visible.
        
        Returns:
            Screenshot as bytes
        """
        if not self.is_active:
            await self.inject()
        
        screenshot = await self.page.screenshot(full_page=False)
        
        return screenshot
    
    def get_buttons(self) -> list[dict[str, Any]]:
        """Get all button elements."""
        return [
            el for el in self.elements 
            if el.get('tag') == 'button' or el.get('role') == 'button'
        ]
    
    def get_links(self) -> list[dict[str, Any]]:
        """Get all link elements."""
        return [
            el for el in self.elements 
            if el.get('tag') == 'a' or el.get('role') == 'link'
        ]
    
    def get_inputs(self) -> list[dict[str, Any]]:
        """Get all input elements."""
        return [
            el for el in self.elements 
            if el.get('tag') in ('input', 'textarea', 'select')
        ]
    
    def get_forms_grouped(self) -> list[list[dict[str, Any]]]:
        """
        Get inputs grouped by their proximity (likely same form).
        
        Returns:
            List of input groups
        """
        inputs = self.get_inputs()
        if not inputs:
            return []
        
        # Simple grouping by vertical proximity
        sorted_inputs = sorted(inputs, key=lambda x: x['rect']['y'])
        
        groups = []
        current_group = [sorted_inputs[0]]
        
        for i in range(1, len(sorted_inputs)):
            prev = sorted_inputs[i - 1]
            curr = sorted_inputs[i]
            
            # If vertical distance > 100px, start new group
            if curr['rect']['y'] - prev['rect']['y'] > 100:
                groups.append(current_group)
                current_group = []
            
            current_group.append(curr)
        
        if current_group:
            groups.append(current_group)
        
        return groups
