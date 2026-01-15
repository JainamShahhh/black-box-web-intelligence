"""
GraphQL Introspection Module.
Detects and extracts GraphQL schemas through introspection queries.
"""

import json
import re
from typing import Any
from dataclasses import dataclass, field


INTROSPECTION_QUERY = """
query IntrospectionQuery {
  __schema {
    queryType { name }
    mutationType { name }
    subscriptionType { name }
    types {
      ...FullType
    }
    directives {
      name
      description
      locations
      args {
        ...InputValue
      }
    }
  }
}

fragment FullType on __Type {
  kind
  name
  description
  fields(includeDeprecated: true) {
    name
    description
    args {
      ...InputValue
    }
    type {
      ...TypeRef
    }
    isDeprecated
    deprecationReason
  }
  inputFields {
    ...InputValue
  }
  interfaces {
    ...TypeRef
  }
  enumValues(includeDeprecated: true) {
    name
    description
    isDeprecated
    deprecationReason
  }
  possibleTypes {
    ...TypeRef
  }
}

fragment InputValue on __InputValue {
  name
  description
  type {
    ...TypeRef
  }
  defaultValue
}

fragment TypeRef on __Type {
  kind
  name
  ofType {
    kind
    name
    ofType {
      kind
      name
      ofType {
        kind
        name
        ofType {
          kind
          name
          ofType {
            kind
            name
            ofType {
              kind
              name
            }
          }
        }
      }
    }
  }
}
"""


@dataclass
class GraphQLField:
    """A GraphQL field definition."""
    name: str
    type_name: str
    description: str | None = None
    args: list[dict] = field(default_factory=list)
    is_deprecated: bool = False


@dataclass
class GraphQLType:
    """A GraphQL type definition."""
    name: str
    kind: str  # OBJECT, INPUT_OBJECT, ENUM, SCALAR, etc.
    description: str | None = None
    fields: list[GraphQLField] = field(default_factory=list)


@dataclass
class GraphQLEndpoint:
    """Detected GraphQL endpoint with extracted schema."""
    url: str
    introspection_enabled: bool = False
    query_type: str | None = None
    mutation_type: str | None = None
    subscription_type: str | None = None
    types: list[GraphQLType] = field(default_factory=list)
    queries: list[GraphQLField] = field(default_factory=list)
    mutations: list[GraphQLField] = field(default_factory=list)
    security_findings: list[str] = field(default_factory=list)


class GraphQLIntrospector:
    """
    Detect GraphQL endpoints and perform introspection.
    """
    
    def __init__(self):
        self.endpoints: list[GraphQLEndpoint] = []
        self.detected_urls: set[str] = set()
    
    def detect_graphql(self, url: str, response_body: str, content_type: str = '') -> bool:
        """Detect if a response is from a GraphQL endpoint."""
        # Check URL patterns
        if '/graphql' in url.lower() or '/gql' in url.lower():
            self.detected_urls.add(url)
            return True
        
        # Check response structure
        try:
            data = json.loads(response_body)
            if isinstance(data, dict):
                # GraphQL responses have 'data' and/or 'errors' keys
                if 'data' in data or 'errors' in data:
                    if '__schema' in str(data) or '__typename' in str(data):
                        self.detected_urls.add(url)
                        return True
                    # Check for GraphQL-style structure
                    if isinstance(data.get('data'), dict):
                        self.detected_urls.add(url)
                        return True
        except:
            pass
        
        return False
    
    def parse_introspection_result(self, url: str, response: dict) -> GraphQLEndpoint:
        """Parse introspection query response."""
        endpoint = GraphQLEndpoint(url=url)
        
        schema = response.get('data', {}).get('__schema', {})
        if not schema:
            return endpoint
        
        endpoint.introspection_enabled = True
        
        # Get root types
        if schema.get('queryType'):
            endpoint.query_type = schema['queryType'].get('name')
        if schema.get('mutationType'):
            endpoint.mutation_type = schema['mutationType'].get('name')
        if schema.get('subscriptionType'):
            endpoint.subscription_type = schema['subscriptionType'].get('name')
        
        # Parse all types
        for type_def in schema.get('types', []):
            name = type_def.get('name', '')
            
            # Skip internal types
            if name.startswith('__'):
                continue
            
            gql_type = GraphQLType(
                name=name,
                kind=type_def.get('kind', 'UNKNOWN'),
                description=type_def.get('description')
            )
            
            # Parse fields
            for field_def in type_def.get('fields', []) or []:
                gql_field = GraphQLField(
                    name=field_def.get('name', ''),
                    type_name=self._get_type_name(field_def.get('type', {})),
                    description=field_def.get('description'),
                    args=[{'name': a.get('name'), 'type': self._get_type_name(a.get('type', {}))} 
                          for a in field_def.get('args', [])],
                    is_deprecated=field_def.get('isDeprecated', False)
                )
                gql_type.fields.append(gql_field)
                
                # Add to queries/mutations
                if name == endpoint.query_type:
                    endpoint.queries.append(gql_field)
                elif name == endpoint.mutation_type:
                    endpoint.mutations.append(gql_field)
            
            endpoint.types.append(gql_type)
        
        # Security analysis
        self._analyze_security(endpoint)
        
        return endpoint
    
    def _get_type_name(self, type_ref: dict) -> str:
        """Recursively get the full type name."""
        if not type_ref:
            return 'Unknown'
        
        kind = type_ref.get('kind', '')
        name = type_ref.get('name', '')
        of_type = type_ref.get('ofType')
        
        if name:
            return name
        elif kind == 'NON_NULL':
            return f"{self._get_type_name(of_type)}!"
        elif kind == 'LIST':
            return f"[{self._get_type_name(of_type)}]"
        else:
            return 'Unknown'
    
    def _analyze_security(self, endpoint: GraphQLEndpoint) -> None:
        """Analyze GraphQL endpoint for security issues."""
        findings = []
        
        # Introspection enabled
        if endpoint.introspection_enabled:
            findings.append("WARNING: Introspection is enabled - schema is exposed")
        
        # Dangerous mutations
        dangerous_patterns = ['delete', 'remove', 'admin', 'password', 'token', 'secret']
        for mutation in endpoint.mutations:
            name_lower = mutation.name.lower()
            for pattern in dangerous_patterns:
                if pattern in name_lower:
                    findings.append(f"SENSITIVE: Mutation '{mutation.name}' may be sensitive")
                    break
        
        # Large response types
        for gql_type in endpoint.types:
            if len(gql_type.fields) > 50:
                findings.append(f"INFO: Type '{gql_type.name}' has many fields ({len(gql_type.fields)})")
        
        # Check for auth-related types
        auth_patterns = ['user', 'auth', 'login', 'session', 'token']
        for gql_type in endpoint.types:
            name_lower = gql_type.name.lower()
            for pattern in auth_patterns:
                if pattern in name_lower:
                    findings.append(f"AUTH: Type '{gql_type.name}' appears auth-related")
                    break
        
        endpoint.security_findings = findings
    
    def get_report(self) -> dict:
        """Get GraphQL introspection report."""
        return {
            'detected_endpoints': list(self.detected_urls),
            'endpoints': [
                {
                    'url': ep.url,
                    'introspection_enabled': ep.introspection_enabled,
                    'query_count': len(ep.queries),
                    'mutation_count': len(ep.mutations),
                    'type_count': len(ep.types),
                    'queries': [{'name': q.name, 'type': q.type_name} for q in ep.queries[:20]],
                    'mutations': [{'name': m.name, 'type': m.type_name} for m in ep.mutations[:20]],
                    'security_findings': ep.security_findings
                }
                for ep in self.endpoints
            ]
        }


# Singleton per session
_introspectors: dict[str, GraphQLIntrospector] = {}


def get_graphql_introspector(session_id: str) -> GraphQLIntrospector:
    """Get or create GraphQL introspector for session."""
    if session_id not in _introspectors:
        _introspectors[session_id] = GraphQLIntrospector()
    return _introspectors[session_id]
