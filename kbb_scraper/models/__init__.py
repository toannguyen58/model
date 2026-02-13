"""
Data models for KBB scraper.
"""
from .car_specs import CarModelData, BodyTypeData, Specification, TrimSpecification
from .db_schema import Vehicle, VehicleSpecs, VehicleFeatures, VehicleScores, FourTableDataset
from .review_data import ConsumerReview, ExpertReview, ReviewData

__all__ = [
    "CarModelData",
    "BodyTypeData",
    "Specification",
    "TrimSpecification",
    "Vehicle",
    "VehicleSpecs",
    "VehicleFeatures",
    "VehicleScores",
    "FourTableDataset",
    "ConsumerReview",
    "ExpertReview",
    "ReviewData",
]
