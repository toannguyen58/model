"""
KBB Research Scraper - A package for scraping car specifications from Kelley Blue Book.

Main components:
    - KBBResearchScraper: Main scraper class for extracting data from KBB
    - SchemaTransformer: Transforms raw scraped data into normalized 4-table format
    - DatabaseExporter: Exports transformed data to JSON files

Usage:
    from kbb_scraper import KBBResearchScraper, SchemaTransformer, DatabaseExporter

    # Scrape data
    scraper = KBBResearchScraper(headless=True)
    data = scraper.scrape_car_model("Toyota", "Camry", "2020")
    scraper.close()

    # Transform to normalized schema
    transformer = SchemaTransformer()
    dataset = transformer.transform(data, "Toyota", "Camry", "2020")

    # Export to files
    exporter = DatabaseExporter("output/")
    exporter.export(dataset, "Toyota", "Camry", "2020")
"""

__version__ = "1.0.0"
__author__ = "eric5805"

# Core scraping components
from .scrapers.kbb_scraper import KBBResearchScraper
from .scrapers.bodytype_detector import BodyTypeDetector
from .scrapers.reviews_scraper import KBBReviewsScraper
from .drivers import DriverManager

# Data models
from .models.car_specs import CarModelData, BodyTypeData
from .models.db_schema import (
    Vehicle,
    VehicleSpecs,
    VehicleFeatures,
    VehicleScores,
    FourTableDataset,
)
from .models.review_data import ConsumerReview, ExpertReview, ReviewData

# Data transformation and export
from .transformers import SchemaTransformer
from .exporters import DatabaseExporter, CsvExporter

# Utilities
from .utils.file_handler import DataSaver

# Legacy export (not used internally but available for external use)
from .parsers.data_parser import KBBDataParser

__all__ = [
    # Core scraping
    "KBBResearchScraper",
    "BodyTypeDetector",
    "KBBReviewsScraper",
    "DriverManager",
    # Data models
    "CarModelData",
    "BodyTypeData",
    "Vehicle",
    "VehicleSpecs",
    "VehicleFeatures",
    "VehicleScores",
    "FourTableDataset",
    "ConsumerReview",
    "ExpertReview",
    "ReviewData",
    # Transformation & Export
    "SchemaTransformer",
    "DatabaseExporter",
    "CsvExporter",
    # Utilities
    "DataSaver",
    # Legacy (for external use)
    "KBBDataParser",
]
