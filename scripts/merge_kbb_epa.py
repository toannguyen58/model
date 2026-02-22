"""
Merge KBB and EPA vehicle datasets into a unified schema.

Steps:
  1. Restore original KBB data (remove naively appended EPA rows)
  2. Normalize fuel types and make names
  3. Extract base_model from EPA model names via tiered matching
  4. Smart merge: skip duplicates, append new powertrain variants & EPA-only vehicles
  5. Output sorted, unified CSV
"""

import pandas as pd
import re
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "csv"
KBB_EPA_PATH = DATA_DIR / "all_cars.csv"
EPA_PATH = DATA_DIR / "epa_alt_fuel_vehicles.csv"

# ---------------------------------------------------------------------------
# Make-name normalization (EPA -> KBB convention)
# ---------------------------------------------------------------------------
MAKE_NORM = {
    "Alfa Romeo": "Alfa-Romeo",
    "Land Rover": "Land-Rover",
    "MINI": "Mini",
}

# ---------------------------------------------------------------------------
# Fuel-type normalization
# ---------------------------------------------------------------------------
FUEL_NORM = {
    "HybridLeafIcon": "Hybrid",
    "ElectricLeafIcon": "Electric",
    "Flexible Fuel": "Flex-Fuel",
    "All-Electric": "Electric",
}

# ---------------------------------------------------------------------------
# Series mapping for luxury brands (Tier 3)
# ---------------------------------------------------------------------------
SERIES_MAP = {
    "BMW": {
        "1": "1-Series", "2": "2-Series", "3": "3-Series", "4": "4-Series",
        "5": "5-Series", "6": "6-Series", "7": "7-Series", "8": "8-Series",
    },
    "Mercedes-Benz": {
        "C": "C-Class", "E": "E-Class", "S": "S-Class",
        "A": "A-Class", "G": "G-Class",
    },
}

# Precompiled patterns for series extraction
# BMW: first digit (e.g. "330e" -> "3", "528i" -> "5")
BMW_RE = re.compile(r"^(\d)")
# Mercedes: leading letter(s) before digits (e.g. "C300" -> "C", "E350" -> "E", "S580" -> "S")
MERC_RE = re.compile(r"^([A-Z]+)(?=\d)")


def normalize_fuel(val):
    if pd.isna(val):
        return val
    return FUEL_NORM.get(val, val)


def normalize_make(val):
    if pd.isna(val):
        return val
    return MAKE_NORM.get(val, val)


def extract_base_model(epa_model, kbb_models_for_make):
    """
    Tiered matching of an EPA model name to a KBB base model.

    Args:
        epa_model: EPA model string (e.g. "RAV4 Hybrid", "330e xDrive")
        kbb_models_for_make: set of KBB model names for this make

    Returns:
        matched KBB base model, or the EPA model as-is (Tier 4)
    """
    if not kbb_models_for_make or pd.isna(epa_model):
        return epa_model

    epa_lower = epa_model.lower().replace("-", "")

    # Tier 1: exact match (hyphen-normalized)
    for km in kbb_models_for_make:
        if epa_lower == km.lower().replace("-", ""):
            return km

    # Tier 2: longest prefix match
    best_match = None
    best_len = 0
    for km in kbb_models_for_make:
        km_lower = km.lower().replace("-", "")
        # EPA model must start with KBB model name (word boundary)
        if epa_lower.startswith(km_lower):
            # Ensure match is at a word boundary (next char is space, end, or non-alpha for short models)
            rest = epa_model[len(km):]
            if rest == "" or rest[0] in (" ", "-", "/"):
                if len(km) > best_len:
                    best_len = len(km)
                    best_match = km
    if best_match:
        return best_match

    # Tier 2b: try without hyphen normalization on epa side too
    for km in kbb_models_for_make:
        if epa_model.startswith(km):
            rest = epa_model[len(km):]
            if rest == "" or rest[0] in (" ", "-", "/"):
                if len(km) > best_len:
                    best_len = len(km)
                    best_match = km
    if best_match:
        return best_match

    # Tier 4 (no match): return EPA model as-is
    return epa_model


def extract_series_model(make, epa_model, kbb_models_for_make):
    """Tier 3: series-based matching for BMW / Mercedes-Benz."""
    series_map = SERIES_MAP.get(make)
    if not series_map:
        return None

    if make == "BMW":
        m = BMW_RE.match(epa_model)
        if m:
            digit = m.group(1)
            series = series_map.get(digit)
            if series and series in kbb_models_for_make:
                return series
        # Also check direct KBB model matches (X1, X3, i3, i4, iX, Z4, M3, etc.)
        return None

    if make == "Mercedes-Benz":
        m = MERC_RE.match(epa_model)
        if m:
            prefix = m.group(1)
            series = series_map.get(prefix)
            if series and series in kbb_models_for_make:
                return series
        # Direct matches (GLA, GLC, GLE, GLS, GLB, CLA, CLS, SL, SLK)
        return None

    return None


def main():
    print("=" * 60)
    print("KBB + EPA Unified Merge")
    print("=" * 60)

    # ------------------------------------------------------------------
    # Step 1: Load and restore original KBB data
    # ------------------------------------------------------------------
    raw = pd.read_csv(KBB_EPA_PATH, low_memory=False)
    print(f"\nLoaded all_cars.csv: {len(raw)} rows")

    # Identify true KBB rows. KBB rows always have at least one KBB-specific
    # column populated (price, hp, bodytype, etc.), while EPA-appended rows
    # have NaN for all of them. This is robust across re-runs.
    KBB_ONLY_COLS = ["bodytype", "price", "hp", "torque_lbft", "cargo_cuft"]
    kbb_only_present = [c for c in KBB_ONLY_COLS if c in raw.columns]
    has_kbb_data = ~raw[kbb_only_present].isna().all(axis=1)

    if "data_source" in raw.columns:
        # Use KBB-specific columns to catch mislabeled rows from prior runs
        kbb = raw[has_kbb_data].copy()
    else:
        # First run: original file has null-trim EPA rows from naive concat
        kbb = raw[raw["trim"].notna()].copy()
    print(f"KBB rows: {len(kbb)}")

    # Drop columns that will be re-populated by the merge
    for col in ["engine_cylinders", "engine_volume", "extra_tech",
                "fuel_type", "base_model", "data_source"]:
        if col in kbb.columns:
            kbb.drop(columns=[col], inplace=True)

    # ------------------------------------------------------------------
    # Step 2: Load EPA data
    # ------------------------------------------------------------------
    epa = pd.read_csv(EPA_PATH)
    print(f"EPA rows: {len(epa)}")

    # ------------------------------------------------------------------
    # Normalize fuel types
    # ------------------------------------------------------------------
    kbb["Fuel Type"] = kbb["Fuel Type"].apply(normalize_fuel)
    epa["fuel_type"] = epa["fuel_type"].apply(normalize_fuel)

    # ------------------------------------------------------------------
    # Build KBB model lookup: {make: set(models)}
    # ------------------------------------------------------------------
    kbb_models = {}
    for make in kbb["make"].unique():
        kbb_models[make] = set(kbb[kbb["make"] == make]["model"].unique())

    # ------------------------------------------------------------------
    # Step 3: Normalize EPA makes and extract base_model
    # ------------------------------------------------------------------
    epa["brand"] = epa["brand"].apply(normalize_make)

    base_models = []
    for _, row in epa.iterrows():
        make = row["brand"]
        model = row["model"]
        models_set = kbb_models.get(make, set())

        # Try Tier 3 (series) first for BMW/Mercedes, then fall through to general
        series_match = extract_series_model(make, model, models_set)
        if series_match:
            base_models.append(series_match)
        else:
            base_models.append(extract_base_model(model, models_set))

    epa["base_model"] = base_models

    # ------------------------------------------------------------------
    # Step 4: Classify and merge
    # ------------------------------------------------------------------
    # Build KBB lookup keys
    kbb["fuel_type"] = kbb["Fuel Type"]
    kbb["base_model"] = kbb["model"]
    kbb["data_source"] = "kbb"

    # Key sets for matching
    kbb_keys_full = set(
        zip(kbb["make"], kbb["model"], kbb["year"], kbb["fuel_type"])
    )
    kbb_keys_model = set(
        zip(kbb["make"], kbb["model"], kbb["year"])
    )

    cat_a = []  # skip
    cat_b = []  # new powertrain variant
    cat_c = []  # EPA-only vehicle

    for idx, row in epa.iterrows():
        make = row["brand"]
        bm = row["base_model"]
        year = row["year"]
        fuel = row["fuel_type"]

        key_full = (make, bm, year, fuel)
        key_model = (make, bm, year)

        if key_full in kbb_keys_full:
            cat_a.append(idx)
        elif key_model in kbb_keys_model:
            cat_b.append(idx)
        else:
            cat_c.append(idx)

    print(f"\nMerge classification:")
    print(f"  Category A (skip, already in KBB): {len(cat_a)}")
    print(f"  Category B (new powertrain variant): {len(cat_b)}")
    print(f"  Category C (EPA-only vehicle):       {len(cat_c)}")

    # ------------------------------------------------------------------
    # Build EPA rows to append (Category B + C)
    # ------------------------------------------------------------------
    epa_append = epa.loc[cat_b + cat_c].copy()
    print(f"  EPA rows to append: {len(epa_append)}")

    # Map EPA columns to unified schema
    epa_unified = pd.DataFrame()
    epa_unified["make"] = epa_append["brand"]
    epa_unified["model"] = epa_append["base_model"]
    epa_unified["year"] = epa_append["year"]
    epa_unified["trim"] = epa_append["model"]  # Full EPA model name as trim
    epa_unified["Fuel Type"] = epa_append["fuel_type"]
    epa_unified["fuel_type"] = epa_append["fuel_type"]
    epa_unified["mpg_city"] = epa_append["mpg_city"]
    epa_unified["mpg_hwy"] = epa_append["mpg_hwy"]
    epa_unified["mpg_comb"] = epa_append["mpg_comb"]
    epa_unified["Drivetrain"] = epa_append["drivetrain"]
    epa_unified["Engine"] = epa_append["engine"]
    epa_unified["engine_cylinders"] = epa_append["engine_cylinders"]
    epa_unified["engine_volume"] = epa_append["engine_volume"]
    epa_unified["extra_tech"] = epa_append["extra_tech"]
    epa_unified["base_model"] = epa_append["base_model"]
    epa_unified["data_source"] = "epa"

    # ------------------------------------------------------------------
    # Step 5: Concat and output
    # ------------------------------------------------------------------
    merged = pd.concat([kbb, epa_unified], ignore_index=True)

    # Sort by (year, make, base_model, fuel_type, trim)
    merged.sort_values(
        by=["year", "make", "base_model", "fuel_type", "trim"],
        na_position="last",
        ignore_index=True,
        inplace=True,
    )

    # ------------------------------------------------------------------
    # Verification
    # ------------------------------------------------------------------
    print(f"\n{'=' * 60}")
    print("Verification")
    print(f"{'=' * 60}")
    print(f"Final row count: {len(merged)}")
    print(f"  KBB rows:      {len(kbb)}")
    print(f"  EPA appended:  {len(epa_append)}")
    print(f"Null trims: {merged['trim'].isna().sum()}")
    print(f"Null base_model: {merged['base_model'].isna().sum()}")

    fuel_vals = merged["Fuel Type"].dropna().unique()
    bad_fuels = [f for f in fuel_vals if f in ("HybridLeafIcon", "ElectricLeafIcon", "All-Electric", "Flexible Fuel")]
    print(f"Bad fuel types remaining: {bad_fuels if bad_fuels else 'None'}")

    sources = merged["data_source"].value_counts()
    print(f"Data sources:\n{sources.to_string()}")

    # Spot check: Toyota RAV4 2022
    rav4 = merged[
        (merged["make"] == "Toyota")
        & (merged["base_model"] == "RAV4")
        & (merged["year"] == 2022)
    ]
    print(f"\nSpot check - Toyota RAV4 2022 ({len(rav4)} rows):")
    print(rav4[["make", "model", "year", "trim", "Fuel Type", "data_source"]].to_string())

    # Write output
    merged.to_csv(KBB_EPA_PATH, index=False)
    print(f"\nWrote {len(merged)} rows to {KBB_EPA_PATH}")
    print("Done!")


if __name__ == "__main__":
    main()
