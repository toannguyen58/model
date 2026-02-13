"""
Detects and categorizes body types from KBB tabs - Improved for BMW issue
"""
import re
from typing import List, Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class BodyTypeDetector:
    """Detects body types from tab names - FIXED for BMW issue"""

    def __init__(self):
        self.body_type_mapping = {
            'sedan': ['sedan', 'sedans', '4 door', '4-door', '4d'],
            'suv': ['suv', 'suvs', 'crossover', 'crossovers', 'sport utility'],
            'wagon': ['wagon', 'wagons', 'estate', 'touring', 'sportwagon'],
            'coupe': ['coupe', 'coupes', '2 door', '2-door', '2d'],
            'convertible': ['convertible', 'convertibles', 'cabriolet', 'roadster'],
            'truck': ['truck', 'pickup', 'pickups'],
            'van': ['van', 'minivan', 'vans', 'minivans'],
            'hatchback': ['hatchback', 'hatchbacks', '5 door', '5-door', '5d'],
            'hybrid': ['hybrid', 'hev', 'plugin', 'plug-in'],
            'electric': ['electric', 'ev', 'bev', 'electric vehicle'],
            'performance': ['m performance', 'amg', 's line', 'f sport', 'type r', 'gt'],
            'default': ['default', 'standard', 'base']
        }
        self.detected_bodytypes = {}

    def detect_body_type(self, tab_name: str) -> str:
        """
        Detect body type from tab name - IMPROVED for BMW
        Returns standardized body type name
        """
        tab_name_lower = tab_name.lower()

        # Special handling for BMW patterns
        bmw_patterns = {
            'wagon': [r'wagon', r'touring', r'sportwagon'],
            'gran turismo': ['gran turismo', 'gt'],
            'gran coupe': ['gran coupe', '4 series gran coupe'],
        }

        # Check for BMW specific patterns first
        for body_type, patterns in bmw_patterns.items():
            for pattern in patterns:
                if isinstance(pattern, str) and pattern in tab_name_lower:
                    logger.debug(f"Detected BMW {body_type} from: {tab_name}")
                    return 'wagon' if 'wagon' in body_type else 'sedan'
                elif isinstance(pattern, str) and re.search(pattern, tab_name_lower, re.IGNORECASE):
                    logger.debug(f"Detected BMW {body_type} from pattern: {tab_name}")
                    return 'wagon' if 'wagon' in body_type else 'sedan'

        # Check for specific body types in mapping
        for std_name, keywords in self.body_type_mapping.items():
            for keyword in keywords:
                if keyword in tab_name_lower:
                    logger.debug(f"Detected body type '{std_name}' from tab: {tab_name}")
                    return std_name

        # Check for numeric patterns like "4D", "2D"
        if re.search(r'\b4d\b|\b4 door\b|\b4-door\b', tab_name_lower):
            return 'sedan'
        elif re.search(r'\b2d\b|\b2 door\b|\b2-door\b', tab_name_lower):
            return 'coupe'
        elif re.search(r'\b5d\b|\b5 door\b|\b5-door\b', tab_name_lower):
            return 'hatchback'

        # Default based on common terms
        if any(word in tab_name_lower for word in ['le', 'se', 'xle', 'limited', 'premium', 'sport']):
            return 'sedan'  # Common trim levels usually for sedans

        logger.debug(f"No body type detected, using 'default': {tab_name}")
        return 'default'

    def categorize_tabs(self, tab_names: List[str]) -> Dict[str, List[str]]:
        """
        Categorize all tabs by body type - FIXED for duplicate detection
        Returns: {body_type: [tab_names]}
        """
        categorized = {}

        for tab_name in tab_names:
            body_type = self.detect_body_type(tab_name)

            if body_type not in categorized:
                categorized[body_type] = []

            # Check if this tab is actually different from others in same category
            if not self._is_duplicate_tab(tab_name, categorized[body_type]):
                categorized[body_type].append(tab_name)

            # Store for reference
            self.detected_bodytypes[tab_name] = body_type

        # Filter out categories with no tabs
        categorized = {k: v for k, v in categorized.items() if v}

        logger.info(f"Categorized {len(tab_names)} tabs into {len(categorized)} body types")
        for body_type, tabs in categorized.items():
            logger.info(f"  {body_type}: {len(tabs)} tabs")

        return categorized

    def _is_duplicate_tab(self, new_tab: str, existing_tabs: List[str]) -> bool:
        """
        Check if a tab is a duplicate (different name but same content)
        Common in KBB where tabs might have slightly different names but same data
        """
        new_lower = new_tab.lower()

        for existing in existing_tabs:
            existing_lower = existing.lower()

            # If tabs are very similar (85% similar words), consider duplicate
            new_words = set(new_lower.split())
            existing_words = set(existing_lower.split())

            if len(new_words) > 0 and len(existing_words) > 0:
                similarity = len(new_words.intersection(existing_words)) / max(len(new_words), len(existing_words))
                if similarity > 0.7:  # 70% similar
                    logger.debug(f"Tab '{new_tab}' appears similar to '{existing}' (similarity: {similarity:.2f})")
                    return True

        return False

    def get_bodytype_for_tab(self, tab_name: str) -> Optional[str]:
        """Get body type for a specific tab"""
        return self.detected_bodytypes.get(tab_name)

    def should_process_separately(self, categorized_tabs: Dict[str, List[str]]) -> bool:
        """
        Determine if different body types should be processed separately
        Now also checks if tabs actually have different data
        """
        # If we have multiple distinct body types
        distinct_bodytypes = [bt for bt in categorized_tabs.keys() if bt != 'default']

        if len(distinct_bodytypes) > 1:
            # Additional check: if tabs within same category are actually different
            for body_type, tabs in categorized_tabs.items():
                if len(tabs) > 1:
                    # Check if tabs with same body type name might actually be different
                    tab_keywords = [t.lower().split() for t in tabs]
                    if len(set(tuple(t) for t in tab_keywords)) > 1:
                        return True
            return True

        return False

    def get_bodytype_filename(self, body_type: str, make: str, model: str, year: str) -> str:
        """Generate filename for a specific body type"""
        sanitized_make = make.lower().replace(' ', '_')
        sanitized_model = model.lower().replace(' ', '_')

        if body_type == 'default':
            return f"{sanitized_make}_{sanitized_model}_{year}_specs.csv"
        else:
            return f"{sanitized_make}_{sanitized_model}_{year}_{body_type}_specs.csv"