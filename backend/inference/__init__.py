"""Inference module - URL clustering, schema merging, and workflow detection."""

from .url_clustering import URLClusterer
from .schema_merger import SchemaMerger
from .workflow_detector import WorkflowDetector
from .permission_mapper import PermissionMapper

__all__ = [
    "URLClusterer",
    "SchemaMerger",
    "WorkflowDetector",
    "PermissionMapper",
]
