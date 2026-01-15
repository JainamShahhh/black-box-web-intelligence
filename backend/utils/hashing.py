"""
Hashing Utilities - SimHash for state deduplication.
"""

import hashlib
from typing import Any

try:
    from simhash import Simhash
    SIMHASH_AVAILABLE = True
except ImportError:
    SIMHASH_AVAILABLE = False


def compute_simhash(data: str | list[str] | dict[str, Any]) -> str:
    """
    Compute SimHash of data for similarity comparison.
    
    Args:
        data: String, list of features, or dict to hash
        
    Returns:
        Hash string
    """
    # Convert to feature list
    if isinstance(data, str):
        features = data.split()
    elif isinstance(data, dict):
        features = _dict_to_features(data)
    elif isinstance(data, list):
        features = data
    else:
        features = [str(data)]
    
    if SIMHASH_AVAILABLE:
        return str(Simhash(features).value)
    else:
        # Fallback to MD5
        combined = " ".join(str(f) for f in features)
        return hashlib.md5(combined.encode()).hexdigest()


def hamming_distance(hash1: str, hash2: str) -> int:
    """
    Calculate Hamming distance between two SimHash values.
    
    Args:
        hash1: First hash
        hash2: Second hash
        
    Returns:
        Hamming distance (number of differing bits)
    """
    if SIMHASH_AVAILABLE:
        try:
            h1 = Simhash(int(hash1))
            h2 = Simhash(int(hash2))
            return h1.distance(h2)
        except (ValueError, TypeError):
            pass
    
    # Fallback for MD5 hashes - character difference
    if len(hash1) != len(hash2):
        return max(len(hash1), len(hash2))
    
    return sum(c1 != c2 for c1, c2 in zip(hash1, hash2))


def _dict_to_features(data: dict[str, Any], prefix: str = "") -> list[str]:
    """
    Convert dictionary to list of features for hashing.
    
    Args:
        data: Dictionary to convert
        prefix: Key prefix for nested dicts
        
    Returns:
        List of feature strings
    """
    features = []
    
    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else key
        
        if isinstance(value, dict):
            features.extend(_dict_to_features(value, full_key))
        elif isinstance(value, list):
            features.append(f"{full_key}:list[{len(value)}]")
            for i, item in enumerate(value[:5]):  # Limit items
                if isinstance(item, dict):
                    features.extend(_dict_to_features(item, f"{full_key}[{i}]"))
                else:
                    features.append(f"{full_key}[{i}]:{type(item).__name__}")
        else:
            features.append(f"{full_key}:{type(value).__name__}")
    
    return features


def similarity(hash1: str, hash2: str) -> float:
    """
    Calculate similarity between two hashes (0-1).
    
    Args:
        hash1: First hash
        hash2: Second hash
        
    Returns:
        Similarity score (1.0 = identical)
    """
    distance = hamming_distance(hash1, hash2)
    
    # For SimHash (64-bit), max distance is 64
    if SIMHASH_AVAILABLE:
        max_distance = 64
    else:
        max_distance = max(len(hash1), len(hash2))
    
    if max_distance == 0:
        return 1.0
    
    return 1.0 - (distance / max_distance)
