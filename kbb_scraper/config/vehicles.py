# kbb_scraper/config/vehicles.py
"""
Vehicle brands and models dictionary for KBB scraping.

Each model maps to (start_year, end_year) inclusive — the years the model
was available on kbb.com.  Models with production gaps (e.g. Ranger
2000-2011 then 2019-2024) use the full span; the scraper's existing 404
handler covers the gap years.
"""

# Outer-bound reference constants
YEAR_START = 2000
YEAR_END = 2024

# fmt: off
# ──────────────────────────────────────────────────────────────────────
#  Full dictionary — {brand: {model: (start_year, end_year)}}
# ──────────────────────────────────────────────────────────────────────
VEHICLES = {
    # ── American Brands ──────────────────────────────────────────────
    "Ford": {
        "F-150":      (2000, 2024),
        "Mustang":    (2000, 2024),
        "Explorer":   (2000, 2024),
        "Escape":     (2001, 2024),
        "Edge":       (2007, 2024),
        "Expedition": (2000, 2024),
        "Ranger":     (2000, 2024),   # gap 2012-2018, 404 handler covers it
        "Bronco":     (2021, 2024),
        "Focus":      (2000, 2018),
        "Fusion":     (2006, 2020),
        "Taurus":     (2000, 2019),
        "Fiesta":     (2011, 2019),
        "F-250":      (2000, 2024),
        "F-350":      (2000, 2024),
        "Flex":       (2009, 2019),
        "Transit":    (2015, 2024),
        "EcoSport":   (2018, 2022),
        "Maverick":   (2022, 2024),
    },
    "Chevrolet": {
        "Silverado-1500": (2000, 2024),
        "Camaro":         (2000, 2024),  # gap 2003-2009, 404 covers it
        "Corvette":       (2000, 2024),
        "Equinox":        (2005, 2024),
        "Tahoe":          (2000, 2024),
        "Suburban":       (2000, 2024),
        "Traverse":       (2009, 2024),
        "Malibu":         (2000, 2024),
        "Impala":         (2000, 2020),
        "Cruze":          (2011, 2019),
        "Colorado":       (2004, 2024),
        "Blazer":         (2019, 2024),
        "Trax":           (2015, 2024),
        "Spark":          (2013, 2022),
        "Sonic":          (2012, 2020),
        "Bolt-EV":        (2017, 2023),
        "Trailblazer":    (2021, 2024),
    },
    "GMC": {
        "Sierra-1500":  (2000, 2024),
        "Yukon":        (2000, 2024),
        "Acadia":       (2007, 2024),
        "Terrain":      (2010, 2024),
        "Canyon":       (2004, 2024),
        "Sierra-2500HD":(2001, 2024),
        "Yukon-XL":     (2000, 2024),
        "Savana":       (2003, 2024),
    },
    "Dodge": {
        "Charger":       (2006, 2024),
        "Challenger":    (2008, 2024),
        "Durango":       (2000, 2024),
        "Ram-1500":      (2000, 2010),  # Ram split to own brand in 2011
        "Grand-Caravan": (2000, 2020),
        "Journey":       (2009, 2020),
        "Dart":          (2013, 2016),
        "Nitro":         (2007, 2011),
        "Avenger":       (2008, 2014),
        "Magnum":        (2005, 2008),
    },
    "Jeep": {
        "Wrangler":       (2000, 2024),
        "Grand-Cherokee": (2000, 2024),
        "Cherokee":       (2000, 2024),  # gap 2002-2013, 404 covers it
        "Compass":        (2007, 2024),
        "Renegade":       (2015, 2024),
        "Gladiator":      (2020, 2024),
        "Liberty":        (2002, 2012),
        "Patriot":        (2007, 2017),
        "Commander":      (2006, 2010),
        "Wagoneer":       (2022, 2024),
    },
    "Chrysler": {
        "300":              (2005, 2024),
        "Pacifica":         (2017, 2024),
        "Town-and-Country": (2000, 2016),
        "Sebring":          (2001, 2010),
        "200":              (2011, 2017),
        "PT-Cruiser":       (2001, 2010),
    },
    "Tesla": {
        "Model-3":   (2017, 2024),
        "Model-Y":   (2020, 2024),
        "Model-S":   (2012, 2024),
        "Model-X":   (2016, 2024),
        "Cybertruck": (2024, 2024),
    },
    "Cadillac": {
        "Escalade": (2000, 2024),
        "XT5":      (2017, 2024),
        "XT4":      (2019, 2024),
        "CT5":      (2020, 2024),
        "CT4":      (2020, 2024),
        "XT6":      (2020, 2024),
        "CTS":      (2003, 2019),
        "ATS":      (2013, 2019),
        "SRX":      (2004, 2016),
        "DTS":      (2006, 2011),
        "XTS":      (2013, 2019),
        "Lyriq":    (2023, 2024),
    },
    "Lincoln": {
        "Navigator":   (2000, 2024),
        "Aviator":     (2003, 2024),  # gap 2006-2019, 404 covers it
        "Corsair":     (2020, 2024),
        "Nautilus":    (2019, 2024),
        "MKZ":         (2007, 2020),
        "MKC":         (2015, 2019),
        "MKX":         (2007, 2018),
        "Continental": (2017, 2020),
        "Town-Car":    (2000, 2011),
    },
    "Buick": {
        "Enclave":  (2008, 2024),
        "Encore":   (2013, 2024),
        "Envision": (2016, 2024),
        "LaCrosse": (2005, 2019),
        "Regal":    (2011, 2020),
        "Verano":   (2012, 2017),
    },

    # ── Japanese Brands ──────────────────────────────────────────────
    "Toyota": {
        "Camry":            (2000, 2024),
        "Corolla":          (2000, 2024),
        "RAV4":             (2000, 2024),
        "Highlander":       (2001, 2024),
        "Tacoma":           (2000, 2024),
        "Tundra":           (2000, 2024),
        "4Runner":          (2000, 2024),
        "Prius":            (2001, 2024),
        "Sienna":           (2000, 2024),
        "Avalon":           (2000, 2022),
        "Land-Cruiser":     (2000, 2024),  # gap 2022-2023, 404 covers it
        "Sequoia":          (2001, 2024),
        "C-HR":             (2018, 2022),
        "Venza":            (2009, 2024),  # gap 2016-2020, 404 covers it
        "Supra":            (2020, 2024),
        "86":               (2017, 2020),
        "Yaris":            (2004, 2020),
        "Matrix":           (2003, 2013),
        "FJ-Cruiser":       (2007, 2014),
        "Crown":            (2023, 2024),
        "GR86":             (2022, 2024),
        "Corolla-Cross":    (2022, 2024),
        "Grand-Highlander": (2024, 2024),
        "bZ4X":             (2023, 2024),
    },
    "Honda": {
        "Civic":     (2000, 2024),
        "Accord":    (2000, 2024),
        "CR-V":      (2000, 2024),
        "Pilot":     (2003, 2024),
        "Odyssey":   (2000, 2024),
        "HR-V":      (2016, 2024),
        "Passport":  (2019, 2024),
        "Ridgeline": (2006, 2024),  # gap 2015-2016, 404 covers it
        "Fit":       (2007, 2020),
        "Insight":   (2000, 2022),  # gap 2007-2009, 2015-2018; 404 covers
        "Element":   (2003, 2011),
        "S2000":     (2000, 2009),
        "Crosstour": (2010, 2015),
        "Prologue":  (2024, 2024),
        "CR-Z":      (2011, 2016),
    },
    "Nissan": {
        "Altima":    (2000, 2024),
        "Sentra":    (2000, 2024),
        "Rogue":     (2008, 2024),
        "Pathfinder":(2000, 2024),
        "Murano":    (2003, 2024),
        "Maxima":    (2000, 2023),
        "Frontier":  (2000, 2024),
        "Titan":     (2004, 2024),
        "Armada":    (2004, 2024),
        "370Z":      (2009, 2020),
        "350Z":      (2003, 2009),
        "Versa":     (2007, 2024),
        "Kicks":     (2018, 2024),
        "Juke":      (2011, 2017),
        "Leaf":      (2011, 2024),
        "GT-R":      (2009, 2024),
        "Quest":     (2004, 2017),
        "Xterra":    (2000, 2015),
        "Z":         (2023, 2024),
    },
    "Mazda": {
        "Mazda3":     (2004, 2024),
        "Mazda6":     (2003, 2021),
        "CX-5":      (2013, 2024),
        "CX-9":      (2007, 2024),
        "CX-30":     (2020, 2024),
        "MX-5-Miata":(2000, 2024),
        "CX-3":      (2016, 2021),
        "CX-50":     (2023, 2024),
        "RX-8":      (2004, 2012),
        "Tribute":   (2001, 2011),
        "CX-7":      (2007, 2012),
    },
    "Subaru": {
        "Outback":   (2000, 2024),
        "Forester":  (2000, 2024),
        "Crosstrek": (2013, 2024),
        "Impreza":   (2000, 2024),
        "Legacy":    (2000, 2024),
        "Ascent":    (2019, 2024),
        "WRX":       (2002, 2024),
        "BRZ":       (2013, 2024),
        "Tribeca":   (2006, 2014),
        "Baja":      (2003, 2006),
        "Solterra":  (2023, 2024),
    },
    "Lexus": {
        "RX":     (2000, 2024),
        "ES":     (2000, 2024),
        "NX":     (2015, 2024),
        "GX":     (2003, 2024),
        "IS":     (2001, 2024),
        "LS":     (2000, 2024),
        "LX":     (2000, 2024),
        "UX":     (2019, 2024),
        "RC":     (2015, 2024),
        "LC":     (2018, 2024),
        "RX-350": (2007, 2024),
        "ES-350": (2007, 2024),
        "NX-300": (2018, 2021),
        "GS":     (2000, 2020),
        "CT":     (2011, 2017),
        "RZ":     (2023, 2024),
    },
    "Infiniti": {
        "Q50":  (2014, 2024),
        "Q60":  (2014, 2022),
        "QX50": (2014, 2024),
        "QX60": (2013, 2024),
        "QX80": (2014, 2024),
        "G35":  (2003, 2008),
        "G37":  (2008, 2013),
        "FX35": (2003, 2013),
        "QX55": (2022, 2024),
        "QX70": (2014, 2017),
        "M35":  (2006, 2010),
        "M37":  (2011, 2013),
        "JX35": (2013, 2013),
    },
    "Acura": {
        "MDX":     (2001, 2024),
        "RDX":     (2007, 2024),
        "TLX":     (2015, 2024),
        "ILX":     (2013, 2022),
        "NSX":     (2017, 2022),
        "TSX":     (2004, 2014),
        "TL":      (2000, 2014),
        "RL":      (2000, 2012),
        "ZDX":     (2010, 2013),
        "Integra": (2023, 2024),
        "RSX":     (2002, 2006),
    },
    "Mitsubishi": {
        "Outlander":       (2003, 2024),
        "Eclipse-Cross":   (2018, 2024),
        "Outlander-Sport": (2011, 2024),
        "Mirage":          (2014, 2024),
        "Lancer":          (2002, 2017),
        "Eclipse":         (2000, 2012),
        "Galant":          (2000, 2012),
        "Endeavor":        (2004, 2011),
        "Montero":         (2001, 2006),
    },

    # ── German Brands ────────────────────────────────────────────────
    "BMW": {
        "3-Series": (2000, 2024),
        "5-Series": (2000, 2024),
        "X3":       (2004, 2024),
        "X5":       (2000, 2024),
        "7-Series": (2000, 2024),
        "X1":       (2013, 2024),
        "X7":       (2019, 2024),
        "4-Series": (2014, 2024),
        "2-Series": (2014, 2024),
        "6-Series": (2004, 2019),
        "X4":       (2015, 2024),
        "X6":       (2008, 2024),
        "i3":       (2014, 2021),
        "i4":       (2022, 2024),
        "iX":       (2022, 2024),
        "M3":       (2001, 2024),
        "M4":       (2015, 2024),
        "M5":       (2000, 2024),
        "Z4":       (2003, 2024),  # gap 2017-2019, 404 covers it
        "8-Series": (2019, 2024),
    },
    "Mercedes-Benz": {
        "C-Class": (2001, 2024),
        "E-Class": (2000, 2024),
        "S-Class": (2000, 2024),
        "GLC":     (2016, 2024),
        "GLE":     (2016, 2024),
        "GLS":     (2017, 2024),
        "A-Class": (2019, 2022),
        "CLA":     (2014, 2024),
        "GLB":     (2020, 2024),
        "G-Class": (2002, 2024),
        "CLS":     (2006, 2024),
        "SL":      (2003, 2024),
        "AMG-GT":  (2016, 2024),
        "EQS":     (2022, 2024),
        "EQE":     (2023, 2024),
        "GLA":     (2015, 2024),
        "GLK":     (2010, 2015),
        "ML":      (2000, 2015),
        "GL":      (2007, 2016),
        "SLK":     (2001, 2016),
        "CLK":     (2001, 2009),
    },
    "Audi": {
        "A4":        (2000, 2024),
        "A6":        (2000, 2024),
        "Q5":        (2009, 2024),
        "Q7":        (2007, 2024),
        "A3":        (2006, 2024),
        "Q3":        (2015, 2024),
        "A5":        (2008, 2024),
        "A8":        (2000, 2024),
        "Q8":        (2019, 2024),
        "e-tron":    (2019, 2024),
        "TT":        (2000, 2024),
        "R8":        (2008, 2024),
        "S4":        (2004, 2024),
        "S5":        (2008, 2024),
        "RS5":       (2013, 2024),
        "A7":        (2012, 2024),
        "Q4-e-tron": (2022, 2024),
        "SQ5":       (2014, 2024),
    },
    "Volkswagen": {
        "Jetta":   (2000, 2024),
        "Passat":  (2000, 2022),
        "Tiguan":  (2009, 2024),
        "Atlas":   (2018, 2024),
        "Golf":    (2000, 2024),
        "GTI":     (2006, 2024),
        "Beetle":  (2000, 2019),
        "Arteon":  (2019, 2024),
        "ID.4":    (2021, 2024),
        "Taos":    (2022, 2024),
        "CC":      (2009, 2017),
        "Touareg": (2004, 2017),
        "Rabbit":  (2006, 2009),
        "Eos":     (2007, 2016),
    },
    "Porsche": {
        "911":         (2000, 2024),
        "Cayenne":     (2003, 2024),
        "Macan":       (2015, 2024),
        "Panamera":    (2010, 2024),
        "Taycan":      (2020, 2024),
        "718-Cayman":  (2017, 2024),
        "718-Boxster": (2017, 2024),
        "Boxster":     (2000, 2016),
        "Cayman":      (2006, 2016),
    },

    # ── Korean Brands ────────────────────────────────────────────────
    "Hyundai": {
        "Elantra":    (2001, 2024),
        "Sonata":     (2000, 2024),
        "Tucson":     (2005, 2024),
        "Santa-Fe":   (2001, 2024),
        "Palisade":   (2020, 2024),
        "Kona":       (2018, 2024),
        "Venue":      (2020, 2024),
        "Ioniq":      (2017, 2022),
        "Accent":     (2000, 2022),
        "Veloster":   (2012, 2021),
        "Genesis":    (2009, 2016),
        "Azera":      (2006, 2017),
        "Santa-Cruz": (2022, 2024),
        "Ioniq-5":    (2022, 2024),
        "Ioniq-6":    (2023, 2024),
    },
    "Kia": {
        "Optima":   (2001, 2020),
        "Sorento":  (2003, 2024),
        "Sportage": (2000, 2024),
        "Telluride":(2020, 2024),
        "Forte":    (2010, 2024),
        "Soul":     (2010, 2024),
        "Seltos":   (2021, 2024),
        "K5":       (2021, 2024),
        "Carnival": (2022, 2024),
        "Stinger":  (2018, 2024),
        "Niro":     (2017, 2024),
        "Rio":      (2001, 2024),
        "Cadenza":  (2014, 2020),
        "EV6":      (2022, 2024),
        "Sedona":   (2002, 2021),
    },
    "Genesis": {
        "G70":  (2019, 2024),
        "G80":  (2017, 2024),
        "G90":  (2017, 2024),
        "GV70": (2022, 2024),
        "GV80": (2021, 2024),
        "GV60": (2023, 2024),
    },

    # ── British Brands ───────────────────────────────────────────────
    "Land-Rover": {
        "Range-Rover":        (2003, 2024),
        "Range-Rover-Sport":  (2006, 2024),
        "Discovery":          (2017, 2024),
        "Defender":           (2020, 2024),
        "Range-Rover-Velar":  (2018, 2024),
        "Range-Rover-Evoque": (2012, 2024),
        "Discovery-Sport":    (2015, 2024),
        "LR2":                (2008, 2015),
        "LR3":                (2005, 2009),
        "LR4":                (2010, 2016),
        "Freelander":         (2002, 2005),
    },
    "Jaguar": {
        "F-Pace": (2017, 2024),
        "E-Pace": (2018, 2024),
        "XF":     (2009, 2024),
        "XE":     (2017, 2024),
        "F-Type": (2014, 2024),
        "XJ":     (2000, 2019),
        "XK":     (2007, 2015),
        "I-Pace": (2019, 2024),
        "S-Type": (2000, 2008),
        "X-Type": (2002, 2008),
    },
    "Mini": {
        "Cooper":      (2002, 2024),
        "Countryman":  (2011, 2024),
        "Clubman":     (2008, 2024),
        "Convertible": (2005, 2024),
        "Hardtop":     (2014, 2024),
        "Paceman":     (2013, 2016),
        "Coupe":       (2012, 2015),
        "Roadster":    (2012, 2015),
    },

    # ── Italian Brands ───────────────────────────────────────────────
    "Alfa-Romeo": {
        "Giulia":  (2017, 2024),
        "Stelvio": (2018, 2024),
        "4C":      (2015, 2020),
        "Tonale":  (2023, 2024),
    },
    "Maserati": {
        "Ghibli":       (2014, 2024),
        "Levante":      (2017, 2024),
        "Quattroporte": (2005, 2024),
        "GranTurismo":  (2008, 2024),
        "MC20":         (2022, 2024),
    },
    "Fiat": {
        "500":        (2012, 2019),
        "500X":       (2016, 2024),
        "500L":       (2014, 2020),
        "124-Spider": (2017, 2020),
    },

    # ── Swedish Brands ───────────────────────────────────────────────
    "Volvo": {
        "XC90": (2003, 2024),
        "XC60": (2010, 2024),
        "XC40": (2019, 2024),
        "S60":  (2001, 2024),
        "S90":  (2017, 2024),
        "V60":  (2015, 2024),
        "V90":  (2017, 2024),
        "C40":  (2022, 2024),
        "S40":  (2004, 2011),
        "C30":  (2008, 2013),
        "C70":  (2006, 2013),
        "V50":  (2005, 2011),
    },

    # ── Other Brands ─────────────────────────────────────────────────
    "Ram": {
        "1500":           (2011, 2024),  # became its own brand in 2011
        "2500":           (2011, 2024),
        "3500":           (2011, 2024),
        "ProMaster":      (2014, 2024),
        "ProMaster-City": (2015, 2024),
    },
    "Rivian": {
        "R1T": (2022, 2024),
        "R1S": (2022, 2024),
    },
    "Lucid": {
        "Air": (2022, 2024),
    },
    "Polestar": {
        "2": (2021, 2024),
        "1": (2020, 2021),
    },
}
# fmt: on


# ──────────────────────────────────────────────────────────────────────
#  Test dictionary — same format, small subset
# ──────────────────────────────────────────────────────────────────────
VEHICLES_TEST = {
    "Toyota": {"Corolla": (2000, 2024), "RAV4": (2000, 2024)},
    "Honda":  {"Civic": (2000, 2024), "CR-V": (2000, 2024)},
    "Ford":   {"F-150": (2000, 2024), "Mustang": (2000, 2024), "Explorer": (2000, 2024)},
    "BMW":    {"3-Series": (2000, 2024), "M4": (2015, 2024), "X5": (2000, 2024)},
    "Audi":   {"A3": (2006, 2024), "Q5": (2009, 2024)},
}

# Test mode only uses these specific years (intersected with model ranges)
YEARS_TEST = [2017, 2020, 2023]


# ──────────────────────────────────────────────────────────────────────
#  Helper functions
# ──────────────────────────────────────────────────────────────────────

def get_all_vehicles(test_mode: bool = False) -> dict:
    """Get vehicle dictionary based on mode."""
    return VEHICLES_TEST if test_mode else VEHICLES


def get_scrape_combinations(test_mode: bool = False) -> list:
    """
    Generate all valid (make, model, year) combinations for scraping.

    Each model's year range is respected — years outside the range are
    skipped.  In test mode the years are further restricted to YEARS_TEST.

    Returns:
        List of tuples: [(make, model, year_str), ...]
    """
    vehicles = get_all_vehicles(test_mode)

    combinations = []
    for make, models in vehicles.items():
        for model, (start_year, end_year) in models.items():
            if test_mode:
                years = [y for y in YEARS_TEST if start_year <= y <= end_year]
            else:
                years = list(range(start_year, end_year + 1))

            for year in years:
                combinations.append((make, model, str(year)))

    return combinations


def get_stats(test_mode: bool = False) -> dict:
    """Get statistics about the vehicle dictionary."""
    vehicles = get_all_vehicles(test_mode)
    combinations = get_scrape_combinations(test_mode)

    total_models = sum(len(models) for models in vehicles.values())

    # Collect all years that actually appear in the combinations
    all_years = sorted({int(y) for _, _, y in combinations}) if combinations else []

    return {
        "brands": len(vehicles),
        "total_models": total_models,
        "year_range": f"{all_years[0]}-{all_years[-1]}" if all_years else "N/A",
        "total_combinations": len(combinations),
    }


if __name__ == "__main__":
    # Print stats for both modes
    print("=== Full Vehicle Dictionary ===")
    stats = get_stats(test_mode=False)
    for key, value in stats.items():
        print(f"  {key}: {value}")

    print("\n=== Test Vehicle Dictionary ===")
    stats_test = get_stats(test_mode=True)
    for key, value in stats_test.items():
        print(f"  {key}: {value}")

    print("\n=== Sample Test Combinations ===")
    combos = get_scrape_combinations(test_mode=True)
    for combo in combos[:10]:
        print(f"  {combo}")
    if len(combos) > 10:
        print(f"  ... and {len(combos) - 10} more")
    else:
        print(f"  Total: {len(combos)}")
