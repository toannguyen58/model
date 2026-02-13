#!/usr/bin/env python3
"""
Main script for KBB research data collection - Fixed summary logging
"""
import argparse
import logging
import sys
import traceback
from pathlib import Path
from typing import Dict, Any, List
from kbb_scraper.scrapers.kbb_scraper import KBBResearchScraper
from kbb_scraper.scrapers.reviews_scraper import KBBReviewsScraper
from kbb_scraper.utils.helpers import setup_logging, extract_car_info_from_url
from kbb_scraper.config import settings, get_scrape_combinations, get_stats

logger = setup_logging()

def validate_and_summarize_results(results: Dict[str, Any], make: str, model: str, year: str) -> bool:
    """Validate scraped data and print summary - FIXED"""
    if not results:
        logger.error(f"No results returned for {year} {make} {model}")
        return False

    # Check if we have bodytypes data
    if 'bodytypes' not in results or not results['bodytypes']:
        logger.error(f"No bodytypes data in results for {year} {make} {model}")
        return False

    logger.info(f"Successfully scraped {year} {make} {model}")

    # Calculate and print accurate summary
    total_specs = 0
    total_trims = 0

    for body_type, data in results['bodytypes'].items():
        if isinstance(data, dict):
            specs = len(data.get('specifications', []))
            trims = len(data.get('trim_names', []))
            logger.info(f"   {body_type}: {specs} specifications, {trims} trims")

            # Show sample trim names (cleaned)
            if 'trim_names' in data and data['trim_names']:
                sample_trims = data['trim_names'][:3]
                if sample_trims:
                    logger.info(f"     Sample trims: {', '.join(sample_trims[:3])}")

            total_specs += specs
            total_trims += trims

    logger.info(f"Total: {total_specs} specifications across {total_trims} unique trims")

    return True

def scrape_single_model(make: str, model: str, year: str, headless: bool = True):
    """Scrape a single car model"""
    logger.info(f"Starting scrape for {year} {make} {model}")

    scraper = KBBResearchScraper(headless=headless)

    try:
        results = scraper.scrape_car_model(make, model, year)

        if validate_and_summarize_results(results, make, model, year):
            return results
        else:
            logger.error(f"Invalid data scraped for {year} {make} {model}")
            return None

    except Exception as e:
        logger.error(f"Failed to scrape {year} {make} {model}: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None

    finally:
        scraper.close()

def scrape_from_url(url: str, headless: bool = True):
    """Scrape from a specific URL"""
    logger.info(f"Scraping from URL: {url}")

    # Extract car info from URL
    car_info = extract_car_info_from_url(url)

    if not car_info:
        logger.error(f"Could not extract car info from URL: {url}")
        return None

    return scrape_single_model(
        car_info['make'],
        car_info['model'],
        car_info['year'],
        headless
    ), car_info

def export_to_4table_format(results: Dict[str, Any], make: str, model: str, year: str,
                            output_dir: Path) -> bool:
    """
    Transform and export results to 4-table database format.

    Args:
        results: Raw scraped data with 'bodytypes' key
        make: Vehicle make
        model: Vehicle model
        year: Vehicle year
        output_dir: Directory to write output files

    Returns:
        True if export was successful, False otherwise
    """
    from kbb_scraper.transformers import SchemaTransformer
    from kbb_scraper.exporters import DatabaseExporter

    try:
        # Transform data
        transformer = SchemaTransformer()
        dataset = transformer.transform(results, make, model, year)

        if len(dataset) == 0:
            logger.error("No vehicles transformed - check input data")
            return False

        # Export to JSON files
        exporter = DatabaseExporter(output_dir)
        exported_files = exporter.export(dataset, make, model, year)

        logger.info(f"Exported {len(dataset)} vehicles to 4-table format:")
        for table_name, filepath in exported_files.items():
            logger.info(f"   {table_name}: {filepath}")

        return True

    except Exception as e:
        logger.error(f"Failed to export to 4-table format: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

def scrape_reviews_for_model(driver, make: str, model: str, year: str):
    """Scrape consumer reviews and expert review using an existing WebDriver session."""
    try:
        reviews_scraper = KBBReviewsScraper(driver=driver)
        review_data = reviews_scraper.scrape_reviews(make, model, year)

        has_consumer = review_data.consumer_review is not None
        has_expert = review_data.expert_review is not None
        logger.info(
            f"Reviews for {year} {make} {model}: "
            f"consumer={'yes' if has_consumer else 'no'}, "
            f"expert={'yes' if has_expert else 'no'}"
        )
        return review_data

    except Exception as e:
        logger.error(f"Failed to scrape reviews for {year} {make} {model}: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None


def scrape_single_model_with_reviews(make: str, model: str, year: str, headless: bool = True):
    """Scrape specifications AND reviews for a single car model in one browser session."""
    logger.info(f"Starting combined scrape (specs + reviews) for {year} {make} {model}")

    scraper = KBBResearchScraper(headless=headless)

    try:
        results = scraper.scrape_car_model(make, model, year)

        if not validate_and_summarize_results(results, make, model, year):
            logger.error(f"Invalid spec data for {year} {make} {model}")
            return None, None

        # Reuse the same browser session for reviews
        review_data = scrape_reviews_for_model(scraper.driver, make, model, year)
        return results, review_data

    except Exception as e:
        logger.error(f"Failed combined scrape for {year} {make} {model}: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None, None

    finally:
        scraper.close()


def _is_driver_alive(scraper) -> bool:
    """Check if the Selenium driver is still responsive."""
    try:
        _ = scraper.driver.title
        return True
    except Exception:
        return False


def _recreate_scraper(scraper, headless, with_reviews):
    """Recreate scraper (and optionally reviews scraper) after a driver crash."""
    try:
        scraper.close()
    except Exception:
        pass
    logger.warning("Recreating WebDriver...")
    new_scraper = KBBResearchScraper(headless=headless)
    new_reviews = KBBReviewsScraper(driver=new_scraper.driver) if with_reviews else None
    logger.info("WebDriver recreated successfully")
    return new_scraper, new_reviews


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='KBB Research Data Scraper')
    parser.add_argument('--make', help='Car make (e.g., Toyota)')
    parser.add_argument('--model', help='Car model (e.g., Camry)')
    parser.add_argument('--year', help='Model year (e.g., 2017)')
    parser.add_argument('--url', help='Direct KBB URL to scrape')
    parser.add_argument('--batch-file', help='JSON file with list of models to scrape')
    parser.add_argument('--no-headless', action='store_true',
                       help='Run browser in visible mode (for debugging)')
    parser.add_argument('--output-dir', help='Custom output directory')
    parser.add_argument('--export-db', action='store_true',
                       help='Export to 4-table database format (vehicle, vehicle_specs, vehicle_features, vehicle_scores)')
    parser.add_argument('--test', action='store_true',
                       help='Run with test dictionary (5 brands, 15 models, 3 years = 45 combinations)')
    parser.add_argument('--batch', action='store_true',
                       help='Run with full dictionary (38 brands, 412 models, 25 years = 10,300 combinations)')
    parser.add_argument('--with-reviews', action='store_true',
                       help='Also scrape consumer reviews and expert review/recommendations')

    args = parser.parse_args()

    # Override output directory if specified
    if args.output_dir:
        output_path = Path(args.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        settings.DATA_DIR = output_path
        settings.RAW_DATA_DIR = output_path / "raw"
        settings.PROCESSED_DATA_DIR = output_path / "processed"
        settings.CSV_DATA_DIR = output_path / "csv"
        settings.RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
        settings.PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
        settings.CSV_DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Set up 4-table output directory
    db_output_dir = settings.PROCESSED_DATA_DIR / "4table" if args.export_db else None
    if db_output_dir:
        db_output_dir.mkdir(parents=True, exist_ok=True)

    headless = not args.no_headless
    results = None
    make = model = year = None

    if args.url:
        # Scrape from single URL
        scrape_result = scrape_from_url(args.url, headless)
        if scrape_result:
            results, car_info = scrape_result
            make = car_info['make']
            model = car_info['model']
            year = car_info['year']
            if args.with_reviews and results:
                reviews_scraper = KBBReviewsScraper(headless=headless)
                try:
                    review_data = reviews_scraper.scrape_reviews(make, model, year)
                    has_consumer = review_data.consumer_review is not None
                    has_expert = review_data.expert_review is not None
                    logger.info(
                        f"Reviews for {year} {make} {model}: "
                        f"consumer={'yes' if has_consumer else 'no'}, "
                        f"expert={'yes' if has_expert else 'no'}"
                    )
                finally:
                    reviews_scraper.close()

    elif args.make and args.model and args.year:
        # Scrape single model
        make, model, year = args.make, args.model, args.year
        if args.with_reviews:
            results, _ = scrape_single_model_with_reviews(make, model, year, headless)
        else:
            results = scrape_single_model(make, model, year, headless)

    elif args.batch_file:
        # Scrape batch from file — reuse a single browser for all models
        import json

        batch_file = Path(args.batch_file)
        if not batch_file.exists():
            logger.error(f"Batch file not found: {batch_file}")
            return False

        with open(batch_file, 'r') as f:
            models = json.load(f)

        if not isinstance(models, list):
            logger.error("Batch file should contain a list of models")
            return False

        successful = 0
        failed = 0
        failed_models = []

        scraper = KBBResearchScraper(headless=headless)
        reviews_scraper = KBBReviewsScraper(driver=scraper.driver) if args.with_reviews else None

        try:
            for i, model_info in enumerate(models, 1):
                make = model_info.get('make')
                model = model_info.get('model')
                year = model_info.get('year')

                if not all([make, model, year]):
                    logger.warning(f"Skipping invalid model info: {model_info}")
                    failed += 1
                    continue

                logger.info(f"[{i}/{len(models)}] Scraping {year} {make} {model}")

                try:
                    result = scraper.scrape_car_model(make, model, year)

                    if validate_and_summarize_results(result, make, model, year):
                        successful += 1
                        if args.export_db and db_output_dir:
                            export_to_4table_format(result, make, model, year, db_output_dir)
                        if reviews_scraper:
                            reviews_scraper.scrape_reviews(make, model, year)
                    else:
                        failed += 1
                        failed_models.append(f"{year} {make} {model}")

                except Exception as e:
                    logger.error(f"Failed to scrape {year} {make} {model}: {e}")
                    failed += 1
                    failed_models.append(f"{year} {make} {model}")

                    if not _is_driver_alive(scraper):
                        scraper, reviews_scraper = _recreate_scraper(
                            scraper, headless, args.with_reviews
                        )

        finally:
            scraper.close()

        logger.info(f"\nBatch scraping complete:")
        logger.info(f"   Successful: {successful}/{len(models)}")
        logger.info(f"   Failed: {failed}")
        logger.info(f"   CSV data saved to: {settings.CSV_DATA_DIR / 'all_cars.csv'}")
        if args.export_db:
            logger.info(f"   4-table data saved to: {db_output_dir}")

        if failed_models:
            logger.info(f"   Failed models:")
            for fm in failed_models[:10]:
                logger.info(f"      - {fm}")
            if len(failed_models) > 10:
                logger.info(f"      ... and {len(failed_models) - 10} more")

        return successful > 0

    elif args.test or args.batch:
        # Scrape from vehicle dictionary (test or full)
        test_mode = args.test
        stats = get_stats(test_mode)
        combinations = get_scrape_combinations(test_mode)

        mode_name = "TEST" if test_mode else "FULL"
        logger.info(f"=== Running {mode_name} batch scrape ===")
        logger.info(f"   Brands: {stats['brands']}")
        logger.info(f"   Models: {stats['total_models']}")
        logger.info(f"   Years: {stats['year_range']}")
        logger.info(f"   Total combinations: {stats['total_combinations']}")

        successful = 0
        failed = 0
        failed_models = []

        scraper = KBBResearchScraper(headless=headless)
        reviews_scraper = KBBReviewsScraper(driver=scraper.driver) if args.with_reviews else None

        try:
            for i, (make, model, year) in enumerate(combinations, 1):
                logger.info(f"[{i}/{len(combinations)}] Scraping {year} {make} {model}")

                try:
                    result = scraper.scrape_car_model(make, model, year)

                    if validate_and_summarize_results(result, make, model, year):
                        successful += 1
                        # Export to 4-table format if requested
                        if args.export_db and db_output_dir:
                            export_to_4table_format(result, make, model, year, db_output_dir)
                        # Scrape reviews with same driver session
                        if reviews_scraper:
                            reviews_scraper.scrape_reviews(make, model, year)
                    else:
                        failed += 1
                        failed_models.append(f"{year} {make} {model}")

                except Exception as e:
                    logger.error(f"Failed to scrape {year} {make} {model}: {e}")
                    failed += 1
                    failed_models.append(f"{year} {make} {model}")

                    if not _is_driver_alive(scraper):
                        scraper, reviews_scraper = _recreate_scraper(
                            scraper, headless, args.with_reviews
                        )

        finally:
            scraper.close()

        logger.info(f"\n=== {mode_name} Batch Scraping Complete ===")
        logger.info(f"   Successful: {successful}/{len(combinations)}")
        logger.info(f"   Failed: {failed}")
        logger.info(f"   CSV data saved to: {settings.CSV_DATA_DIR / 'all_cars.csv'}")
        if args.export_db:
            logger.info(f"   4-table data saved to: {db_output_dir}")

        if failed_models:
            logger.info(f"   Failed models:")
            for fm in failed_models[:10]:
                logger.info(f"      - {fm}")
            if len(failed_models) > 10:
                logger.info(f"      ... and {len(failed_models) - 10} more")

        return successful > 0

    else:
        # Example: Scrape Audi A3 2017
        logger.info("No arguments provided, running example (Audi A3 2017)...")
        make, model, year = "Audi", "A3", "2017"
        if args.with_reviews:
            results, _ = scrape_single_model_with_reviews(make, model, year, headless)
        else:
            results = scrape_single_model(make, model, year, headless)

    if results:
        logger.info("Scraping completed successfully!")
        logger.info(f"CSV data saved to: {settings.CSV_DATA_DIR / 'all_cars.csv'}")

        # Export to 4-table format if requested
        if args.export_db and db_output_dir and make and model and year:
            export_success = export_to_4table_format(results, make, model, year, db_output_dir)
            if export_success:
                logger.info(f"4-table data saved to: {db_output_dir}")
            else:
                logger.error("Failed to export to 4-table format")
                return False

        return True
    else:
        logger.error("Scraping failed or no data collected")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
