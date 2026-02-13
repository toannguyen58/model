"""
Helper functions for the scraper
"""
import logging
import time
import random
from typing import List, Dict, Any
from pathlib import Path

def setup_logging():
    """Setup logging configuration"""
    import logging.config
    from kbb_scraper.config import settings

    logging.config.dictConfig(settings.LOGGING_CONFIG)
    return logging.getLogger('kbb_scraper')

def delay_random(min_seconds: float = 1, max_seconds: float = 3):
    """Random delay to avoid detection"""
    delay = random.uniform(min_seconds, max_seconds)
    time.sleep(delay)

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe saving"""
    import re

    # Remove invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)

    # Remove multiple underscores
    filename = re.sub(r'_+', '_', filename)

    # Limit length
    if len(filename) > 200:
        filename = filename[:200]

    return filename.strip('._ ')

def extract_car_info_from_url(url: str) -> Dict[str, str]:
    """Extract make, model, year from KBB URL"""
    import re

    pattern = r'/([^/]+)/([^/]+)/(\d{4})/specs/'
    match = re.search(pattern, url)

    if match:
        return {
            'make': match.group(1).replace('-', ' ').title(),
            'model': match.group(2).replace('-', ' ').title(),
            'year': match.group(3)
        }

    return {}

def validate_data(data: Dict[str, Any]) -> bool:
    """Validate scraped data has minimum required fields"""
    required = ['make', 'model', 'year']

    for field in required:
        if field not in data or not data[field]:
            return False

    # Check if we have any actual data
    if 'bodytypes' in data:
        if not data['bodytypes']:
            return False
        for bodytype_data in data['bodytypes'].values():
            if 'specifications' not in bodytype_data or not bodytype_data['specifications']:
                return False
    elif 'data' in data:
        if not data['data']:
            return False

    return True

def get_file_size(filepath: Path) -> str:
    """Get human readable file size"""
    size = filepath.stat().st_size

    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0

    return f"{size:.2f} TB"