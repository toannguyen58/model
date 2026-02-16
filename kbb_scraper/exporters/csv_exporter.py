"""
CSV exporter: flattens scraped data and appends to a single CSV file.
"""
import csv
import logging
import re
from pathlib import Path
from typing import Any, Dict, List

from kbb_scraper.parsers.value_parser import (
    parse_fuel_economy,
    parse_horsepower,
    parse_price,
    parse_torque,
    parse_volume,
    parse_weight,
)

logger = logging.getLogger(__name__)

# Labels that should be normalised before lookup
LABEL_ALIASES = {
    "Turning Circle": "Turning Diameter",
    "0 to 60": "0 - 60",
}

# Complete column schema — spec columns followed by feature columns.
# Feature columns match the curated set from Audi_A3_eda.csv.
# No dynamic feature columns are added; unlisted columns are ignored.
FIXED_COLUMNS = [
    # --- identity & spec columns ---
    "make", "model", "year", "bodytype", "trim",
    "price",
    "mpg_city", "mpg_hwy", "mpg_comb",
    "Fuel Type", "hp", "Engine",
    "torque_lbft", "cargo_cuft",
    "0 - 60",
    "curb_weight_lbs",
    "Drivetrain", "Transmission Type", "Recommended Fuel", "Fuel Capacity",
    "Wheel Base", "Overall Length", "Front Head Room", "Front Leg Room",
    "Front Shoulder Room", "Width with mirrors", "Turning Diameter",
    # --- feature columns (Standard / Optional / Not Available) ---
    "Blind-Spot Alert", "Collision Warning System",
    "Child Seat Anchors", "Child Door Locks",
    "Traction Control", "Bluetooth Wireless Technology",
    "Cruise Control", "Remote Keyless Entry", "Remote Engine Start",
    "Smartphone Interface", "Internet Access", "Navigation System",
    "Voice Recognition System", "Real-Time Traffic Information",
    "Hands Free Phone", "Premium Radio", "Bluetooth Streaming Audio",
    "Satellite Radio", "Remote Control Liftgate/Trunk Release",
    "Heated Mirrors", "Leather Seats", "Folding Rear Seat",
    "Dual Power Front Seats", "Power Driver's Seat",
    "Leather-Wrapped Steering Wheel", "Power Outlet", "Power Windows",
    "Rear Window Defroster", "Steering Wheel Controls",
    "Tilt Steering Wheel", "Tilt/Telescoping Steering Wheel",
    "Cup Holder Count", "Alloy Wheels", "Fog Lights",
    "Power Folding Exterior Mirrors", "Rear Spoiler",
    "Rain Sensing Windshield Wipers", "Alarm System",
    "Dual-Clutch Automatic Transmission", "Hill Start Assist",
    "Stability Control",
]

FIXED_SET = set(FIXED_COLUMNS)

# Labels that are known to be intentionally unmapped (not warnings)
_KNOWN_UNMAPPED = {
    'specifications', 'features', 'compare', 'save', 'see pricing', '',
    'fair market price', 'horsepower', 'torque', 'cargo volume',
    'curb weight', 'fuel economy',
}
_WARNED_LABELS: set = set()  # module-level dedup so each label warns once

# Detect labels that are actually trim names rather than spec/feature names.
# Trim names contain body-style suffixes like "Sedan 4D", "Coupe 2D", etc.
_TRIM_NAME_RE = re.compile(
    r'(Sedan|Coupe|Convertible|Hatchback|Wagon|SUV|Cab|Van|Truck)\s+\d+D\b',
    re.IGNORECASE,
)

# Labels whose raw string is NOT in the schema but whose parsed numeric IS.
# The raw value is consumed by the parser but not written to the row.
_PARSED_ONLY = {
    "Fair Market Price": ("price", parse_price),
    "Horsepower":        ("hp", parse_horsepower),
    "Torque":            ("torque_lbft", parse_torque),
    "Cargo Volume":      ("cargo_cuft", parse_volume),
    "Curb Weight":       ("curb_weight_lbs", parse_weight),
}


def _is_trim_name(label: str) -> bool:
    """Return True if *label* looks like a vehicle trim name."""
    return bool(_TRIM_NAME_RE.search(label))


class CsvExporter:
    """Flatten one scrape result and append it to a single CSV file."""

    def __init__(self, csv_path: Path):
        self.csv_path = csv_path

    # ------------------------------------------------------------------
    # public
    # ------------------------------------------------------------------

    def export(self, data: Dict[str, Any]) -> None:
        """Flatten *data* (one scrape_car_model result) and append to CSV."""
        rows = self.flatten_one_scrape(data)
        if rows:
            self.append_to_csv(rows)

    # ------------------------------------------------------------------
    # flatten
    # ------------------------------------------------------------------

    def flatten_one_scrape(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert the nested scrape dict into a list of flat row dicts.

        Only columns present in FIXED_COLUMNS are written.
        """
        make = data.get("make", "")
        model = data.get("model", "")
        year = data.get("year", "")
        bodytypes: Dict[str, Any] = data.get("bodytypes", {})

        rows: List[Dict[str, Any]] = []

        for bodytype, bt_data in bodytypes.items():
            trim_names: List[str] = bt_data.get("trim_names", [])
            specs: List[Dict[str, Any]] = bt_data.get("specifications", [])

            if not trim_names:
                continue

            # Build per-label lookup (first occurrence wins for duplicates)
            seen_labels: set = set()
            label_values: List[tuple] = []  # (normalised_label, values)
            for spec in specs:
                raw_label = spec.get("label", "")
                label = LABEL_ALIASES.get(raw_label, raw_label)
                if label in seen_labels:
                    continue
                # Reject labels that are actually trim names (transposed data)
                if _is_trim_name(label):
                    logger.warning(f"Skipping trim-name label: {label}")
                    continue
                seen_labels.add(label)
                label_values.append((label, spec.get("values", [])))

            num_trims = len(trim_names)
            for trim_idx in range(num_trims):
                row: Dict[str, Any] = {
                    "make": make,
                    "model": model,
                    "year": year,
                    "bodytype": bodytype,
                    "trim": trim_names[trim_idx],
                }

                for label, values in label_values:
                    val = values[trim_idx] if trim_idx < len(values) else ""

                    if label in _PARSED_ONLY:
                        # Raw string not in schema; write only the parsed column
                        col, parser = _PARSED_ONLY[label]
                        row[col] = parser(val)
                    elif label == "Fuel Economy":
                        # Special: one raw label → three parsed columns
                        city, hwy, comb = parse_fuel_economy(val)
                        row["mpg_city"] = city
                        row["mpg_hwy"] = hwy
                        row["mpg_comb"] = comb
                    elif label in FIXED_SET:
                        # Raw label IS in the schema — write as-is
                        row[label] = val
                    else:
                        # Label is NOT in schema — warn once per label
                        if label.lower() not in _KNOWN_UNMAPPED and label not in _WARNED_LABELS:
                            _WARNED_LABELS.add(label)
                            logger.warning(
                                f"Unmapped spec label ignored: '{label}' "
                                f"(KBB may have changed their schema)"
                            )

                rows.append(row)

        return rows

    # ------------------------------------------------------------------
    # CSV I/O
    # ------------------------------------------------------------------

    # Key columns that uniquely identify a row
    _DEDUP_KEYS = ("make", "model", "year", "bodytype", "trim")

    def _load_existing_keys(self) -> set:
        """Load existing (make, model, year, bodytype, trim) tuples from CSV."""
        keys: set = set()
        if not self.csv_path.exists():
            return keys
        try:
            with open(self.csv_path, "r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    key = tuple(row.get(k, "") for k in self._DEDUP_KEYS)
                    keys.add(key)
        except Exception as e:
            logger.warning(f"Could not read existing CSV for dedup: {e}")
        return keys

    def append_to_csv(self, rows: List[Dict[str, Any]]) -> None:
        """Append *rows* to the CSV file, skipping duplicates."""
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)

        existing_keys = self._load_existing_keys()
        new_rows = []
        skipped = 0

        for row in rows:
            key = tuple(row.get(k, "") for k in self._DEDUP_KEYS)
            if key in existing_keys:
                skipped += 1
                continue
            existing_keys.add(key)
            new_rows.append(row)

        if skipped:
            logger.info(f"Skipped {skipped} duplicate row(s)")

        if not new_rows:
            logger.info("No new rows to append (all duplicates)")
            return

        file_exists = self.csv_path.exists()
        with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f, fieldnames=FIXED_COLUMNS, extrasaction="ignore"
            )
            if not file_exists:
                writer.writeheader()
            for row in new_rows:
                writer.writerow(row)

        logger.info(f"Appended {len(new_rows)} rows to {self.csv_path}")
