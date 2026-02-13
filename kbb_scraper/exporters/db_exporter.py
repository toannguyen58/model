"""
Database exporter for 4-table schema JSON output.
"""
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

from ..models.db_schema import FourTableDataset

logger = logging.getLogger(__name__)


class DatabaseExporter:
    """
    Exports FourTableDataset to JSON files in database-ready format.

    Creates:
    - vehicle.json
    - vehicle_specs.json
    - vehicle_features.json
    - vehicle_scores.json
    - combined_4table.json (all tables in one file)
    - metadata.json
    """

    def __init__(self, output_dir: Path):
        """
        Initialize exporter with output directory.

        Args:
            output_dir: Directory to write JSON files to
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export(self, dataset: FourTableDataset,
               make: str, model: str, year: str,
               include_timestamp: bool = True) -> Dict[str, Path]:
        """
        Export dataset to JSON files.

        Args:
            dataset: FourTableDataset to export
            make: Vehicle make for metadata
            model: Vehicle model for metadata
            year: Vehicle year for metadata
            include_timestamp: Whether to include timestamp in filenames

        Returns:
            Dictionary mapping table names to file paths
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S") if include_timestamp else ""
        prefix = f"{timestamp}_" if timestamp else ""

        exported_files = {}

        # Get all table data
        tables = dataset.to_dict()

        # Export individual table files
        for table_name in ["vehicle", "vehicle_specs", "vehicle_features", "vehicle_scores"]:
            table_data = tables[table_name]
            filename = f"{prefix}{table_name}.json"
            filepath = self.output_dir / filename

            self._write_json(filepath, table_data)
            exported_files[table_name] = filepath
            logger.info(f"Exported {len(table_data['records'])} records to {filepath}")

        # Export combined file
        combined_filename = f"{prefix}combined_4table.json"
        combined_filepath = self.output_dir / combined_filename
        self._write_json(combined_filepath, tables)
        exported_files["combined"] = combined_filepath
        logger.info(f"Exported combined data to {combined_filepath}")

        # Export metadata
        metadata = self._create_metadata(dataset, make, model, year)
        metadata_filename = f"{prefix}metadata.json"
        metadata_filepath = self.output_dir / metadata_filename
        self._write_json(metadata_filepath, metadata)
        exported_files["metadata"] = metadata_filepath

        return exported_files

    def export_single_table(self, dataset: FourTableDataset, table_name: str,
                            filename: Optional[str] = None) -> Path:
        """
        Export a single table to JSON.

        Args:
            dataset: FourTableDataset to export from
            table_name: Name of table ("vehicle", "vehicle_specs", etc.)
            filename: Optional custom filename

        Returns:
            Path to exported file
        """
        table_data = dataset.get_table(table_name)

        if not table_data:
            raise ValueError(f"Unknown table: {table_name}")

        if filename is None:
            filename = f"{table_name}.json"

        filepath = self.output_dir / filename
        self._write_json(filepath, table_data)

        logger.info(f"Exported {table_name} to {filepath}")
        return filepath

    def _write_json(self, filepath: Path, data: Dict[str, Any]):
        """Write data to JSON file."""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _create_metadata(self, dataset: FourTableDataset,
                         make: str, model: str, year: str) -> Dict[str, Any]:
        """Create metadata about the export."""
        return {
            "export_info": {
                "timestamp": datetime.now().isoformat(),
                "schema_version": "4table_v1",
                "source": "kbb_scraper"
            },
            "vehicle_info": {
                "make": make,
                "model": model,
                "year": year
            },
            "record_counts": {
                "vehicle": len(dataset.vehicles),
                "vehicle_specs": len(dataset.specs),
                "vehicle_features": len(dataset.features),
                "vehicle_scores": len(dataset.scores)
            },
            "tables": ["vehicle", "vehicle_specs", "vehicle_features", "vehicle_scores"]
        }


def export_to_database_format(dataset: FourTableDataset, output_dir: Path,
                               make: str, model: str, year: str) -> Dict[str, Path]:
    """
    Convenience function to export dataset to database format.

    Args:
        dataset: FourTableDataset to export
        output_dir: Directory to write files to
        make: Vehicle make
        model: Vehicle model
        year: Vehicle year

    Returns:
        Dictionary mapping table names to file paths
    """
    exporter = DatabaseExporter(output_dir)
    return exporter.export(dataset, make, model, year)
