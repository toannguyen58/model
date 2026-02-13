"""
Scraper for KBB consumer reviews and expert review / recommendation data.

Can operate standalone or reuse an existing Selenium WebDriver from the
specifications scraper so that both datasets are collected in the same
browser session.

Usage (standalone):
    scraper = KBBReviewsScraper(headless=True)
    review_data = scraper.scrape_reviews("Toyota", "Camry", "2020")
    scraper.close()

Usage (sharing driver with specs scraper):
    specs_scraper = KBBResearchScraper(headless=True)
    specs = specs_scraper.scrape_car_model("Toyota", "Camry", "2020")

    reviews_scraper = KBBReviewsScraper(driver=specs_scraper.driver)
    review_data = reviews_scraper.scrape_reviews("Toyota", "Camry", "2020")
    # Do NOT call reviews_scraper.close() — the specs scraper owns the driver.
"""
import csv
import json
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from kbb_scraper.config import settings
from kbb_scraper.drivers import DriverManager
from kbb_scraper.models.review_data import ConsumerReview, ExpertReview, ReviewData
from kbb_scraper.parsers.review_parser import ReviewParser

logger = logging.getLogger(__name__)


class KBBReviewsScraper:
    """Scraper for KBB consumer reviews and expert review data."""

    def __init__(self, driver: Optional[WebDriver] = None, headless: bool = True):
        """
        Args:
            driver: An existing Selenium WebDriver to reuse.  When provided the
                    scraper will *not* close the driver on ``close()``.
            headless: Only used when *driver* is ``None`` (creates its own).
        """
        if driver is not None:
            self.driver = driver
            self._owns_driver = False
        else:
            self._driver_manager = DriverManager(headless=headless)
            self.driver = self._driver_manager.setup_driver()
            self._owns_driver = True

        self._parser = ReviewParser()

    # ------------------------------------------------------------------ #
    #  Navigation helpers
    # ------------------------------------------------------------------ #

    def _navigate(self, url: str) -> bool:
        """Navigate to *url*, return ``True`` if the page loaded OK."""
        logger.info(f"Navigating to: {url}")
        try:
            self.driver.get(url)
            time.sleep(3)

            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            if "404" in self.driver.title or "Page Not Found" in self.driver.page_source:
                logger.warning(f"Page not found: {url}")
                return False

            # Extra settle time for JS-rendered content
            time.sleep(2)
            return True

        except TimeoutException:
            logger.error(f"Timeout loading: {url}")
            return False
        except Exception as e:
            logger.error(f"Error navigating to {url}: {e}")
            return False

    # ------------------------------------------------------------------ #
    #  Scrape consumer reviews
    # ------------------------------------------------------------------ #

    def scrape_consumer_reviews(self, make: str, model: str, year: str) -> Optional[ConsumerReview]:
        """Navigate to the consumer-reviews page and extract review data."""
        url = f"{settings.KBB_BASE_URL}/{make.lower()}/{model.lower()}/{year}/consumer-reviews/"

        if not self._navigate(url):
            return None

        parsed = self._parser.parse_consumer_reviews_page(self.driver.page_source)

        if not parsed.get("overall_rating"):
            logger.warning(f"No consumer review data found for {year} {make} {model}")
            return None

        review = ConsumerReview(
            overall_rating=parsed.get("overall_rating"),
            review_count=parsed.get("review_count"),
            recommend_percentage=parsed.get("recommend_percentage"),
            star_distribution=parsed.get("star_distribution", {}),
            category_ratings=parsed.get("category_ratings", {}),
        )

        logger.info(
            f"Consumer review: {review.overall_rating}/5 "
            f"({review.review_count} reviews, "
            f"{review.recommend_percentage}% recommend)"
        )
        if review.star_distribution:
            logger.info(f"  Star distribution: {review.star_distribution}")
        if review.category_ratings:
            logger.info(f"  Category ratings: {review.category_ratings}")

        return review

    # ------------------------------------------------------------------ #
    #  Scrape expert review / recommendations
    # ------------------------------------------------------------------ #

    def scrape_expert_review(self, make: str, model: str, year: str) -> Optional[ExpertReview]:
        """Navigate to the model overview page and extract expert review data."""
        url = f"{settings.KBB_BASE_URL}/{make.lower()}/{model.lower()}/{year}/"

        if not self._navigate(url):
            return None

        parsed = self._parser.parse_expert_review_page(self.driver.page_source)

        review = ExpertReview(
            expert_rating=parsed.get("expert_rating"),
            ranking=parsed.get("ranking"),
            pros=parsed.get("pros", []),
            cons=parsed.get("cons", []),
        )

        if review.expert_rating:
            logger.info(f"Expert rating: {review.expert_rating}/5")
        if review.ranking:
            logger.info(f"Ranking: {review.ranking}")
        if review.pros:
            logger.info(f"Pros ({len(review.pros)}): {review.pros}")
        if review.cons:
            logger.info(f"Cons ({len(review.cons)}): {review.cons}")

        # Return None only if we got absolutely nothing
        if not any([review.expert_rating, review.ranking, review.pros, review.cons]):
            logger.warning(f"No expert review data found for {year} {make} {model}")
            return None

        return review

    # ------------------------------------------------------------------ #
    #  Combined scrape
    # ------------------------------------------------------------------ #

    def scrape_reviews(self, make: str, model: str, year: str) -> ReviewData:
        """
        Scrape both consumer reviews and expert review for a vehicle.

        Always returns a ``ReviewData`` instance (individual fields may be
        ``None`` if the corresponding page had no data).
        """
        logger.info(f"=== Starting review scrape for {year} {make} {model} ===")

        consumer_review = self.scrape_consumer_reviews(make, model, year)
        expert_review = self.scrape_expert_review(make, model, year)

        review_data = ReviewData(
            make=make,
            model=model,
            year=year,
            consumer_review=consumer_review,
            expert_review=expert_review,
        )

        self.save_results(review_data, make, model, year)
        return review_data

    # ------------------------------------------------------------------ #
    #  Persistence
    # ------------------------------------------------------------------ #

    # ------------------------------------------------------------------ #
    #  CSV schema
    # ------------------------------------------------------------------ #

    REVIEW_CSV_COLUMNS = [
        "make", "model", "year",
        "consumer_overall_rating", "consumer_review_count", "consumer_recommend_pct",
        "star_5_pct", "star_4_pct", "star_3_pct", "star_2_pct", "star_1_pct",
        "rating_value", "rating_performance", "rating_quality",
        "rating_comfort", "rating_reliability", "rating_styling",
        "expert_rating", "expert_ranking",
        "pros", "cons",
    ]

    # ------------------------------------------------------------------ #
    #  Persistence
    # ------------------------------------------------------------------ #

    def save_results(self, review_data: ReviewData, make: str, model: str, year: str):
        """Save review data to both JSON and CSV."""
        self._save_json(review_data, make, model, year)
        self._save_csv(review_data, make, model, year)

    def _save_json(self, review_data: ReviewData, make: str, model: str, year: str):
        """Save review data to ``data/raw/{make}_{model}_reviews.json``."""
        try:
            output_dir = Path(settings.RAW_DATA_DIR)
            output_dir.mkdir(parents=True, exist_ok=True)

            filename = f"{make}_{model}_reviews.json"
            filepath = output_dir / filename

            # Load existing data
            if filepath.exists():
                with open(filepath, "r", encoding="utf-8") as f:
                    combined = json.load(f)
            else:
                combined = {
                    "make": make,
                    "model": model,
                    "years": {},
                }

            combined["years"][year] = review_data.to_dict()
            combined["last_updated"] = datetime.now().isoformat()

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(combined, f, indent=2, ensure_ascii=False)

            logger.info(f"Review JSON saved to: {filepath}")

        except Exception as e:
            logger.error(f"Error saving review JSON: {e}")

    def _save_csv(self, review_data: ReviewData, make: str, model: str, year: str):
        """Append one row to ``data/csv/all_reviews.csv``."""
        try:
            csv_path = Path(settings.CSV_DATA_DIR) / "all_reviews.csv"
            csv_path.parent.mkdir(parents=True, exist_ok=True)

            row = self._flatten_review(review_data)
            file_exists = csv_path.exists()

            with open(csv_path, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(
                    f, fieldnames=self.REVIEW_CSV_COLUMNS, extrasaction="ignore"
                )
                if not file_exists:
                    writer.writeheader()
                writer.writerow(row)

            logger.info(f"Review CSV appended to: {csv_path}")

        except Exception as e:
            logger.error(f"Error saving review CSV: {e}")

    @staticmethod
    def _flatten_review(review_data: ReviewData) -> dict:
        """Flatten a ReviewData instance into a single CSV row dict."""
        row: dict = {
            "make": review_data.make,
            "model": review_data.model,
            "year": review_data.year,
        }

        cr = review_data.consumer_review
        if cr:
            row["consumer_overall_rating"] = cr.overall_rating
            row["consumer_review_count"] = cr.review_count
            row["consumer_recommend_pct"] = cr.recommend_percentage
            for star in range(5, 0, -1):
                row[f"star_{star}_pct"] = cr.star_distribution.get(star)
            for cat in ("value", "performance", "quality", "comfort",
                        "reliability", "styling"):
                row[f"rating_{cat}"] = cr.category_ratings.get(cat)

        er = review_data.expert_review
        if er:
            row["expert_rating"] = er.expert_rating
            row["expert_ranking"] = er.ranking
            row["pros"] = " | ".join(er.pros) if er.pros else ""
            row["cons"] = " | ".join(er.cons) if er.cons else ""

        return row

    # ------------------------------------------------------------------ #
    #  Lifecycle
    # ------------------------------------------------------------------ #

    def close(self):
        """Close the browser — only when this instance created its own driver."""
        if self._owns_driver and hasattr(self, "_driver_manager"):
            self._driver_manager.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
