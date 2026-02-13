"""
Parses HTML data from KBB - Keep original trim names as requested
"""
from bs4 import BeautifulSoup
import pandas as pd
import logging
import re
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)


class KBBDataParser:
    """Parses KBB specification tables - Keep original trim names"""

    def __init__(self):
        self.spec_categories = {
            'engine': ['engine', 'horsepower', 'torque', 'cylinders', 'displacement'],
            'transmission': ['transmission', 'gear', 'shift'],
            'drivetrain': ['drivetrain', 'drive', '4wd', 'awd', 'fwd', 'rwd'],
            'fuel': ['fuel', 'mpg', 'gas', 'tank', 'efficiency'],
            'dimensions': ['length', 'width', 'height', 'wheelbase', 'weight', 'curb'],
            'capacity': ['seating', 'cargo', 'towing', 'capacity'],
            'brakes': ['brake', 'disc', 'drum', 'abs'],
            'suspension': ['suspension', 'strut', 'shock', 'spring'],
            'tires': ['tire', 'wheel', 'rim'],
            'performance': ['acceleration', '0-60', 'top speed', 'horsepower'],
            'features': ['feature', 'option', 'standard', 'premium']
        }

    def parse_table_data(self, table_html: str) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Parse specification table HTML into structured data
        Returns: (parsed_data, trim_names) - KEEP ORIGINAL TRIM NAMES
        """
        soup = BeautifulSoup(table_html, 'lxml')
        parsed_data = []
        trim_names = []

        try:
            # First, extract trim names from the table headers - KEEP ORIGINAL
            trim_names = self._extract_trim_names_raw(soup)

            # Parse the table rows
            rows = soup.select("tbody tr")
            logger.debug(f"Found {len(rows)} rows in table")

            for row in rows:
                cells = row.find_all("td")

                if len(cells) < 3:
                    continue  # Skip incomplete rows

                spec_name = self._clean_spec_name(cells[1].get_text(strip=True))
                values = [self._clean_value(c.get_text(strip=True)) for c in cells[2:]]

                # Truncate values to match number of trims
                if len(values) > len(trim_names):
                    values = values[:len(trim_names)]
                elif len(values) < len(trim_names):
                    # Pad with empty values if needed
                    values = values + [''] * (len(trim_names) - len(values))

                # Categorize the specification
                category = self._categorize_spec(spec_name)

                # Create data entry
                entry = {
                    "spec_name": spec_name,
                    "spec_category": category,
                    "values": values,
                    "unit": self._extract_unit(spec_name),
                    "is_numeric": self._is_numeric_value(values[0] if values else "")
                }

                parsed_data.append(entry)

            logger.info(f"Parsed {len(parsed_data)} specifications for {len(trim_names)} trims")
            return parsed_data, trim_names

        except Exception as e:
            logger.error(f"Error parsing table data: {e}")
            return [], []

    def _extract_trim_names_raw(self, soup: BeautifulSoup) -> List[str]:
        """
        Extract trim names from table headers - KEEP ORIGINAL NAMES
        """
        trim_names = []

        try:
            # Find all header cells (th elements)
            headers = soup.select("#compare-trim-tables thead tr th")

            if not headers:
                logger.warning("No table headers found")
                return []

            # Skip first two columns (icon and spec name)
            for th in headers[2:]:
                text = th.get_text(" ", strip=True)  # Use space instead of newline

                # Skip empty headers
                if not text or text.isspace():
                    continue

                # Clean up whitespace but keep original text
                text = ' '.join(text.split())

                # Only add if not a "See Pricing" button
                if "See Pricing" not in text and "See Cars" not in text:
                    trim_names.append(text)
                else:
                    logger.debug(f"Skipping button text: {text}")

            logger.debug(f"Extracted {len(trim_names)} raw trim names")
            return trim_names

        except Exception as e:
            logger.error(f"Error extracting trim names: {e}")
            return []

    def _clean_spec_name(self, spec_name: str) -> str:
        """Clean and standardize specification names"""
        if not spec_name:
            return ""

        # Remove extra whitespace
        spec_name = ' '.join(spec_name.split())

        # Remove common prefixes/suffixes
        spec_name = re.sub(r'^\d+\.\s*', '', spec_name)  # Remove numbering
        spec_name = re.sub(r'\([^)]*\)', '', spec_name)  # Remove parentheses content
        spec_name = re.sub(r'\[[^\]]*\]', '', spec_name)  # Remove bracket content

        # Standardize common terms
        replacements = {
            'MPG': 'Miles Per Gallon',
            'hp': 'Horsepower',
            'lb-ft': 'Torque',
            'lbs': 'Pounds',
            'in.': 'Inches',
            'ft': 'Feet',
            'gal': 'Gallons',
            'L': 'Liters',
            'cyl': 'Cylinders',
            'A/T': 'Automatic Transmission',
            'M/T': 'Manual Transmission',
            'CVT': 'Continuously Variable Transmission'
        }

        for short, long in replacements.items():
            spec_name = spec_name.replace(short, long)

        return spec_name.strip()

    def _clean_value(self, value: str) -> str:
        """Clean and standardize values"""
        if not value:
            return ""

        value = value.strip()

        # Replace common placeholders
        if value in ['--', 'N/A', 'Not Available', '']:
            return ""

        # Remove extra spaces and normalize
        value = ' '.join(value.split())

        return value

    def _categorize_spec(self, spec_name: str) -> str:
        """Categorize specification based on keywords"""
        spec_lower = spec_name.lower()

        for category, keywords in self.spec_categories.items():
            if any(keyword in spec_lower for keyword in keywords):
                return category

        return 'other'

    def _extract_unit(self, spec_name: str) -> str:
        """Extract unit of measurement from spec name"""
        unit_patterns = {
            'hp': 'horsepower',
            'lb-ft': 'lb-ft',
            'mpg': 'mpg',
            'lbs': 'lbs',
            'in': 'inches',
            'ft': 'feet',
            'gal': 'gallons',
            'L': 'liters',
            'sec': 'seconds',
            'mph': 'mph'
        }

        for unit_key, unit_name in unit_patterns.items():
            if unit_key in spec_name.lower():
                return unit_name

        return ''

    def _is_numeric_value(self, value: str) -> bool:
        """Check if value appears to be numeric"""
        if not value:
            return False

        # Check for common numeric patterns
        patterns = [
            r'^\d+$',  # Integer
            r'^\d+\.\d+$',  # Decimal
            r'^\d+-\d+$',  # Range
            r'^\d+\s*(hp|mpg|lbs|in|ft|gal|L|sec|mph)',  # With units
        ]

        for pattern in patterns:
            if re.search(pattern, value, re.IGNORECASE):
                return True

        return False