"""Browser module - Playwright management, accessibility, and Set-of-Marks."""

from .manager import BrowserManager
from .accessibility import AccessibilityExtractor
from .set_of_marks import SetOfMarksOverlay

__all__ = [
    "BrowserManager",
    "AccessibilityExtractor",
    "SetOfMarksOverlay",
]
