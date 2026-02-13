"""
Data models for car specifications
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime

@dataclass
class TrimSpecification:
    """Specification for a single trim"""
    trim_name: str
    value: str
    unit: str = ""
    is_numeric: bool = False

@dataclass
class Specification:
    """A single specification with values for different trims"""
    name: str
    category: str
    trims: List[TrimSpecification] = field(default_factory=list)
    description: str = ""

@dataclass
class BodyTypeData:
    """Data for a specific body type"""
    body_type: str
    tab_name: str
    trim_names: List[str]
    specifications: List[Specification] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    scrape_timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class CarModelData:
    """Complete data for a car model"""
    make: str
    model: str
    year: str
    bodytypes: Dict[str, BodyTypeData] = field(default_factory=dict)
    url: str = ""
    scrape_date: datetime = field(default_factory=datetime.now)

    def add_bodytype_data(self, body_type: str, data: BodyTypeData):
        """Add body type data"""
        self.bodytypes[body_type] = data

    def get_all_specifications(self) -> List[Specification]:
        """Get all specifications across all body types"""
        all_specs = []
        for bodytype_data in self.bodytypes.values():
            all_specs.extend(bodytype_data.specifications)
        return all_specs

    def to_dataframe(self):
        """Convert to pandas DataFrame"""
        import pandas as pd

        rows = []
        for body_type, bodytype_data in self.bodytypes.items():
            for spec in bodytype_data.specifications:
                for trim_spec in spec.trims:
                    row = {
                        'make': self.make,
                        'model': self.model,
                        'year': self.year,
                        'body_type': body_type,
                        'tab_name': bodytype_data.tab_name,
                        'spec_name': spec.name,
                        'spec_category': spec.category,
                        'trim_name': trim_spec.trim_name,
                        'value': trim_spec.value,
                        'unit': trim_spec.unit,
                        'is_numeric': trim_spec.is_numeric,
                        'scrape_date': self.scrape_date
                    }
                    rows.append(row)

        return pd.DataFrame(rows)