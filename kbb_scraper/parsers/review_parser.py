"""
Parser for KBB consumer reviews and expert review HTML pages.

Extracts structured data from:
  - JSON-LD (schema.org) embedded in the page
  - HTML elements for visual data (star bars, category ratings, etc.)
"""
import json
import re
import logging
from typing import Dict, List, Optional, Any, Tuple

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class ReviewParser:
    """Parses KBB review pages to extract consumer and expert review data."""

    # Known category rating labels on the consumer reviews page
    KNOWN_CATEGORIES = ["value", "performance", "quality", "comfort", "reliability", "styling"]

    # ------------------------------------------------------------------ #
    #  Public API
    # ------------------------------------------------------------------ #

    def parse_consumer_reviews_page(self, page_source: str) -> Dict[str, Any]:
        """
        Parse a KBB consumer reviews page and return extracted data.

        Returns dict with keys:
            overall_rating, review_count, recommend_percentage,
            star_distribution, category_ratings
        """
        soup = BeautifulSoup(page_source, "html.parser")
        result: Dict[str, Any] = {}

        # 1. JSON-LD  ─  overall rating & review count
        jsonld_data = self._extract_jsonld(soup)
        agg = self._find_aggregate_rating(jsonld_data)
        if agg:
            try:
                result["overall_rating"] = float(agg["ratingValue"])
            except (KeyError, TypeError, ValueError):
                pass
            try:
                result["review_count"] = int(agg["reviewCount"])
            except (KeyError, TypeError, ValueError):
                pass

        # 2. Recommend percentage
        result["recommend_percentage"] = self._extract_recommend_percentage(soup)

        # 3. Star distribution
        result["star_distribution"] = self._extract_star_distribution(soup)

        # 4. Category ratings
        result["category_ratings"] = self._extract_category_ratings(soup)

        return result

    def parse_expert_review_page(self, page_source: str) -> Dict[str, Any]:
        """
        Parse a KBB model overview page for expert review / recommendation data.

        Returns dict with keys:
            expert_rating, ranking, pros, cons
        """
        soup = BeautifulSoup(page_source, "html.parser")
        result: Dict[str, Any] = {}

        jsonld_data = self._extract_jsonld(soup)

        # Expert rating
        review = self._find_expert_review(jsonld_data)
        if review:
            rating_obj = review.get("reviewRating", {})
            try:
                result["expert_rating"] = float(rating_obj["ratingValue"])
            except (KeyError, TypeError, ValueError):
                pass

        # Pros / cons
        pros, cons = self._find_pros_cons(jsonld_data)
        result["pros"] = pros
        result["cons"] = cons

        # Ranking
        result["ranking"] = self._extract_ranking(soup, jsonld_data)

        return result

    # ------------------------------------------------------------------ #
    #  JSON-LD helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _extract_jsonld(soup: BeautifulSoup) -> List[Dict]:
        """Extract all JSON-LD blocks from the page."""
        scripts = soup.find_all("script", type="application/ld+json")
        data: List[Dict] = []
        for script in scripts:
            try:
                parsed = json.loads(script.string)
                if isinstance(parsed, list):
                    data.extend(parsed)
                else:
                    data.append(parsed)
            except (json.JSONDecodeError, TypeError):
                continue
        return data

    @staticmethod
    def _find_aggregate_rating(jsonld_data: List[Dict]) -> Optional[Dict]:
        """Locate aggregateRating in JSON-LD data."""
        for item in jsonld_data:
            if "aggregateRating" in item:
                return item["aggregateRating"]
            if "@graph" in item:
                for node in item["@graph"]:
                    if "aggregateRating" in node:
                        return node["aggregateRating"]
        return None

    @staticmethod
    def _find_expert_review(jsonld_data: List[Dict]) -> Optional[Dict]:
        """Locate the expert Review object in JSON-LD data."""
        for item in jsonld_data:
            if item.get("@type") == "Review":
                return item
            if "review" in item:
                review = item["review"]
                if isinstance(review, list):
                    return review[0] if review else None
                return review
            if "@graph" in item:
                for node in item["@graph"]:
                    if node.get("@type") == "Review":
                        return node
        return None

    @staticmethod
    def _find_pros_cons(jsonld_data: List[Dict]) -> Tuple[List[str], List[str]]:
        """Extract positive / negative notes from JSON-LD ItemList structures."""
        pros: List[str] = []
        cons: List[str] = []

        for item in jsonld_data:
            nodes = [item]
            if "@graph" in item:
                nodes.extend(item["@graph"])

            for node in nodes:
                if node.get("@type") != "ItemList":
                    continue
                name = (node.get("name") or "").lower()
                elements = node.get("itemListElement", [])
                texts: List[str] = []
                for elem in elements:
                    if isinstance(elem, dict):
                        text = elem.get("name", "")
                        if not text:
                            nested = elem.get("item", {})
                            if isinstance(nested, dict):
                                text = nested.get("name", "")
                        if text:
                            texts.append(text)

                if "positive" in name or "pro" in name:
                    pros = texts
                elif "negative" in name or "con" in name:
                    cons = texts

        return pros, cons

    # ------------------------------------------------------------------ #
    #  HTML element extraction
    # ------------------------------------------------------------------ #

    @staticmethod
    def _extract_recommend_percentage(soup: BeautifulSoup) -> Optional[int]:
        """Extract the 'XX% Recommend this vehicle' value."""
        # Strategy 1: text node containing "Recommend this vehicle"
        for text_node in soup.find_all(string=re.compile(r"Recommend\s+this\s+vehicle", re.I)):
            parent = text_node.parent
            if parent:
                container = parent.parent if parent.parent else parent
                text = container.get_text()
                match = re.search(r"(\d+)\s*%", text)
                if match:
                    return int(match.group(1))

        # Strategy 2: broader text scan
        full_text = soup.get_text()
        match = re.search(r"(\d+)\s*%\s*Recommend", full_text, re.I)
        if match:
            return int(match.group(1))

        return None

    @staticmethod
    def _extract_star_distribution(soup: BeautifulSoup) -> Dict[int, int]:
        """
        Extract star rating distribution.

        Looks for the pattern where each row contains a star number (1-5)
        and a percentage value.
        """
        distribution: Dict[int, int] = {}

        full_text = soup.get_text(separator="\n")
        lines = [ln.strip() for ln in full_text.split("\n") if ln.strip()]

        for i, line in enumerate(lines):
            if not re.match(r"^[1-5]$", line):
                continue
            star = int(line)
            # Scan the next few lines for a percentage
            for j in range(i + 1, min(i + 5, len(lines))):
                pct_match = re.search(r"(\d+)\s*%", lines[j])
                if pct_match:
                    distribution[star] = int(pct_match.group(1))
                    break

        # Fallback: aria-label based detection
        if not distribution:
            for star in range(1, 6):
                elems = soup.find_all(attrs={"aria-label": re.compile(rf"{star}\s*star", re.I)})
                for elem in elems:
                    match = re.search(r"(\d+)\s*%", elem.get_text())
                    if match:
                        distribution[star] = int(match.group(1))

        return distribution

    def _extract_category_ratings(self, soup: BeautifulSoup) -> Dict[str, float]:
        """
        Extract category ratings (Value, Performance, Quality, etc.).

        Each category label is followed (in nearby text) by its numeric rating.
        """
        categories: Dict[str, float] = {}

        full_text = soup.get_text(separator="\n")
        lines = [ln.strip() for ln in full_text.split("\n") if ln.strip()]

        for i, line in enumerate(lines):
            line_lower = line.lower()
            for cat in self.KNOWN_CATEGORIES:
                if line_lower != cat:
                    continue
                # Look forward only — the numeric rating follows the label
                for j in range(i + 1, min(i + 5, len(lines))):
                    rating_match = re.match(r"^(\d+\.?\d*)$", lines[j])
                    if rating_match:
                        val = float(rating_match.group(1))
                        if 0 < val <= 5.0:
                            categories[cat] = val
                            break

        return categories

    @staticmethod
    def _extract_ranking(soup: BeautifulSoup, jsonld_data: List[Dict]) -> Optional[str]:
        """Extract ranking text like '#2 in Best Midsize Cars of 2020'."""
        # Check JSON-LD first
        for item in jsonld_data:
            nodes = [item]
            if "@graph" in item:
                nodes.extend(item["@graph"])
            for node in nodes:
                if node.get("@type") == "Review":
                    # Some KBB pages embed ranking in the review description
                    desc = node.get("description", "")
                    match = re.search(r"(#\d+\s+in\s+[^.\"'\n]+)", desc)
                    if match:
                        return match.group(1).strip()

        # Fallback: scan HTML text
        full_text = soup.get_text()
        match = re.search(r"(#\d+\s+in\s+[^.\"'\n]+)", full_text)
        if match:
            return match.group(1).strip()

        return None
