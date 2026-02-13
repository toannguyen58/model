"""
Handles file operations for saving scraped data - Fixed save methods
"""
import pandas as pd
import json
import csv
import logging
import traceback
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

from ..config.settings import RAW_DATA_DIR, PROCESSED_DATA_DIR, RESEARCH_CONFIG

logger = logging.getLogger(__name__)

class DataSaver:
    """Handles saving scraped data - FIXED save methods"""

    def __init__(self):
        self.raw_data_dir = RAW_DATA_DIR
        self.processed_data_dir = PROCESSED_DATA_DIR
        self.data_format = RESEARCH_CONFIG['data_format']
        self.include_timestamp = RESEARCH_CONFIG['include_timestamp']

    def save_bodytype_data(self, bodytype_data: Dict[str, Any],
                          filename: str, body_type: str,
                          make: str, model: str, year: str):
        """Save data for a specific body type - FIXED parameter handling"""
        try:
            # Check if bodytype_data is valid
            if not bodytype_data or not isinstance(bodytype_data, dict):
                logger.error(f"❌ Invalid bodytype_data for {body_type}: expected dict, got {type(bodytype_data)}")
                return

            if 'specifications' not in bodytype_data or 'trim_names' not in bodytype_data:
                logger.error(f"❌ Missing required fields in bodytype_data for {body_type}")
                return

            # Create filename with timestamp if configured
            if self.include_timestamp:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{timestamp}_{filename}"

            # Create body type directory
            bodytype_dir = self.raw_data_dir / body_type
            bodytype_dir.mkdir(parents=True, exist_ok=True)
            filepath = bodytype_dir / filename

            # Convert to DataFrame
            df = self._create_dataframe_from_parsed_data(
                bodytype_data['specifications'],
                bodytype_data['trim_names']
            )

            if df is not None and not df.empty:
                # Add metadata columns
                df.insert(0, 'body_type', body_type)
                df.insert(0, 'tab_name', bodytype_data.get('tab_name', ''))
                df.insert(0, 'year', year)
                df.insert(0, 'model', model)
                df.insert(0, 'make', make)
                df.insert(0, 'scrape_date', datetime.now().strftime("%Y-%m-%d"))

                # Save based on format
                if self.data_format == 'csv':
                    filepath = filepath.with_suffix('.csv')
                    df.to_csv(filepath, index=False, encoding='utf-8')
                elif self.data_format == 'json':
                    filepath = filepath.with_suffix('.json')
                    df.to_json(filepath, orient='records', indent=2)
                elif self.data_format == 'parquet':
                    filepath = filepath.with_suffix('.parquet')
                    df.to_parquet(filepath, index=False)

                logger.info(f"💾 Saved {body_type} data to {filepath}")
                logger.info(f"   📊 {len(df)} rows, {len(bodytype_data['trim_names'])} trims")

                # Also save raw JSON for reference
                raw_json_path = filepath.with_suffix('.raw.json')
                with open(raw_json_path, 'w', encoding='utf-8') as f:
                    json.dump(bodytype_data, f, indent=2, ensure_ascii=False)
            else:
                logger.warning(f"⚠️  No data to save for {body_type}")

        except Exception as e:
            logger.error(f"❌ Error saving bodytype data for {body_type}: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")

    def _create_dataframe_from_parsed_data(self, specifications: List[Dict[str, Any]],
                                          trim_names: List[str]) -> pd.DataFrame:
        """Create DataFrame from parsed specification data"""
        if not specifications or not trim_names:
            return pd.DataFrame()

        rows = []
        for spec in specifications:
            spec_name = spec.get('spec_name', '')
            spec_category = spec.get('spec_category', '')
            unit = spec.get('unit', '')
            values = spec.get('values', [])
            is_numeric = spec.get('is_numeric', False)

            # Ensure values list matches trim_names length
            if len(values) != len(trim_names):
                # Pad or truncate values to match trim_names
                if len(values) < len(trim_names):
                    values = values + [''] * (len(trim_names) - len(values))
                else:
                    values = values[:len(trim_names)]

            # Create one row per trim
            for trim_name, value in zip(trim_names, values):
                row = {
                    'spec_name': spec_name,
                    'spec_category': spec_category,
                    'unit': unit,
                    'trim_name': trim_name,
                    'value': value,
                    'is_numeric': is_numeric
                }
                rows.append(row)

        df = pd.DataFrame(rows)

        # Clean up empty values
        df = df.replace('', pd.NA)

        return df

    def save_combined_data(self, results: Dict[str, Any],
                          make: str, model: str, year: str):
        """Save all data combined in one file - FIXED"""
        try:
            # Check if results has bodytypes
            if 'bodytypes' not in results or not results['bodytypes']:
                logger.warning(f"⚠️  No bodytypes data to combine for {make} {model} {year}")
                return

            # Create combined DataFrame
            all_dfs = []

            for body_type, data in results['bodytypes'].items():
                if isinstance(data, dict) and 'specifications' in data and 'trim_names' in data:
                    df = self._create_dataframe_from_parsed_data(
                        data['specifications'],
                        data['trim_names']
                    )

                    if df is not None and not df.empty:
                        # Add identifying columns
                        df.insert(0, 'body_type', body_type)
                        df.insert(0, 'tab_name', data.get('tab_name', ''))
                        all_dfs.append(df)
                else:
                    logger.warning(f"⚠️  Invalid data structure for {body_type}: {type(data)}")

            if not all_dfs:
                logger.warning(f"⚠️  No valid data to combine for {make} {model} {year}")
                return

            combined_df = pd.concat(all_dfs, ignore_index=True)

            # Add common metadata
            combined_df.insert(0, 'year', year)
            combined_df.insert(0, 'model', model)
            combined_df.insert(0, 'make', make)
            combined_df.insert(0, 'scrape_date', datetime.now().strftime("%Y-%m-%d"))

            # Remove any completely empty rows
            combined_df = combined_df.dropna(how='all')

            # Save to processed directory
            filename = f"{make.lower()}_{model.lower()}_{year}_combined.{self.data_format}"
            if self.include_timestamp:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{timestamp}_{filename}"

            filepath = self.processed_data_dir / filename

            if self.data_format == 'csv':
                filepath = filepath.with_suffix('.csv')
                combined_df.to_csv(filepath, index=False, encoding='utf-8')
            elif self.data_format == 'json':
                filepath = filepath.with_suffix('.json')
                combined_df.to_json(filepath, orient='records', indent=2)
            elif self.data_format == 'parquet':
                filepath = filepath.with_suffix('.parquet')
                combined_df.to_parquet(filepath, index=False)

            logger.info(f"💾 Saved combined data to {filepath}")
            logger.info(f"   📊 Total rows: {len(combined_df)}")

        except Exception as e:
            logger.error(f"❌ Error saving combined data: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")

    def save_single_dataset(self, results: Dict[str, Any], filename: str):
        """Save single dataset (no body type separation) - FIXED"""
        try:
            if self.include_timestamp:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{timestamp}_{filename}"

            filepath = self.raw_data_dir / filename

            # Convert to DataFrame
            if 'data' in results and results['data']:
                all_dfs = []
                for data in results['data']:
                    if isinstance(data, dict) and 'specifications' in data and 'trim_names' in data:
                        df = self._create_dataframe_from_parsed_data(
                            data['specifications'],
                            data['trim_names']
                        )

                        if df is not None and not df.empty:
                            if 'tab_name' in data:
                                df.insert(0, 'tab_name', data['tab_name'])
                            all_dfs.append(df)

                if all_dfs:
                    combined_df = pd.concat(all_dfs, ignore_index=True)

                    # Add metadata
                    combined_df.insert(0, 'year', results['year'])
                    combined_df.insert(0, 'model', results['model'])
                    combined_df.insert(0, 'make', results['make'])
                    combined_df.insert(0, 'scrape_date', datetime.now().strftime("%Y-%m-%d"))

                    # Save
                    if self.data_format == 'csv':
                        filepath = filepath.with_suffix('.csv')
                        combined_df.to_csv(filepath, index=False, encoding='utf-8')
                    elif self.data_format == 'json':
                        filepath = filepath.with_suffix('.json')
                        combined_df.to_json(filepath, orient='records', indent=2)

                    logger.info(f"💾 Saved single dataset to {filepath}")

        except Exception as e:
            logger.error(f"❌ Error saving single dataset: {e}")