"""
Configuration settings for KBB Research Scraper - UV compatible
"""


import sys
from pathlib import Path
# Get the package root directory (where pyproject.toml is)
if __name__ == "__main__":
    # Running as script
    BASE_DIR = Path(__file__).resolve().parent.parent
else:
    # Running as module/package
    BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Data directories
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
CSV_DATA_DIR = DATA_DIR / "csv"
LOGS_DIR = BASE_DIR / "logs"
SCRIPTS_DIR = BASE_DIR / "scripts"

# Create directories
for directory in [RAW_DATA_DIR, PROCESSED_DATA_DIR, CSV_DATA_DIR, LOGS_DIR, SCRIPTS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# KBB URL configuration
KBB_BASE_URL = "https://www.kbb.com"
KBB_SPECS_URL_TEMPLATE = "{make}/{model}/{year}/specs/"

# Body type categories (mapping KBB names to standardized names)
BODY_TYPE_MAPPING = {
    'sedan': ['sedan', 'sedans'],
    'suv': ['suv', 'suvs', 'crossover', 'crossovers'],
    'wagon': ['wagon', 'wagons'],
    'coupe': ['coupe', 'coupes'],
    'convertible': ['convertible', 'convertibles'],
    'hatchback': ['hatchback', 'hatchbacks'],
    'truck': ['truck', 'pickup', 'pickups'],
    'van': ['van', 'minivan', 'vans', 'minivans'],
    'hybrid': ['hybrid', 'hev'],
    'electric': ['electric', 'ev', 'bev'],
    'default': ['default', 'standard']
}

# Database schema categories (for research organization)
SPEC_CATEGORIES = {
    'identification': ['Year', 'Make', 'Model', 'Trim', 'Body Style'],
    'engine': ['Engine', 'Horsepower', 'Torque', 'Cylinders', 'Displacement'],
    'fuel_efficiency': ['MPG City', 'MPG Highway', 'MPG Combined', 'Fuel Type', 'Fuel Tank Capacity'],
    'performance': ['Transmission', 'Drivetrain', '0-60 MPH', 'Top Speed'],
    'dimensions': ['Length', 'Width', 'Height', 'Wheelbase', 'Curb Weight'],
    'capacity': ['Seating', 'Cargo Capacity', 'Towing Capacity'],
    'features': ['Safety Features', 'Technology', 'Comfort', 'Entertainment'],
    'pricing': ['MSRP', 'Invoice', 'Resale Value', 'Price Range']
}

# Selenium settings
SELENIUM_CONFIG = {
    'implicit_wait': 10,
    'explicit_wait': 15,
    'page_load_timeout': 30,
    'headless': True,  # Set to False for debugging
    'chrome_options': [
        '--headless=new',  # Use new headless mode
        '--no-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu',
        '--window-size=1920,1080',
        '--disable-blink-features=AutomationControlled',
        '--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    ]
}

# Logging configuration
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
        'verbose': {
            'format': '%(asctime)s [%(levelname)s] %(name)s:%(lineno)d: %(message)s'
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': LOGS_DIR / 'scraper.log',
            'formatter': 'standard',
            'encoding': 'utf-8',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
            'stream': sys.stdout,
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': LOGS_DIR / 'errors.log',
            'formatter': 'verbose',
            'encoding': 'utf-8',
        },
    },
    'loggers': {
        'kbb_scraper': {
            'handlers': ['file', 'console', 'error_file'],
            'level': 'INFO',
            'propagate': False
        },
        'selenium': {
            'handlers': ['file'],
            'level': 'WARNING',
            'propagate': False
        },
        'webdriver_manager': {
            'handlers': ['file'],
            'level': 'WARNING',
            'propagate': False
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    }
}

# Research specific settings
RESEARCH_CONFIG = {
    'save_individual_bodytypes': True,
    'save_combined_data': True,
    'data_format': 'csv',  # or 'json', 'parquet'
    'include_timestamp': True,
    'max_retries': 3,
    'delay_between_requests': 2,  # seconds
    'request_timeout': 30,
    'cache_enabled': True,
    'cache_expiry_hours': 24,
}

# Cache settings
CACHE_CONFIG = {
    'enabled': True,
    'directory': BASE_DIR / '.cache' / 'kbb_scraper',
    'max_size_mb': 100,
    'expiry_days': 7,
}

# Add cache directory
CACHE_CONFIG['directory'].mkdir(parents=True, exist_ok=True)