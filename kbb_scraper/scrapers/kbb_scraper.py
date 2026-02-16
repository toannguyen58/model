# kbb_scraper/scrapers/kbb_scraper.py
import time
import re
import logging
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from kbb_scraper.config import settings
from kbb_scraper.drivers import DriverManager

logger = logging.getLogger(__name__)

# Patterns that indicate the page is a block/CAPTCHA rather than real content
_BLOCK_INDICATORS = [
    "access denied",
    "please verify you are a human",
    "are you a robot",
    "captcha",
    "unusual traffic",
    "too many requests",
    "rate limit",
    "blocked",
    "security check",
    "pardon our interruption",
    "just a moment",           # Cloudflare challenge
    "checking your browser",   # Cloudflare challenge
    "enable javascript and cookies",
]


def _is_blocked(page_source: str, title: str) -> bool:
    """Return True if the page looks like a CAPTCHA / block page."""
    combined = (title + " " + page_source[:5000]).lower()
    return any(indicator in combined for indicator in _BLOCK_INDICATORS)


class KBBResearchScraper:
    """Scraper for KBB research data with support for multiple body types"""

    def __init__(self, headless: bool = True):
        """Initialize the scraper using DriverManager"""
        self._driver_manager = DriverManager(headless=headless)
        self.driver = self._driver_manager.setup_driver()
        
    def navigate_to_car_model(self, make: str, model: str, year: str) -> str:
        """Navigate to the KBB page for a specific car model.

        Returns:
            "specs"     - normal specs comparison page loaded
            "overview"  - redirected to overview page (no /specs/ in URL)
            "not_found" - car does not exist (404 or no content)
            "blocked"   - CAPTCHA or rate-limit page detected
        """
        url = f"https://www.kbb.com/{make.lower()}/{model.lower()}/{year}/specs/"
        logger.info(f"Navigating to: {url}")

        try:
            self.driver.get(url)
            time.sleep(3)  # Initial page load

            # Check for CAPTCHA / block pages BEFORE other checks
            if _is_blocked(self.driver.page_source, self.driver.title):
                logger.error(f"BLOCKED / CAPTCHA detected at: {url}")
                self._save_debug_html(f"blocked_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html")
                return "blocked"

            # Check if page loaded successfully
            if "404" in self.driver.title or "Page Not Found" in self.driver.page_source:
                logger.error(f"Page not found: {url}")
                return "not_found"

            # Wait for main content to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # Check if we were redirected away from /specs/
            current_url = self.driver.current_url
            if not current_url.rstrip('/').endswith('/specs'):
                logger.info(f"Redirected to overview page: {current_url}")
                return "overview"

            # Wait for specs table to be present (primary indicator of loaded content)
            try:
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.ID, "compare-trim-tables"))
                )
                logger.info("Specs table loaded successfully")
            except TimeoutException:
                logger.warning("compare-trim-tables not found - checking for alternative content")
                # Check if any table exists
                tables = self.driver.find_elements(By.TAG_NAME, "table")
                if tables:
                    logger.info(f"Found {len(tables)} table(s) on page")
                else:
                    logger.error(f"No tables found on page - car does not exist: {year} {make} {model}")
                    return "not_found"

            return "specs"

        except Exception as e:
            logger.error(f"Error navigating to {url}: {e}")
            return "not_found"
    
    def get_all_body_types(self, wait_time: int = 10) -> List[str]:
        """Get ALL available body types for the current model - FIXED"""
        body_types = []
        
        try:
            # Wait for body type container
            WebDriverWait(self.driver, wait_time).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'argo-flexbox-content')]"))
            )
            
            # Find all body type elements using the class pattern from HTML
            # Looking for elements with classes like "css-17dykbp e1f04f5s0"
            body_type_xpaths = [
                "//div[contains(@class, 'css-17dykbp')]",
                "//button[contains(@class, 'body-type')]",
                "//div[contains(@class, 'bodyType')]",
                "//button[@role='tab']",
                "//div[@role='tab']"
            ]
            
            for xpath in body_type_xpaths:
                elements = self.driver.find_elements(By.XPATH, xpath)
                if elements:
                    logger.info(f"Found {len(elements)} body type elements with xpath: {xpath}")
                    
                    for element in elements:
                        try:
                            # Get body type name
                            body_type = self._extract_body_type_name(element)
                            
                            if body_type and body_type not in body_types:
                                body_types.append(body_type)
                                logger.debug(f"Found body type: {body_type}")
                                
                        except Exception as e:
                            logger.debug(f"Could not extract from element: {e}")
                            continue
                    
                    if body_types:
                        break
            
            # If no body types found with specific selectors, try a more general approach
            if not body_types:
                logger.info("Trying alternative body type detection...")
                
                # Look for any clickable elements that might be body types
                clickable_elements = self.driver.find_elements(
                    By.XPATH, 
                    "//div[@role='button'] | //button | //div[@tabindex]"
                )
                
                for element in clickable_elements:
                    try:
                        # Check if element looks like a body type selector
                        text = element.text.strip()
                        if text and len(text) < 20:  # Body type names are usually short
                            # Check if it's a common body type
                            common_types = ['sedan', 'suv', 'coupe', 'hatchback', 
                                          'convertible', 'wagon', 'truck', 'van']
                            if any(body_type in text.lower() for body_type in common_types):
                                if text not in body_types:
                                    body_types.append(text)
                    except Exception:
                        continue

        except TimeoutException:
            logger.warning("Body type container not found, might be single body type model")
        except Exception as e:
            logger.error(f"Error finding body types: {e}")
        
        # If we still don't have body types, assume it's a single body type model
        if not body_types:
            body_types = ["Default"]
            logger.info("Assuming single body type model")
        
        logger.info(f"Found {len(body_types)} body type(s): {body_types}")
        return body_types
    
    def _extract_body_type_name(self, element) -> str:
        """Extract body type name from element"""
        # Try different attributes in order of reliability
        sources = [
            ("aria-label", element.get_attribute("aria-label")),
            ("text", element.text),
            ("title", element.get_attribute("title")),
            ("data-testid", element.get_attribute("data-testid")),
            ("data-value", element.get_attribute("data-value")),
            ("class", element.get_attribute("class"))
        ]
        
        for source_name, value in sources:
            if value:
                cleaned = self._clean_body_type_name(value)
                if cleaned:
                    logger.debug(f"Got body type from {source_name}: {value} -> {cleaned}")
                    return cleaned
        
        return ""
    
    def _clean_body_type_name(self, name: str) -> str:
        """Clean and standardize body type names"""
        if not name:
            return ""
        
        # Remove HTML entities and extra whitespace
        name = re.sub(r'\s+', ' ', name).strip()
        
        # Remove common indicators
        remove_patterns = [
            r'\(\d+\)',  # (2), (3) etc
            r'\d+$',     # Trailing numbers
            r'selected', 
            r'unselected',
            r'active',
            r'inactive',
            r'tab',
            r'button',
            r'^\d+\s*',  # Leading numbers
        ]
        
        for pattern in remove_patterns:
            name = re.sub(pattern, '', name, flags=re.IGNORECASE)
        
        # Standardize common names
        name_lower = name.lower()
        body_type_mapping = {
            'sedan': 'Sedan',
            'suv': 'SUV',
            'coupe': 'Coupe',
            'convertible': 'Convertible',
            'hatchback': 'Hatchback',
            'wagon': 'Wagon',
            'truck': 'Truck',
            'van': 'Van',
            'minivan': 'Minivan',
            'pickup': 'Pickup Truck',
            'sport utility': 'SUV',
            '4dr': '4-Door',
            '2dr': '2-Door'
        }
        
        for key, value in body_type_mapping.items():
            if key in name_lower:
                return value
        
        # Clean up and capitalize
        name = name.strip(' -:')
        if name:
            # Capitalize first letter of each word
            name = ' '.join(word.capitalize() for word in name.split())
        
        return name
    
    def _get_current_content_signature(self) -> str:
        """Get a signature of current page content to detect changes"""
        try:
            # Get first trim name or first few cell values as signature
            h3_elements = self.driver.find_elements(By.TAG_NAME, "h3")
            for h3 in h3_elements[:5]:
                text = h3.text.strip()
                if text and len(text) > 5:
                    return text
            # Fallback: get first table cell content
            cells = self.driver.find_elements(By.CSS_SELECTOR, "table td")
            if cells:
                return cells[0].text.strip()
        except Exception:
            pass
        return ""

    def select_body_type(self, body_type_name: str) -> bool:
        """Click on a specific body type tab/button and wait for content to change"""
        try:
            body_type_lower = body_type_name.lower()

            # Capture current content BEFORE clicking to detect change later
            old_signature = self._get_current_content_signature()
            logger.debug(f"Content signature before click: {old_signature[:50] if old_signature else 'empty'}")

            # Try different strategies to find and click the body type
            selectors = [
                f"//*[@role='tab' and contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{body_type_lower}')]",
                f"//*[@role='tablist']//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{body_type_lower}')]",
                f"//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{body_type_lower}')]",
                f"//*[contains(@aria-label, '{body_type_name}') or contains(@aria-label, '{body_type_lower}')]",
                f"//div[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{body_type_lower}')]",
            ]

            clicked = False
            for selector in selectors:
                if clicked:
                    break
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        try:
                            # Check if already selected
                            aria_selected = element.get_attribute("aria-selected")
                            if aria_selected == "true":
                                logger.debug(f"Body type '{body_type_name}' is already selected")
                                return True

                            # Check if clickable
                            if element.is_displayed() and element.is_enabled():
                                # Click the element
                                self.driver.execute_script("arguments[0].click();", element)
                                logger.info(f"Clicked on body type: {body_type_name}")
                                clicked = True
                                break
                        except Exception as e:
                            logger.debug(f"Could not click element: {e}")
                            continue

                except (TimeoutException, NoSuchElementException):
                    continue

            if not clicked:
                logger.warning(f"Could not find/click body type: {body_type_name}")
                return False

            # CRITICAL: Wait for content to ACTUALLY CHANGE, not just exist
            max_wait = 10
            wait_interval = 0.5
            waited = 0

            while waited < max_wait:
                time.sleep(wait_interval)
                waited += wait_interval

                new_signature = self._get_current_content_signature()

                # Check if content has changed
                if new_signature and new_signature != old_signature:
                    logger.info(f"Content changed after {waited}s - new signature: {new_signature[:50]}")
                    # Give a bit more time for full render
                    time.sleep(0.5)
                    return True

            logger.warning(f"Content did not change after clicking {body_type_name} (waited {max_wait}s)")
            # Return True anyway - maybe content was already showing or detection failed
            return True

        except Exception as e:
            logger.error(f"Error selecting body type '{body_type_name}': {e}")
            return False
    
    def get_trim_names(self) -> List[str]:
        """Extract trim names from the page - universal approach"""
        trim_names = []

        try:
            # Debug: Log all h3 elements to understand page structure
            all_h3 = self.driver.find_elements(By.TAG_NAME, "h3")
            logger.debug(f"Found {len(all_h3)} h3 elements on page")
            for i, h3 in enumerate(all_h3[:10]):
                logger.debug(f"  h3[{i}]: {h3.text.strip()[:50]}")

            # Strategy 1: Find trim cards by looking for parent containers with multiple children
            # Trim names are usually in repeating card structures
            card_containers = self.driver.find_elements(By.XPATH,
                "//div[.//a[contains(@href, 'pricing') or contains(text(), 'Pricing')]]//h3 | "
                "//div[.//button[contains(text(), 'Pricing')]]//h3"
            )
            for elem in card_containers:
                text = elem.text.strip()
                if text and text not in trim_names and len(text) > 5:
                    if text.lower() not in ['save', 'see pricing', 'compare', 'specifications']:
                        trim_names.append(text)

            # Strategy 2: Look for h3 elements that are siblings (same parent = card layout)
            if not trim_names:
                h3_elements = self.driver.find_elements(By.CSS_SELECTOR, "h3")
                for h3 in h3_elements:
                    text = h3.text.strip()
                    # Filter: trim names usually have make/model info or body style
                    if text and len(text) > 5 and len(text) < 60:
                        # Exclude common non-trim text
                        excluded = ['save', 'pricing', 'compare', 'specification', 'feature',
                                   'overview', 'review', 'research', 'price', 'msrp']
                        if not any(ex in text.lower() for ex in excluded):
                            if text not in trim_names:
                                trim_names.append(text)

            # Strategy 3: Look in the comparison table header area
            if not trim_names:
                # The compare-trim-tables might have trim info in a different structure
                try:
                    table = self.driver.find_element(By.ID, "compare-trim-tables")
                    # Look for any text elements in the table header area
                    header_texts = table.find_elements(By.XPATH, ".//thead//*[string-length(text()) > 5]")
                    for elem in header_texts:
                        text = elem.text.strip()
                        if text and text not in trim_names:
                            if text.lower() not in ['save', 'see pricing', 'specifications']:
                                trim_names.append(text)
                except Exception:
                    pass

            if trim_names:
                logger.info(f"Found {len(trim_names)} trim names: {trim_names}")
            else:
                logger.warning("No trim names found - check page structure")

        except Exception as e:
            logger.error(f"Error getting trim names: {e}")
            logger.debug(traceback.format_exc())

        return trim_names
    
    def get_specifications(self) -> List[Dict[str, Any]]:
        """Extract specifications from the page - universal approach"""
        specs = []

        try:
            # Find the compare-trim-tables
            spec_table = None
            try:
                spec_table = self.driver.find_element(By.ID, "compare-trim-tables")
                logger.info("Found compare-trim-tables by ID")
            except NoSuchElementException:
                # Fallback: find largest table
                tables = self.driver.find_elements(By.TAG_NAME, "table")
                if tables:
                    spec_table = max(tables, key=lambda t: len(t.find_elements(By.TAG_NAME, "tr")))
                    logger.info("Using largest table as spec table")

            if not spec_table:
                logger.error("No spec table found")
                return specs

            # Get table HTML in one call and parse locally (much faster than per-cell Selenium calls)
            table_html = spec_table.get_attribute("innerHTML")
            soup = BeautifulSoup(table_html, "html.parser")
            rows = soup.find_all("tr")
            logger.info(f"Table has {len(rows)} rows total")

            # Debug first few rows
            for i, row in enumerate(rows[:3]):
                cells = row.find_all("td")
                th_cells = row.find_all("th")
                logger.debug(f"Row {i}: {len(th_cells)} th, {len(cells)} td")
                if cells:
                    logger.debug(f"  First cell text: '{cells[0].get_text(strip=True)[:30]}'")

            # Extract specs from all rows
            skip_labels = {'specifications', 'features', 'compare', 'save', 'see pricing', ''}
            skip_prefixes = ('save ', 'see ')

            for row in rows:
                try:
                    th_cells = row.find_all("th")
                    cells = row.find_all("td")

                    if th_cells and cells:
                        all_cells = th_cells + cells
                    elif cells:
                        all_cells = cells
                    elif th_cells:
                        all_cells = th_cells
                    else:
                        all_cells = row.find_all("div", attrs={"role": "cell"})

                    if not all_cells:
                        continue

                    cell_texts = [c.get_text(strip=True) for c in all_cells]

                    if len(cell_texts) < 2:
                        continue

                    # First non-empty cell is the spec name
                    spec_name = None
                    value_start_idx = 0

                    for idx, text in enumerate(cell_texts):
                        if text and len(text) > 1:
                            spec_name = text
                            value_start_idx = idx + 1
                            break

                    if not spec_name:
                        continue

                    name_lower = spec_name.lower()
                    if name_lower in skip_labels or name_lower.startswith(skip_prefixes):
                        continue

                    values = [text if text else "N/A" for text in cell_texts[value_start_idx:]]

                    if values:
                        specs.append({
                            'label': spec_name,
                            'values': values
                        })

                except Exception as e:
                    logger.debug(f"Error parsing row: {e}")
                    continue

            logger.info(f"Extracted {len(specs)} specifications")

            if specs:
                logger.info(f"Sample specs: {[s['label'] for s in specs[:5]]}")
            else:
                logger.warning("No specs extracted - dumping table HTML structure")
                for i, row in enumerate(rows[:3]):
                    logger.warning(f"Row {i} HTML: {str(row)[:200]}")

        except Exception as e:
            logger.error(f"Error getting specifications: {e}")
            logger.debug(traceback.format_exc())

        return specs
    
    def _save_debug_html(self, filename: str):
        """Save current page HTML for debugging"""
        try:
            debug_dir = Path(settings.RAW_DATA_DIR) / "debug"
            debug_dir.mkdir(parents=True, exist_ok=True)
            filepath = debug_dir / filename
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            logger.debug(f"Saved debug HTML to: {filepath}")
        except Exception as e:
            logger.debug(f"Could not save debug HTML: {e}")

    def _clean_trim_name(self, raw_name: str) -> str:
        """Clean trim name by removing 'Save X of Y' prefix"""
        if not raw_name:
            return ""
        # Remove "Save\nX of Y\n" pattern from start
        cleaned = re.sub(r'^Save\s*\n?\d+\s+of\s+\d+\s*\n?', '', raw_name, flags=re.IGNORECASE)
        return cleaned.strip()

    def scrape_current_body_type_data(self) -> Dict[str, Any]:
        """Scrape data for the currently selected body type"""
        data = {
            'trim_names': [],
            'specifications': []
        }

        try:
            # Wait a moment for any dynamic content to load
            time.sleep(1)

            # Check if compare-trim-tables exists
            try:
                table = self.driver.find_element(By.ID, "compare-trim-tables")
                logger.info(f"Found compare-trim-tables, displayed: {table.is_displayed()}")

                # Debug: log table structure
                tbody = table.find_elements(By.TAG_NAME, "tbody")
                thead = table.find_elements(By.TAG_NAME, "thead")
                logger.debug(f"Table has {len(thead)} thead, {len(tbody)} tbody")

            except NoSuchElementException:
                logger.warning("compare-trim-tables not found - trying to find any table")
                tables = self.driver.find_elements(By.TAG_NAME, "table")
                logger.info(f"Found {len(tables)} table(s) on page")

            # Get specifications first
            all_specs = self.get_specifications()

            # Extract trim names from the first specification row and clean them
            if all_specs and len(all_specs) > 0:
                first_spec = all_specs[0]
                # The label is the first trim name, values are the rest
                trim_names = []
                # Add the label (first trim)
                cleaned_label = self._clean_trim_name(first_spec.get('label', ''))
                if cleaned_label:
                    trim_names.append(cleaned_label)
                # Add the values (other trims), excluding "N/A"
                for val in first_spec.get('values', []):
                    cleaned_val = self._clean_trim_name(val)
                    if cleaned_val and cleaned_val != "N/A":
                        trim_names.append(cleaned_val)
                data['trim_names'] = trim_names

            # Drop the first element (trim names row); "See Pricing" is already
            # filtered out by skip_labels in get_specifications().
            if len(all_specs) > 1:
                data['specifications'] = all_specs[1:]
            else:
                data['specifications'] = []

            logger.info(f"Scraped {len(data['trim_names'])} trims, "
                       f"{len(data['specifications'])} specs")

            # Log sample data if available
            if data['trim_names']:
                logger.info(f"Trim names: {data['trim_names']}")
            if data['specifications']:
                logger.info(f"Sample specs: {[s['label'] for s in data['specifications'][:5]]}")

            # Save debug HTML only if no data found
            if not data['trim_names'] and not data['specifications']:
                self._save_debug_html(f"failed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html")
                logger.warning("No data found - debug HTML saved")

        except Exception as e:
            logger.error(f"Error scraping current body type data: {e}")
            logger.debug(traceback.format_exc())
            # Save debug HTML on error
            self._save_debug_html(f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html")

        return data
    
    # ------------------------------------------------------------------ #
    #  Fallback: scrape from overview page Styles section
    # ------------------------------------------------------------------ #

    def _get_style_links_from_overview(self) -> List[Dict[str, str]]:
        """Extract style names and URLs from the overview page's Styles section.

        Returns list of dicts: [{'name': 'LX Sedan 4D', 'url': 'https://...'}, ...]
        """
        styles = []
        try:
            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            seen_urls = set()

            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"]
                if "/styles/" not in href:
                    continue

                name = a_tag.get_text(strip=True)
                if not name or len(name) < 3:
                    continue

                # Build full URL if relative
                if href.startswith("/"):
                    full_url = f"https://www.kbb.com{href}"
                else:
                    full_url = href

                if full_url in seen_urls:
                    continue
                seen_urls.add(full_url)

                styles.append({"name": name, "url": full_url})

            logger.info(f"Found {len(styles)} style links on overview page")
            for s in styles:
                logger.debug(f"  Style: {s['name']} -> {s['url']}")

        except Exception as e:
            logger.error(f"Error extracting style links from overview: {e}")

        return styles

    def _scrape_single_style_specs(self, style_url: str) -> List[Dict[str, Any]]:
        """Navigate to a single style's page and scrape its specifications.

        Returns list of dicts: [{'label': 'Horsepower', 'values': ['220']}, ...]
        Each spec has exactly one value since this is a single-style page.
        """
        specs = []
        try:
            logger.info(f"Navigating to style page: {style_url}")
            self.driver.get(style_url)
            time.sleep(3)

            # Wait for body
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # Find a spec table — same approach as get_specifications()
            spec_table = None
            try:
                spec_table = self.driver.find_element(By.ID, "compare-trim-tables")
                logger.info("Found compare-trim-tables on style page")
            except NoSuchElementException:
                tables = self.driver.find_elements(By.TAG_NAME, "table")
                if tables:
                    spec_table = max(tables, key=lambda t: len(t.find_elements(By.TAG_NAME, "tr")))
                    logger.info("Using largest table on style page")

            if not spec_table:
                logger.warning(f"No spec table found on style page: {style_url}")
                return specs

            table_html = spec_table.get_attribute("innerHTML")
            soup = BeautifulSoup(table_html, "html.parser")
            rows = soup.find_all("tr")

            skip_labels = {'specifications', 'features', 'compare', 'save', 'see pricing', ''}
            skip_prefixes = ('save ', 'see ')

            for row in rows:
                try:
                    th_cells = row.find_all("th")
                    cells = row.find_all("td")

                    if th_cells and cells:
                        all_cells = th_cells + cells
                    elif cells:
                        all_cells = cells
                    elif th_cells:
                        all_cells = th_cells
                    else:
                        continue

                    cell_texts = [c.get_text(strip=True) for c in all_cells]
                    if len(cell_texts) < 2:
                        continue

                    spec_name = None
                    value_start_idx = 0
                    for idx, text in enumerate(cell_texts):
                        if text and len(text) > 1:
                            spec_name = text
                            value_start_idx = idx + 1
                            break

                    if not spec_name:
                        continue

                    name_lower = spec_name.lower()
                    if name_lower in skip_labels or name_lower.startswith(skip_prefixes):
                        continue

                    # Take only the first non-empty value
                    value = "N/A"
                    for text in cell_texts[value_start_idx:]:
                        if text:
                            value = text
                            break

                    specs.append({
                        'label': spec_name,
                        'values': [value]
                    })

                except Exception as e:
                    logger.debug(f"Error parsing style spec row: {e}")
                    continue

            logger.info(f"Extracted {len(specs)} specs from style page")

        except Exception as e:
            logger.error(f"Error scraping style page {style_url}: {e}")
            logger.debug(traceback.format_exc())

        return specs

    def _scrape_overview_styles(self, make: str, model: str, year: str) -> Dict[str, Any]:
        """Fallback: scrape specs from the overview page's Styles section.

        When /specs/ redirects to the overview page, find style links,
        scrape specs from the first style, and use them as shared data
        for all trims.

        Returns bodytypes dict: {'Default': {'trim_names': [...], 'specifications': [...]}}
        """
        style_links = self._get_style_links_from_overview()

        if not style_links:
            logger.warning(f"No style links found on overview for {year} {make} {model}")
            return {}

        # Collect all style/trim names
        style_names = [s['name'] for s in style_links]
        logger.info(f"Styles found: {style_names}")

        # Scrape specs from the first style page (used as mutual/shared data)
        specs = []
        for style in style_links:
            time.sleep(settings.RESEARCH_CONFIG['delay_between_requests'])
            specs = self._scrape_single_style_specs(style['url'])
            if specs:
                logger.info(f"Got specs from style: {style['name']}")
                break
            logger.warning(f"No specs from style: {style['name']}, trying next...")

        if not specs:
            logger.warning(f"Could not get specs from any style for {year} {make} {model}")
            return {}

        # Replicate the single-style specs across all trims (mutual static data)
        num_trims = len(style_names)
        expanded_specs = []
        for spec in specs:
            expanded_specs.append({
                'label': spec['label'],
                'values': spec['values'] * num_trims
            })

        logger.info(f"Built fallback data: {num_trims} trims, {len(expanded_specs)} specs (mutual)")

        return {
            'Default': {
                'trim_names': style_names,
                'specifications': expanded_specs
            }
        }

    def scrape_car_model(self, make: str, model: str, year: str) -> Dict[str, Any]:
        """Main method to scrape all data for a car model with multiple body types"""
        all_data = {
            'make': make,
            'model': model,
            'year': year,
            'scraped_at': datetime.now().isoformat(),
            'bodytypes': {}
        }

        # Navigate to the model page
        nav_result = self.navigate_to_car_model(make, model, year)

        if nav_result == "not_found":
            logger.warning(f"Car not found: {year} {make} {model}")
            return all_data

        if nav_result == "blocked":
            logger.error(f"Blocked by KBB for {year} {make} {model} - "
                         "consider increasing delay or using proxies")
            all_data['blocked'] = True
            return all_data

        if nav_result == "overview":
            logger.info(f"No specs comparison page -- using Styles fallback for {year} {make} {model}")
            all_data['bodytypes'] = self._scrape_overview_styles(make, model, year)
            self.save_results(all_data, make, model, year)
            return all_data

        # nav_result == "specs" -- normal path
        # Get all body types
        body_types = self.get_all_body_types()

        if len(body_types) == 1 and body_types[0] == "Default":
            # Single body type model - just scrape current data
            logger.info("Scraping single body type model")
            data = self.scrape_current_body_type_data()
            all_data['bodytypes']['Default'] = data

        else:
            # Multiple body types
            logger.info(f"Found {len(body_types)} body types: {body_types}")

            # FIRST: Scrape the currently displayed body type (first one) WITHOUT clicking
            first_body_type = body_types[0]
            logger.info(f"[1/{len(body_types)}] Scraping current body type: {first_body_type}")
            data = self.scrape_current_body_type_data()

            if data['trim_names'] or data['specifications']:
                all_data['bodytypes'][first_body_type] = data
                logger.info(f"[OK] Successfully scraped {first_body_type}")
            else:
                logger.warning(f"No data for body type: {first_body_type}")

            # THEN: Click on remaining body types and scrape each
            for i, body_type in enumerate(body_types[1:], 2):
                logger.info(f"[{i}/{len(body_types)}] Switching to body type: {body_type}")

                # Click to select this body type
                if self.select_body_type(body_type):
                    # Scrape data for this body type
                    data = self.scrape_current_body_type_data()

                    if data['trim_names'] or data['specifications']:
                        all_data['bodytypes'][body_type] = data
                        logger.info(f"[OK] Successfully scraped {body_type}")
                    else:
                        logger.warning(f"No data for body type: {body_type}")
                else:
                    logger.warning(f"Could not select body type: {body_type}")

        # Save the data
        self.save_results(all_data, make, model, year)

        return all_data
    
    def save_results(self, data: Dict[str, Any], make: str, model: str, year: str):
        """Save scraped data to CSV - appends to a single all_cars.csv file."""
        try:
            from kbb_scraper.exporters.csv_exporter import CsvExporter

            csv_path = Path(settings.CSV_DATA_DIR) / "all_cars.csv"
            exporter = CsvExporter(csv_path)
            exporter.export(data)

            logger.info(f"Data saved to: {csv_path} ({make} {model} {year})")

        except Exception as e:
            logger.error(f"Error saving results: {e}")
    
    def close(self):
        """Close the browser"""
        if self._driver_manager:
            self._driver_manager.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()