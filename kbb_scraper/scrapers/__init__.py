"""
Web scrapers for KBB data extraction.
"""
from .kbb_scraper import KBBResearchScraper
from .bodytype_detector import BodyTypeDetector
from .reviews_scraper import KBBReviewsScraper

__all__ = ["KBBResearchScraper", "BodyTypeDetector", "KBBReviewsScraper"]
