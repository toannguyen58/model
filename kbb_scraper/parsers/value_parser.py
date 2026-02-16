"""
Value parsing utilities for transforming raw KBB data into database-ready values.

Transforms strings like "220 @ 4500 RPM" -> 220, "$9,325" -> 9325, etc.
"""
import re
import hashlib
from typing import Optional, Tuple


def parse_horsepower(value: str) -> Optional[int]:
    """
    Parse horsepower from strings like "220 @ 4500 RPM" or "220".

    Returns the horsepower as an integer, or None if parsing fails.
    """
    if not value:
        return None

    # Match pattern: number optionally followed by @ RPM info
    match = re.match(r'(\d+)', value.strip())
    if match:
        return int(match.group(1))
    return None


def parse_torque(value: str) -> Optional[int]:
    """
    Parse torque from strings like "258 lb-ft" or "258 @ 4500 RPM".

    Returns the torque as an integer, or None if parsing fails.
    """
    if not value:
        return None

    # Match pattern: number at start (optionally followed by lb-ft or @ RPM)
    match = re.match(r'(\d+)', value.strip())
    if match:
        return int(match.group(1))
    return None


def parse_zero_to_sixty(value: str) -> Optional[float]:
    """
    Parse 0-60 time from strings like "6.6 seconds" or "6.6 sec".

    Returns the time as a float, or None if parsing fails.
    """
    if not value:
        return None

    # Match pattern: decimal number followed by optional seconds/sec
    match = re.match(r'([\d.]+)\s*(?:seconds?|sec)?', value.strip(), re.IGNORECASE)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None


def parse_top_speed(value: str) -> Optional[int]:
    """
    Parse top speed from strings like "130 mph" or "130".

    Returns the speed as an integer, or None if parsing fails.
    """
    if not value:
        return None

    # Match pattern: number followed by optional mph
    match = re.match(r'(\d+)\s*(?:mph)?', value.strip(), re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def parse_fuel_economy(value: str) -> Tuple[Optional[int], Optional[int], Optional[int]]:
    """
    Parse fuel economy from strings like "City 26/Hwy 35/Comb 29 MPG".

    Also handles electric vehicle formats:
      - "City 131/Hwy 117/Comb 124 MPGe"
      - "100 MPGe"
      - "28 kWh/100 mi"  (converted: 3,412 / kWh * 100 ≈ MPGe)
      - "258 mi range" (stored as combined only)

    Returns a tuple of (city, highway, combined) as integers.
    Any unparseable value returns None in that position.
    """
    if not value:
        return (None, None, None)

    city, highway, combined = None, None, None

    # Pattern 1: "City XX/Hwy YY/Comb ZZ MPG(e)"
    city_match = re.search(r'City\s*(\d+)', value, re.IGNORECASE)
    hwy_match = re.search(r'Hwy\s*(\d+)', value, re.IGNORECASE)
    comb_match = re.search(r'Comb(?:ined)?\s*(\d+)', value, re.IGNORECASE)

    if city_match:
        city = int(city_match.group(1))
    if hwy_match:
        highway = int(hwy_match.group(1))
    if comb_match:
        combined = int(comb_match.group(1))

    if city is not None or highway is not None or combined is not None:
        return (city, highway, combined)

    # Pattern 2: "XX MPGe" (electric equivalent)
    mpge_match = re.match(r'(\d+)\s*MPGe', value.strip(), re.IGNORECASE)
    if mpge_match:
        combined = int(mpge_match.group(1))
        return (None, None, combined)

    # Pattern 3: "XX kWh/100 mi" -> approximate MPGe (33.7 kWh per gallon-equivalent)
    kwh_match = re.match(r'([\d.]+)\s*kWh\s*/\s*100\s*mi', value.strip(), re.IGNORECASE)
    if kwh_match:
        kwh_per_100mi = float(kwh_match.group(1))
        if kwh_per_100mi > 0:
            combined = int(3370 / kwh_per_100mi)  # 33.7 kWh/gal * 100
            return (None, None, combined)

    # Pattern 4: Simple "XX MPG" (assume combined)
    simple_match = re.match(r'(\d+)\s*(?:mpg)\b', value.strip(), re.IGNORECASE)
    if simple_match:
        combined = int(simple_match.group(1))
        return (city, highway, combined)

    # Pattern 5: bare number (only if clearly numeric and reasonable for MPG)
    bare_match = re.match(r'^(\d+)$', value.strip())
    if bare_match:
        num = int(bare_match.group(1))
        if 5 <= num <= 200:
            combined = num

    return (city, highway, combined)


def parse_weight(value: str) -> Optional[int]:
    """
    Parse weight from strings like "3197 pounds" or "3197 lbs".

    Returns the weight as an integer, or None if parsing fails.
    """
    if not value:
        return None

    # Match pattern: number followed by optional pounds/lbs
    match = re.match(r'([\d,]+)\s*(?:pounds?|lbs?)?', value.strip(), re.IGNORECASE)
    if match:
        # Remove commas from number
        num_str = match.group(1).replace(',', '')
        try:
            return int(num_str)
        except ValueError:
            return None
    return None


def parse_dimension(value: str) -> Optional[float]:
    """
    Parse dimension from strings like "103.8 inches" or "36.1 feet".

    Returns the dimension as a float in the original unit, or None if parsing fails.
    """
    if not value:
        return None

    # Match pattern: decimal number followed by optional unit
    match = re.match(r'([\d.]+)\s*(?:inches?|in\.?|feet|ft\.?)?', value.strip(), re.IGNORECASE)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None


def parse_volume(value: str) -> Optional[float]:
    """
    Parse volume from strings like "12.30 cu ft" or "13.2 gallons".

    Returns the volume as a float, or None if parsing fails.
    """
    if not value:
        return None

    # Match pattern: decimal number followed by optional unit
    match = re.match(r'([\d.]+)\s*(?:cu\.?\s*ft\.?|cubic\s*feet|gallons?|gal\.?)?',
                     value.strip(), re.IGNORECASE)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None


def parse_price(value: str) -> Optional[int]:
    """
    Parse price from strings like "$9,325" or "9325".

    Returns the price as an integer, or None if parsing fails.
    """
    if not value:
        return None

    # Remove $ and commas, then parse
    cleaned = re.sub(r'[$,]', '', value.strip())

    # Match number (possibly with decimal)
    match = re.match(r'([\d.]+)', cleaned)
    if match:
        try:
            # Convert to int (truncate any decimals)
            return int(float(match.group(1)))
        except ValueError:
            return None
    return None


def feature_to_bool(value: str) -> Optional[bool]:
    """
    Convert feature value to boolean.

    "Standard" -> True
    "Optional" -> True (feature is available)
    "" or empty -> None (unknown/not available)

    Returns True if feature is available, None otherwise.
    """
    if not value:
        return None

    value_lower = value.strip().lower()

    if value_lower == 'standard':
        return True
    elif value_lower == 'optional':
        return True  # Feature is available (optionally)
    else:
        return None


def generate_vehicle_id(brand: str, model: str, year: int, trim: str, body_type: str) -> int:
    """
    Generate a unique vehicle ID based on composite key.

    Creates a hash-based ID from brand, model, year, trim, and body_type.
    Returns a positive integer ID.
    """
    # Create composite key string
    key = f"{brand}|{model}|{year}|{trim}|{body_type}".lower()

    # Generate hash and convert to integer
    hash_bytes = hashlib.md5(key.encode()).digest()
    # Use first 8 bytes to create a positive integer
    vehicle_id = int.from_bytes(hash_bytes[:8], byteorder='big') & 0x7FFFFFFFFFFFFFFF

    return vehicle_id


def clean_trim_name(trim_name: str) -> str:
    """
    Clean trim name by removing prefixes like "Save X of Y".

    Example: "Save 1 of 3 A3 Prestige Sedan 4D" -> "A3 Prestige Sedan 4D"
    """
    if not trim_name:
        return ""

    # Remove "Save X of Y " prefix
    cleaned = re.sub(r'^Save\s+\d+\s+of\s+\d+\s+', '', trim_name.strip())

    return cleaned.strip()
