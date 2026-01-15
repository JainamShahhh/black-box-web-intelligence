"""
Accessibility Tree Extraction.
Converts DOM to semantic accessibility representation for LLM consumption.
"""

from typing import Any
import json


class AccessibilityExtractor:
    """
    Extracts and formats accessibility trees from Playwright pages.
    Provides token-efficient representations for LLM agents.
    """
    
    # Roles to include (semantic, interactive elements)
    INCLUDE_ROLES = {
        'button', 'link', 'textbox', 'checkbox', 'radio', 'combobox',
        'listbox', 'option', 'menuitem', 'menu', 'menubar', 'tab',
        'tablist', 'tabpanel', 'dialog', 'alertdialog', 'alert',
        'form', 'searchbox', 'slider', 'spinbutton', 'switch',
        'heading', 'img', 'figure', 'article', 'main', 'navigation',
        'banner', 'contentinfo', 'complementary', 'region', 'table',
        'row', 'cell', 'columnheader', 'rowheader', 'list', 'listitem',
        'tree', 'treeitem', 'grid', 'gridcell', 'group'
    }
    
    # Roles that are interactive (can be clicked/interacted with)
    INTERACTIVE_ROLES = {
        'button', 'link', 'textbox', 'checkbox', 'radio', 'combobox',
        'listbox', 'option', 'menuitem', 'tab', 'searchbox', 'slider',
        'spinbutton', 'switch', 'treeitem', 'gridcell'
    }
    
    def __init__(self, page):
        """
        Initialize extractor.
        
        Args:
            page: Playwright page object
        """
        self.page = page
    
    async def get_snapshot(self) -> dict[str, Any] | None:
        """
        Get accessibility tree snapshot.
        
        Returns:
            Accessibility tree as dictionary
        """
        try:
            return await self.page.accessibility.snapshot()
        except Exception:
            return None
    
    async def get_formatted_tree(self, include_ids: bool = True) -> str:
        """
        Get formatted accessibility tree as string for LLM consumption.
        
        Args:
            include_ids: Include element IDs for Set-of-Marks
            
        Returns:
            Formatted tree string
        """
        snapshot = await self.get_snapshot()
        if not snapshot:
            return "Unable to capture accessibility tree"
        
        return self._format_tree(snapshot, include_ids)
    
    def _format_tree(
        self, 
        node: dict[str, Any], 
        include_ids: bool,
        depth: int = 0,
        element_counter: list[int] | None = None
    ) -> str:
        """
        Recursively format accessibility tree node.
        
        Args:
            node: Tree node
            include_ids: Include element IDs
            depth: Current depth
            element_counter: Counter for element IDs
            
        Returns:
            Formatted string
        """
        if element_counter is None:
            element_counter = [0]
        
        lines = []
        indent = "  " * depth
        
        role = node.get('role', '')
        name = node.get('name', '')
        value = node.get('value', '')
        
        # Skip nodes without meaningful content
        if not role and not name:
            for child in node.get('children', []):
                lines.append(self._format_tree(child, include_ids, depth, element_counter))
            return '\n'.join(filter(None, lines))
        
        # Build node representation
        parts = []
        
        # Add ID for interactive elements
        if include_ids and role in self.INTERACTIVE_ROLES:
            element_id = element_counter[0]
            element_counter[0] += 1
            parts.append(f"[{element_id}]")
        
        # Add role
        if role:
            parts.append(role.upper())
        
        # Add name/label
        if name:
            # Truncate very long names
            display_name = name[:100] + "..." if len(name) > 100 else name
            parts.append(f'"{display_name}"')
        
        # Add value for inputs
        if value:
            display_value = value[:50] + "..." if len(value) > 50 else value
            parts.append(f'(value: "{display_value}")')
        
        # Add state information
        states = []
        if node.get('disabled'):
            states.append('disabled')
        if node.get('checked') is True:
            states.append('checked')
        if node.get('selected'):
            states.append('selected')
        if node.get('expanded') is True:
            states.append('expanded')
        elif node.get('expanded') is False:
            states.append('collapsed')
        if node.get('required'):
            states.append('required')
        
        if states:
            parts.append(f"[{', '.join(states)}]")
        
        # Build line
        if parts:
            lines.append(f"{indent}{' '.join(parts)}")
        
        # Process children
        for child in node.get('children', []):
            child_str = self._format_tree(child, include_ids, depth + 1, element_counter)
            if child_str:
                lines.append(child_str)
        
        return '\n'.join(filter(None, lines))
    
    async def get_interactive_elements(self) -> list[dict[str, Any]]:
        """
        Get list of interactive elements with their IDs.
        
        Returns:
            List of interactive elements
        """
        snapshot = await self.get_snapshot()
        if not snapshot:
            return []
        
        elements = []
        self._collect_interactive(snapshot, elements)
        return elements
    
    def _collect_interactive(
        self, 
        node: dict[str, Any], 
        elements: list[dict[str, Any]],
        counter: list[int] | None = None
    ) -> None:
        """
        Recursively collect interactive elements.
        
        Args:
            node: Tree node
            elements: List to append to
            counter: Element counter
        """
        if counter is None:
            counter = [0]
        
        role = node.get('role', '')
        
        if role in self.INTERACTIVE_ROLES:
            element_id = counter[0]
            counter[0] += 1
            
            elements.append({
                'id': element_id,
                'role': role,
                'name': node.get('name', ''),
                'value': node.get('value', ''),
                'disabled': node.get('disabled', False),
                'checked': node.get('checked'),
                'selected': node.get('selected'),
            })
        
        for child in node.get('children', []):
            self._collect_interactive(child, elements, counter)
    
    async def get_focused_element(self) -> dict[str, Any] | None:
        """
        Get the currently focused element.
        
        Returns:
            Focused element info or None
        """
        try:
            result = await self.page.evaluate("""
                () => {
                    const el = document.activeElement;
                    if (!el || el === document.body) return null;
                    
                    return {
                        tag: el.tagName,
                        id: el.id,
                        className: el.className,
                        type: el.type,
                        value: el.value,
                        placeholder: el.placeholder,
                        ariaLabel: el.getAttribute('aria-label')
                    };
                }
            """)
            return result
        except Exception:
            return None
    
    async def get_page_summary(self) -> dict[str, Any]:
        """
        Get a summary of the page structure.
        
        Returns:
            Page summary dictionary
        """
        snapshot = await self.get_snapshot()
        if not snapshot:
            return {"error": "Unable to capture accessibility tree"}
        
        # Count elements by role
        role_counts: dict[str, int] = {}
        interactive_count = 0
        
        def count_roles(node: dict[str, Any]) -> None:
            nonlocal interactive_count
            role = node.get('role', '')
            if role:
                role_counts[role] = role_counts.get(role, 0) + 1
                if role in self.INTERACTIVE_ROLES:
                    interactive_count += 1
            for child in node.get('children', []):
                count_roles(child)
        
        count_roles(snapshot)
        
        # Get headings
        headings = []
        
        def collect_headings(node: dict[str, Any]) -> None:
            if node.get('role') == 'heading':
                headings.append(node.get('name', ''))
            for child in node.get('children', []):
                collect_headings(child)
        
        collect_headings(snapshot)
        
        return {
            "url": self.page.url,
            "title": await self.page.title(),
            "interactive_elements": interactive_count,
            "role_counts": role_counts,
            "headings": headings[:10],  # First 10 headings
        }
    
    async def get_forms(self) -> list[dict[str, Any]]:
        """
        Get all forms on the page with their inputs.
        
        Returns:
            List of forms with their fields
        """
        try:
            forms = await self.page.evaluate("""
                () => {
                    const forms = Array.from(document.querySelectorAll('form'));
                    return forms.map((form, formIndex) => {
                        const inputs = Array.from(form.querySelectorAll('input, select, textarea'));
                        return {
                            index: formIndex,
                            action: form.action,
                            method: form.method,
                            id: form.id,
                            fields: inputs.map((input, inputIndex) => ({
                                index: inputIndex,
                                tag: input.tagName,
                                type: input.type || 'text',
                                name: input.name,
                                id: input.id,
                                placeholder: input.placeholder,
                                required: input.required,
                                value: input.value,
                                ariaLabel: input.getAttribute('aria-label')
                            }))
                        };
                    });
                }
            """)
            return forms
        except Exception:
            return []
