"""
Data models for 4-table database schema.

Tables:
- vehicle: Core vehicle identification
- vehicle_specs: Numeric specifications
- vehicle_features: Boolean features
- vehicle_scores: Rating scores (placeholder - not scraped)
"""
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
import json


@dataclass
class Vehicle:
    """Core vehicle identification table."""
    vehicle_id: int
    brand: str
    model: str
    year: int
    trim: str
    body_type: str
    fuel_type: Optional[str] = None
    drivetrain: Optional[str] = None
    transmission: Optional[str] = None
    engine: Optional[str] = None
    msrp: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class VehicleSpecs:
    """Numeric specifications table."""
    vehicle_id: int
    horsepower: Optional[int] = None
    torque: Optional[int] = None
    zero_to_sixty: Optional[float] = None
    top_speed: Optional[int] = None
    mpg_city: Optional[int] = None
    mpg_highway: Optional[int] = None
    mpg_combined: Optional[int] = None
    curb_weight: Optional[int] = None
    wheelbase: Optional[float] = None
    cargo_space: Optional[float] = None
    towing_capacity: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class VehicleFeatures:
    """Boolean features table."""
    vehicle_id: int
    leather_seats: Optional[bool] = None
    heated_seats: Optional[bool] = None
    heated_rear_seats: Optional[bool] = None
    ambient_lighting: Optional[bool] = None
    adaptive_headlights: Optional[bool] = None
    panorama_roof: Optional[bool] = None
    navigation: Optional[bool] = None
    parking_assist: Optional[bool] = None
    premium_audio: Optional[bool] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class VehicleScores:
    """Rating scores table (placeholder - not scraped)."""
    vehicle_id: int
    interior_quality: Optional[int] = None
    sporty_design: Optional[int] = None
    prestige: Optional[int] = None
    performance: Optional[int] = None
    market_value: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class FourTableDataset:
    """Container for all 4 tables of vehicle data."""
    vehicles: List[Vehicle] = field(default_factory=list)
    specs: List[VehicleSpecs] = field(default_factory=list)
    features: List[VehicleFeatures] = field(default_factory=list)
    scores: List[VehicleScores] = field(default_factory=list)

    def add_vehicle(self, vehicle: Vehicle, specs: VehicleSpecs,
                    features: VehicleFeatures, scores: VehicleScores):
        """Add a complete vehicle record across all tables."""
        self.vehicles.append(vehicle)
        self.specs.append(specs)
        self.features.append(features)
        self.scores.append(scores)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with table structure for JSON export."""
        return {
            "vehicle": {
                "table_name": "vehicle",
                "records": [v.to_dict() for v in self.vehicles]
            },
            "vehicle_specs": {
                "table_name": "vehicle_specs",
                "records": [s.to_dict() for s in self.specs]
            },
            "vehicle_features": {
                "table_name": "vehicle_features",
                "records": [f.to_dict() for f in self.features]
            },
            "vehicle_scores": {
                "table_name": "vehicle_scores",
                "records": [s.to_dict() for s in self.scores]
            }
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    def get_table(self, table_name: str) -> Dict[str, Any]:
        """Get a single table by name."""
        tables = self.to_dict()
        return tables.get(table_name, {})

    def __len__(self) -> int:
        """Return number of vehicles in dataset."""
        return len(self.vehicles)
