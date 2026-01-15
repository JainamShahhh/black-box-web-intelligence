"""
Schema Merger - Combines JSON schemas from multiple observations.
Uses union strategy to handle optional fields and type variations.
"""

import json
from typing import Any
from copy import deepcopy

try:
    from genson import SchemaBuilder
    GENSON_AVAILABLE = True
except ImportError:
    GENSON_AVAILABLE = False


class SchemaMerger:
    """
    Merges JSON schemas using union strategy.
    Handles optional fields, type variations, and nested objects.
    """
    
    def __init__(self):
        """Initialize schema merger."""
        self.schemas: dict[str, dict[str, Any]] = {}
        self.observation_counts: dict[str, int] = {}
    
    def merge(
        self,
        pattern: str,
        new_data: dict[str, Any] | str
    ) -> dict[str, Any]:
        """
        Merge new observation into existing schema.
        
        Args:
            pattern: Endpoint pattern (e.g., "GET /api/users/{id}")
            new_data: New JSON data or JSON string
            
        Returns:
            Updated merged schema
        """
        # Parse if string
        if isinstance(new_data, str):
            try:
                new_data = json.loads(new_data)
            except json.JSONDecodeError:
                return self.schemas.get(pattern, {})
        
        # Track observation count
        self.observation_counts[pattern] = self.observation_counts.get(pattern, 0) + 1
        
        if GENSON_AVAILABLE:
            return self._merge_with_genson(pattern, new_data)
        else:
            return self._merge_manual(pattern, new_data)
    
    def _merge_with_genson(
        self,
        pattern: str,
        new_data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Merge using genson library.
        
        Args:
            pattern: Endpoint pattern
            new_data: New data
            
        Returns:
            Merged schema
        """
        builder = SchemaBuilder()
        
        # Add existing schema if present
        if pattern in self.schemas:
            builder.add_schema(self.schemas[pattern])
        
        # Add new data
        builder.add_object(new_data)
        
        # Get merged schema
        merged = builder.to_schema()
        self.schemas[pattern] = merged
        
        return merged
    
    def _merge_manual(
        self,
        pattern: str,
        new_data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Manual schema merging without genson.
        
        Args:
            pattern: Endpoint pattern
            new_data: New data
            
        Returns:
            Merged schema
        """
        # Infer schema from new data
        new_schema = self._infer_schema(new_data)
        
        if pattern not in self.schemas:
            self.schemas[pattern] = new_schema
            return new_schema
        
        # Merge with existing
        existing = self.schemas[pattern]
        merged = self._merge_schemas(existing, new_schema)
        self.schemas[pattern] = merged
        
        return merged
    
    def _infer_schema(self, data: Any) -> dict[str, Any]:
        """
        Infer JSON schema from data.
        
        Args:
            data: Data to analyze
            
        Returns:
            Inferred schema
        """
        if data is None:
            return {"type": "null"}
        
        if isinstance(data, bool):
            return {"type": "boolean"}
        
        if isinstance(data, int):
            return {"type": "integer"}
        
        if isinstance(data, float):
            return {"type": "number"}
        
        if isinstance(data, str):
            schema: dict[str, Any] = {"type": "string"}
            # Detect formats
            if self._is_email(data):
                schema["format"] = "email"
            elif self._is_date(data):
                schema["format"] = "date"
            elif self._is_datetime(data):
                schema["format"] = "date-time"
            elif self._is_uri(data):
                schema["format"] = "uri"
            elif self._is_uuid(data):
                schema["format"] = "uuid"
            return schema
        
        if isinstance(data, list):
            if not data:
                return {"type": "array", "items": {}}
            # Infer from first item
            items_schema = self._infer_schema(data[0])
            return {"type": "array", "items": items_schema}
        
        if isinstance(data, dict):
            properties = {}
            required = []
            
            for key, value in data.items():
                properties[key] = self._infer_schema(value)
                required.append(key)
            
            return {
                "type": "object",
                "properties": properties,
                "required": required
            }
        
        return {}
    
    def _merge_schemas(
        self,
        schema1: dict[str, Any],
        schema2: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Merge two schemas using union strategy.
        
        Args:
            schema1: First schema
            schema2: Second schema
            
        Returns:
            Merged schema
        """
        type1 = schema1.get("type")
        type2 = schema2.get("type")
        
        # Same type - deep merge
        if type1 == type2:
            if type1 == "object":
                return self._merge_object_schemas(schema1, schema2)
            elif type1 == "array":
                return self._merge_array_schemas(schema1, schema2)
            else:
                # For primitives, keep either
                return deepcopy(schema1)
        
        # Different types - create anyOf
        if type1 and type2:
            return {
                "anyOf": [
                    deepcopy(schema1),
                    deepcopy(schema2)
                ]
            }
        
        # One is null - make nullable
        if type1 == "null":
            merged = deepcopy(schema2)
            merged["nullable"] = True
            return merged
        
        if type2 == "null":
            merged = deepcopy(schema1)
            merged["nullable"] = True
            return merged
        
        return deepcopy(schema1) or deepcopy(schema2)
    
    def _merge_object_schemas(
        self,
        schema1: dict[str, Any],
        schema2: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Merge two object schemas.
        
        Args:
            schema1: First object schema
            schema2: Second object schema
            
        Returns:
            Merged object schema
        """
        props1 = schema1.get("properties", {})
        props2 = schema2.get("properties", {})
        req1 = set(schema1.get("required", []))
        req2 = set(schema2.get("required", []))
        
        # Merge properties
        merged_props = deepcopy(props1)
        
        for key, value in props2.items():
            if key in merged_props:
                merged_props[key] = self._merge_schemas(merged_props[key], value)
            else:
                merged_props[key] = deepcopy(value)
        
        # Required fields are intersection (present in both)
        merged_required = list(req1 & req2)
        
        result = {
            "type": "object",
            "properties": merged_props
        }
        
        if merged_required:
            result["required"] = sorted(merged_required)
        
        return result
    
    def _merge_array_schemas(
        self,
        schema1: dict[str, Any],
        schema2: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Merge two array schemas.
        
        Args:
            schema1: First array schema
            schema2: Second array schema
            
        Returns:
            Merged array schema
        """
        items1 = schema1.get("items", {})
        items2 = schema2.get("items", {})
        
        merged_items = self._merge_schemas(items1, items2)
        
        return {
            "type": "array",
            "items": merged_items
        }
    
    # Format detection helpers
    def _is_email(self, s: str) -> bool:
        import re
        return bool(re.match(r'^[\w.-]+@[\w.-]+\.\w+$', s))
    
    def _is_date(self, s: str) -> bool:
        import re
        return bool(re.match(r'^\d{4}-\d{2}-\d{2}$', s))
    
    def _is_datetime(self, s: str) -> bool:
        import re
        return bool(re.match(r'^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}', s))
    
    def _is_uri(self, s: str) -> bool:
        return s.startswith(('http://', 'https://'))
    
    def _is_uuid(self, s: str) -> bool:
        import re
        return bool(re.match(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
            s,
            re.IGNORECASE
        ))
    
    def get_schema(self, pattern: str) -> dict[str, Any] | None:
        """Get schema for a pattern."""
        return self.schemas.get(pattern)
    
    def get_all_schemas(self) -> dict[str, dict[str, Any]]:
        """Get all schemas."""
        return deepcopy(self.schemas)
    
    def get_observation_count(self, pattern: str) -> int:
        """Get observation count for a pattern."""
        return self.observation_counts.get(pattern, 0)
    
    def infer_schema(self, data: Any) -> dict[str, Any]:
        """
        Public method to infer schema from data.
        
        Args:
            data: Data to analyze (dict, list, or primitive)
            
        Returns:
            Inferred JSON schema
        """
        if GENSON_AVAILABLE:
            builder = SchemaBuilder()
            builder.add_object(data)
            return builder.to_schema()
        else:
            return self._infer_schema(data)
