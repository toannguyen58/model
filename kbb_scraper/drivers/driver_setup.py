"""
WebDriver setup with research-friendly configuration
"""
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import logging

from ..config.settings import SELENIUM_CONFIG

logger = logging.getLogger(__name__)


class DriverManager:
    """Manages WebDriver instances for KBB scraping"""

    def __init__(self, headless=None):
        self.headless = headless if headless is not None else SELENIUM_CONFIG['headless']
        self.driver = None

    def setup_driver(self):
        """Setup Chrome WebDriver with research-optimized settings"""
        try:
            chrome_options = Options()

            # Add configured options
            for option in SELENIUM_CONFIG['chrome_options']:
                if self.headless and 'headless' in option:
                    chrome_options.add_argument(option)
                elif not self.headless and 'headless' in option:
                    continue  # Skip headless option if not headless
                else:
                    chrome_options.add_argument(option)

            # Anti-detection measures
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)

            # For research: disable images to speed up
            prefs = {
                "profile.managed_default_content_settings.images": 2,
                "profile.default_content_setting_values.notifications": 2
            }
            chrome_options.add_experimental_option("prefs", prefs)

            # Setup service
            service = Service(ChromeDriverManager().install())

            # Create driver
            self.driver = webdriver.Chrome(service=service, options=chrome_options)

            # Set timeouts
            self.driver.implicitly_wait(SELENIUM_CONFIG['implicit_wait'])
            self.driver.set_page_load_timeout(SELENIUM_CONFIG['page_load_timeout'])

            # Execute anti-detection script
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            logger.info("WebDriver setup complete")
            return self.driver

        except Exception as e:
            logger.error(f"Failed to setup WebDriver: {e}")
            raise

    def get_wait(self, timeout=None):
        """Get WebDriverWait instance"""
        if timeout is None:
            timeout = SELENIUM_CONFIG['explicit_wait']
        return WebDriverWait(self.driver, timeout)

    def close(self):
        """Close the driver"""
        if self.driver:
            self.driver.quit()
            logger.info("WebDriver closed")

    def __enter__(self):
        """Context manager entry"""
        self.setup_driver()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


def setup_research_driver():
    """Convenience function for research scraping"""
    return DriverManager().setup_driver()