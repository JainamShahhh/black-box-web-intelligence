"""
URL Clustering - Groups URLs by structural patterns.
Identifies path parameters and clusters similar endpoints.
"""

import re
from typing import Any
from collections import defaultdict
from urllib.parse import urlparse, parse_qs
import math


class URLClusterer:
    """
    Clusters URLs by structural similarity.
    Uses entropy analysis to identify dynamic path segments.
    """
    
    def __init__(self):
        """Initialize URL clusterer."""
        self.clusters: dict[str, list[str]] = defaultdict(list)
        self.segment_stats: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    
    def add_url(self, url: str) -> str:
        """
        Add URL and return its cluster pattern.
        
        Args:
            url: URL to add
            
        Returns:
            Cluster pattern (e.g., "/api/users/{id}")
        """
        pattern = self.url_to_pattern(url)
        self.clusters[pattern].append(url)
        return pattern
    
    def url_to_pattern(self, url: str) -> str:
        """
        Convert URL to pattern by replacing dynamic segments.
        
        Args:
            url: Full URL
            
        Returns:
            URL pattern with placeholders
        """
        parsed = urlparse(url)
        path = parsed.path
        
        # Split path into segments
        segments = [s for s in path.split('/') if s]
        pattern_segments = []
        
        for i, segment in enumerate(segments):
            if self._is_dynamic_segment(segment, i):
                pattern_segments.append("{id}")
            else:
                pattern_segments.append(segment)
                # Track segment values for entropy calculation
                self.segment_stats[i][segment] += 1
        
        return '/' + '/'.join(pattern_segments)
    
    def _is_dynamic_segment(self, segment: str, position: int) -> bool:
        """
        Determine if a segment is dynamic (a parameter).
        
        Args:
            segment: Path segment
            position: Position in path
            
        Returns:
            True if segment is dynamic
        """
        # UUID pattern
        if re.match(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
            segment,
            re.IGNORECASE
        ):
            return True
        
        # Numeric ID
        if segment.isdigit():
            return True
        
        # MongoDB ObjectId
        if re.match(r'^[0-9a-f]{24}$', segment, re.IGNORECASE):
            return True
        
        # Short alphanumeric ID (high entropy)
        if len(segment) >= 6 and segment.isalnum():
            entropy = self._calculate_entropy(segment)
            if entropy > 3.0:  # High entropy indicates random
                return True
        
        # Check if segment varies at this position
        if position in self.segment_stats:
            unique_values = len(self.segment_stats[position])
            total_occurrences = sum(self.segment_stats[position].values())
            
            if unique_values > 5 and unique_values / total_occurrences > 0.5:
                # Many different values at this position
                return True
        
        return False
    
    def _calculate_entropy(self, text: str) -> float:
        """
        Calculate Shannon entropy of text.
        Higher entropy = more random/dynamic.
        
        Args:
            text: Text to analyze
            
        Returns:
            Entropy value
        """
        if not text:
            return 0.0
        
        # Count character frequencies
        freq: dict[str, int] = {}
        for char in text:
            freq[char] = freq.get(char, 0) + 1
        
        # Calculate entropy
        length = len(text)
        entropy = 0.0
        
        for count in freq.values():
            prob = count / length
            if prob > 0:
                entropy -= prob * math.log2(prob)
        
        return entropy
    
    def cluster_urls(self, urls: list[str]) -> dict[str, list[str]]:
        """
        Cluster a list of URLs.
        
        Args:
            urls: URLs to cluster
            
        Returns:
            Dictionary mapping patterns to URL lists
        """
        self.clusters.clear()
        
        for url in urls:
            self.add_url(url)
        
        return dict(self.clusters)
    
    def cluster(self, urls: list[str]) -> dict[str, list[str]]:
        """
        Alias for cluster_urls.
        
        Args:
            urls: URLs to cluster
            
        Returns:
            Dictionary mapping patterns to URL lists
        """
        return self.cluster_urls(urls)
    
    def get_pattern_for_url(self, url: str) -> str:
        """
        Get pattern for a URL without adding it.
        
        Args:
            url: URL to analyze
            
        Returns:
            Pattern string
        """
        return self.url_to_pattern(url)
    
    def merge_similar_patterns(self) -> dict[str, list[str]]:
        """
        Merge patterns that differ only in parameter names.
        
        Returns:
            Merged clusters
        """
        # Group patterns by structure (ignoring param names)
        normalized: dict[str, list[str]] = defaultdict(list)
        
        for pattern, urls in self.clusters.items():
            # Normalize all {xxx} to {id}
            normalized_pattern = re.sub(r'\{[^}]+\}', '{id}', pattern)
            normalized[normalized_pattern].extend(urls)
        
        return dict(normalized)
    
    def extract_path_params(self, pattern: str) -> list[dict[str, Any]]:
        """
        Extract path parameter definitions from pattern.
        
        Args:
            pattern: URL pattern
            
        Returns:
            List of parameter definitions
        """
        params = []
        segments = pattern.split('/')
        
        for i, segment in enumerate(segments):
            if segment.startswith('{') and segment.endswith('}'):
                param_name = segment[1:-1]
                params.append({
                    "name": param_name,
                    "position": i,
                    "in": "path",
                    "required": True,
                    "schema": {"type": "string"}
                })
        
        return params
    
    def get_statistics(self) -> dict[str, Any]:
        """
        Get clustering statistics.
        
        Returns:
            Statistics dictionary
        """
        return {
            "total_patterns": len(self.clusters),
            "total_urls": sum(len(urls) for urls in self.clusters.values()),
            "largest_cluster": max(
                (len(urls) for urls in self.clusters.values()),
                default=0
            ),
            "patterns": [
                {"pattern": p, "count": len(urls)}
                for p, urls in sorted(
                    self.clusters.items(),
                    key=lambda x: -len(x[1])
                )[:20]
            ]
        }
