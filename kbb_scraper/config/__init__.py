"""
Configuration settings for KBB scraper.
"""
from . import settings
from .vehicles import (
    VEHICLES,
    VEHICLES_TEST,
    YEARS_TEST,
    get_all_vehicles,
    get_scrape_combinations,
    get_stats
)

__all__ = [
    "settings",
    "VEHICLES",
    "VEHICLES_TEST",
    "YEARS_TEST",
    "get_all_vehicles",
    "get_scrape_combinations",
    "get_stats"
]
