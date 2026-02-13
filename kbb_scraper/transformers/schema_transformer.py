"""
Schema transformer for converting raw KBB data to 4-table database schema.
"""
import logging
from typing import Dict, Any, List, Optional

from ..models.db_schema import (
    Vehicle, VehicleSpecs, VehicleFeatures, VehicleScores, FourTableDataset
)
from ..parsers.value_parser import (
    parse_horsepower, parse_torque, parse_zero_to_sixty, parse_top_speed,
    parse_fuel_economy, parse_weight, parse_dimension, parse_volume,
    parse_price, feature_to_bool, generate_vehicle_id, clean_trim_name
)

logger = logging.getLogger(__name__)


class SchemaTransformer:
    """
    Transforms raw KBB scraped data into 4-table database schema format.

    Handles:
    - Spec name mapping with typo correction
    - Value parsing and type conversion
    - Duplicate spec handling (uses first occurrence)
    """

    # Mapping from spec names (including typos) to vehicle fields
    VEHICLE_SPEC_MAP = {
        "fair market price": "msrp",
        "fuel type": "fuel_type",
        "drivetrain": "drivetrain",
        "transmission type": "transmission",
        "engine": "engine",
    }

    # Mapping from spec names to vehicle_specs fields
    SPECS_MAP = {
        "horsepower": "horsepower",
        "torque": "torque",
        "0 - 60": "zero_to_sixty",
        "0 to 60": "zero_to_sixty",
        "0-60": "zero_to_sixty",
        "top speed": "top_speed",
        "fuel economy": "fuel_economy",  # Special handling for city/hwy/combined
        "curb weight": "curb_weight",
        "wheel base": "wheelbase",
        "wheelbase": "wheelbase",
        "cargo volume": "cargo_space",
        "towing capacity": "towing_capacity",
    }

    # Mapping from spec names (including typos) to vehicle_features fields
    FEATURES_MAP = {
        # Leather seats - with typo handling
        "leather seats": "leather_seats",
        "literseather seats": "leather_seats",  # Common OCR/scrape typo
        # Heated seats
        "heated seats": "heated_seats",
        "heated front seats": "heated_seats",
        # Heated rear seats
        "heated rear seats": "heated_rear_seats",
        # Ambient lighting
        "ambient lighting": "ambient_lighting",
        "interior ambient lighting": "ambient_lighting",
        # Adaptive headlights
        "adaptive headlights": "adaptive_headlights",
        "adaptive front headlights": "adaptive_headlights",
        # Panorama roof
        "panorama moon roof": "panorama_roof",
        "panoramic moon roof": "panorama_roof",
        "panorama roof": "panorama_roof",
        "panoramic roof": "panorama_roof",
        "moonroof": "panorama_roof",
        "moon roof": "panorama_roof",
        "sunroof": "panorama_roof",
        # Navigation
        "navigation system": "navigation",
        "navigation": "navigation",
        "gps navigation": "navigation",
        # Parking assist
        "parking assist": "parking_assist",
        "park assist": "parking_assist",
        "parking sensors": "parking_assist",
        "rear parking sensors": "parking_assist",
        # Premium audio
        "premium radio": "premium_audio",
        "premium audio": "premium_audio",
        "premium sound": "premium_audio",
        "premium sound system": "premium_audio",
    }

    def __init__(self):
        self.processed_specs = set()

    def transform(self, raw_data: Dict[str, Any], make: str, model: str, year: str) -> FourTableDataset:
        """
        Transform raw scraped data into FourTableDataset.

        Args:
            raw_data: Dictionary containing 'bodytypes' with scraped data
            make: Vehicle make (e.g., "Audi")
            model: Vehicle model (e.g., "A3")
            year: Vehicle year (e.g., "2017")

        Returns:
            FourTableDataset containing all transformed vehicle data
        """
        dataset = FourTableDataset()

        if 'bodytypes' not in raw_data:
            logger.warning("No 'bodytypes' key in raw data")
            return dataset

        for body_type, bodytype_data in raw_data['bodytypes'].items():
            if not isinstance(bodytype_data, dict):
                continue

            self._transform_bodytype(
                dataset, bodytype_data, make, model, year, body_type
            )

        logger.info(f"Transformed {len(dataset)} vehicles to 4-table schema")
        return dataset

    def transform_single_bodytype(self, bodytype_data: Dict[str, Any],
                                   make: str, model: str, year: str,
                                   body_type: str) -> FourTableDataset:
        """
        Transform a single body type's raw data.

        Args:
            bodytype_data: Dictionary with 'specifications' and 'trim_names'
            make: Vehicle make
            model: Vehicle model
            year: Vehicle year
            body_type: Body type (e.g., "Sedan")

        Returns:
            FourTableDataset containing transformed data for this body type
        """
        dataset = FourTableDataset()
        self._transform_bodytype(dataset, bodytype_data, make, model, year, body_type)
        return dataset

    def _transform_bodytype(self, dataset: FourTableDataset,
                            bodytype_data: Dict[str, Any],
                            make: str, model: str, year: str,
                            body_type: str):
        """Transform a single body type and add to dataset."""
        specifications = bodytype_data.get('specifications', [])
        trim_names = bodytype_data.get('trim_names', [])
        tab_name = bodytype_data.get('tab_name', body_type)

        if not specifications or not trim_names:
            logger.warning(f"No specifications or trim names for {body_type}")
            return

        # Build lookup: spec_name -> {trim_index: value}
        spec_lookup = self._build_spec_lookup(specifications, len(trim_names))

        # Process each trim
        for trim_idx, raw_trim_name in enumerate(trim_names):
            trim_name = clean_trim_name(raw_trim_name)

            # Generate vehicle ID
            vehicle_id = generate_vehicle_id(
                make, model, int(year), trim_name, tab_name
            )

            # Create vehicle record
            vehicle = self._create_vehicle(
                vehicle_id, make, model, int(year), trim_name,
                tab_name, spec_lookup, trim_idx
            )

            # Create specs record
            specs = self._create_specs(vehicle_id, spec_lookup, trim_idx)

            # Create features record
            features = self._create_features(vehicle_id, spec_lookup, trim_idx)

            # Create scores record (empty - not scraped)
            scores = VehicleScores(vehicle_id=vehicle_id)

            dataset.add_vehicle(vehicle, specs, features, scores)

    def _build_spec_lookup(self, specifications: List[Dict[str, Any]],
                           num_trims: int) -> Dict[str, List[str]]:
        """
        Build a lookup dictionary from spec name to list of values by trim index.

        Uses first occurrence for duplicate spec names.
        """
        lookup = {}
        seen_specs = set()

        for spec in specifications:
            spec_name = spec.get('label', spec.get('spec_name', '')).strip().lower()
            values = spec.get('values', [])

            # Skip if already seen (use first occurrence)
            if spec_name in seen_specs:
                continue
            seen_specs.add(spec_name)

            # Pad or truncate values to match number of trims
            if len(values) < num_trims:
                values = values + [''] * (num_trims - len(values))
            elif len(values) > num_trims:
                values = values[:num_trims]

            lookup[spec_name] = values

        return lookup

    def _get_spec_value(self, spec_lookup: Dict[str, List[str]],
                        spec_name: str, trim_idx: int) -> Optional[str]:
        """Get a spec value for a given trim, returning None if not found."""
        values = spec_lookup.get(spec_name.lower())
        if values and trim_idx < len(values):
            val = values[trim_idx]
            return val if val else None
        return None

    def _create_vehicle(self, vehicle_id: int, make: str, model: str, year: int,
                        trim: str, body_type: str, spec_lookup: Dict[str, List[str]],
                        trim_idx: int) -> Vehicle:
        """Create a Vehicle record."""
        # Get values from spec lookup
        msrp_str = self._get_spec_value(spec_lookup, "fair market price", trim_idx)
        fuel_type = self._get_spec_value(spec_lookup, "fuel type", trim_idx)
        drivetrain = self._get_spec_value(spec_lookup, "drivetrain", trim_idx)
        transmission = self._get_spec_value(spec_lookup, "transmission type", trim_idx)
        engine = self._get_spec_value(spec_lookup, "engine", trim_idx)

        # Parse MSRP
        msrp = parse_price(msrp_str) if msrp_str else None

        return Vehicle(
            vehicle_id=vehicle_id,
            brand=make,
            model=model,
            year=year,
            trim=trim,
            body_type=body_type,
            fuel_type=fuel_type,
            drivetrain=drivetrain,
            transmission=transmission,
            engine=engine,
            msrp=msrp
        )

    def _create_specs(self, vehicle_id: int, spec_lookup: Dict[str, List[str]],
                      trim_idx: int) -> VehicleSpecs:
        """Create a VehicleSpecs record."""
        # Parse horsepower
        hp_str = self._get_spec_value(spec_lookup, "horsepower", trim_idx)
        horsepower = parse_horsepower(hp_str) if hp_str else None

        # Parse torque
        torque_str = self._get_spec_value(spec_lookup, "torque", trim_idx)
        torque = parse_torque(torque_str) if torque_str else None

        # Parse 0-60 (try multiple variations)
        zero_to_sixty = None
        for spec_name in ["0 - 60", "0 to 60", "0-60"]:
            zts_str = self._get_spec_value(spec_lookup, spec_name, trim_idx)
            if zts_str:
                zero_to_sixty = parse_zero_to_sixty(zts_str)
                break

        # Parse top speed
        ts_str = self._get_spec_value(spec_lookup, "top speed", trim_idx)
        top_speed = parse_top_speed(ts_str) if ts_str else None

        # Parse fuel economy
        fe_str = self._get_spec_value(spec_lookup, "fuel economy", trim_idx)
        mpg_city, mpg_highway, mpg_combined = parse_fuel_economy(fe_str) if fe_str else (None, None, None)

        # Parse curb weight
        cw_str = self._get_spec_value(spec_lookup, "curb weight", trim_idx)
        curb_weight = parse_weight(cw_str) if cw_str else None

        # Parse wheelbase
        wb_str = None
        for spec_name in ["wheel base", "wheelbase"]:
            wb_str = self._get_spec_value(spec_lookup, spec_name, trim_idx)
            if wb_str:
                break
        wheelbase = parse_dimension(wb_str) if wb_str else None

        # Parse cargo space
        cargo_str = self._get_spec_value(spec_lookup, "cargo volume", trim_idx)
        cargo_space = parse_volume(cargo_str) if cargo_str else None

        # Parse towing capacity
        tow_str = self._get_spec_value(spec_lookup, "towing capacity", trim_idx)
        towing_capacity = parse_weight(tow_str) if tow_str else None

        return VehicleSpecs(
            vehicle_id=vehicle_id,
            horsepower=horsepower,
            torque=torque,
            zero_to_sixty=zero_to_sixty,
            top_speed=top_speed,
            mpg_city=mpg_city,
            mpg_highway=mpg_highway,
            mpg_combined=mpg_combined,
            curb_weight=curb_weight,
            wheelbase=wheelbase,
            cargo_space=cargo_space,
            towing_capacity=towing_capacity
        )

    def _create_features(self, vehicle_id: int, spec_lookup: Dict[str, List[str]],
                         trim_idx: int) -> VehicleFeatures:
        """Create a VehicleFeatures record."""
        # Helper to check multiple possible spec names
        def get_feature(possible_names: List[str]) -> Optional[bool]:
            for name in possible_names:
                val = self._get_spec_value(spec_lookup, name, trim_idx)
                if val:
                    return feature_to_bool(val)
            return None

        return VehicleFeatures(
            vehicle_id=vehicle_id,
            leather_seats=get_feature(["leather seats", "literseather seats"]),
            heated_seats=get_feature(["heated seats", "heated front seats"]),
            heated_rear_seats=get_feature(["heated rear seats"]),
            ambient_lighting=get_feature(["ambient lighting", "interior ambient lighting"]),
            adaptive_headlights=get_feature(["adaptive headlights", "adaptive front headlights"]),
            panorama_roof=get_feature([
                "panorama moon roof", "panoramic moon roof", "panorama roof",
                "panoramic roof", "moonroof", "moon roof", "sunroof"
            ]),
            navigation=get_feature(["navigation system", "navigation", "gps navigation"]),
            parking_assist=get_feature([
                "parking assist", "park assist", "parking sensors", "rear parking sensors"
            ]),
            premium_audio=get_feature([
                "premium radio", "premium audio", "premium sound", "premium sound system"
            ])
        )
