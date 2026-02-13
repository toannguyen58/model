"""
Package entry point for running as `python -m kbb_scraper`.

Usage:
    python -m kbb_scraper --make Toyota --model Camry --year 2020
    python -m kbb_scraper --url "https://www.kbb.com/toyota/camry/2020/specs/"
    python -m kbb_scraper --test
    python -m kbb_scraper --batch
    python -m kbb_scraper --make Toyota --model Camry --year 2020 --with-reviews
    python -m kbb_scraper --test --with-reviews
"""
from kbb_scraper.main import main
import sys

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
