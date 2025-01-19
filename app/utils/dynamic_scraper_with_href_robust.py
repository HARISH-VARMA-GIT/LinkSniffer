from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
import time
import json
from urllib.parse import urljoin
import logging
import random

class DynamicScraper:
    # List of common User-Agent strings for different browsers and devices
    USER_AGENTS = [
        # Chrome on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        # Firefox on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
        # Edge on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        # Safari on macOS
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        # Chrome on macOS
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        # Mobile Chrome on Android
        "Mozilla/5.0 (Linux; Android 10; SM-G981B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        # Mobile Safari on iOS
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1"
    ]

    def __init__(self, headless=True, scroll_pause=2, max_retries=3, user_agent_rotation_frequency=5):
        """
        Initialize the scraper with configurable parameters
        
        Args:
            headless (bool): Run browser in headless mode
            scroll_pause (int): Pause between scrolls in seconds
            max_retries (int): Maximum number of retry attempts for failed operations
            user_agent_rotation_frequency (int): Number of requests before rotating User-Agent
        """
        self.scroll_pause = scroll_pause
        self.max_retries = max_retries
        self.user_agent_rotation_frequency = user_agent_rotation_frequency
        self.request_count = 0
        self.current_user_agent = None
        self.setup_logging()
        self.setup_driver(headless)
        
    def setup_logging(self):
        """Configure logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
    def get_random_user_agent(self):
        """Get a random User-Agent string from the list"""
        user_agent = random.choice(self.USER_AGENTS)
        self.logger.info(f"Selected User-Agent: {user_agent}")
        return user_agent
    
    def should_rotate_user_agent(self):
        """Check if it's time to rotate the User-Agent"""
        return self.request_count % self.user_agent_rotation_frequency == 0
        
    def setup_driver(self, headless):
        """Setup Chrome WebDriver with appropriate options and User-Agent"""
        self.current_user_agent = self.get_random_user_agent()
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument(f'user-agent={self.current_user_agent}')
        
        # Additional options to make the browser appear more realistic
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        self.driver = webdriver.Chrome(options=options)
        
        # Additional JavaScript to make the webdriver less detectable
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
    def rotate_user_agent_if_needed(self):
        """Rotate User-Agent if needed and recreate the driver"""
        if self.should_rotate_user_agent():
            self.logger.info("Rotating User-Agent...")
            self.driver.quit()
            self.setup_driver(headless=True)

    def scroll_to_bottom(self):
        """Scroll to the bottom and return True if new content was loaded"""
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(self.scroll_pause)
        new_height = self.driver.execute_script("return document.body.scrollHeight")
        return new_height != last_height

    def extract_all_links(self):
        """Extract all href links from the current page"""
        links = set()
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((By.TAG_NAME, "a"))
            )
            elements = self.driver.find_elements(By.TAG_NAME, "a")
            for element in elements:
                try:
                    href = element.get_attribute("href")
                    if href:
                        absolute_url = urljoin(self.driver.current_url, href)
                        links.add(absolute_url)
                except StaleElementReferenceException:
                    continue
        except TimeoutException:
            self.logger.warning("Timeout while waiting for anchor tags.")
        return links

    def scrape_website(self, url, max_scrolls=None):
        """
        Scrape all href links from a website with infinite scrolling
        
        Args:
            url (str): Website URL to scrape
            max_scrolls (int, optional): Maximum number of scrolls to perform
        
        Returns:
            set: Set of unique href links
        """
        all_links = set()
        scroll_count = 0
        retry_count = 0
        
        try:
            self.rotate_user_agent_if_needed()
            self.driver.get(url)
            self.request_count += 1
            self.logger.info(f"Starting to scrape: {url}")
            
            while True:
                # Extract links from the current view
                new_links = self.extract_all_links()
                all_links.update(new_links)
                
                self.logger.info(f"Found {len(new_links)} new links. Total: {len(all_links)}")
                
                # Check if we should continue scrolling
                if max_scrolls and scroll_count >= max_scrolls:
                    break
                
                # Scroll and check for new content
                has_new_content = self.scroll_to_bottom()
                
                if not has_new_content:
                    retry_count += 1
                    if retry_count >= self.max_retries:
                        self.logger.info("No new content after multiple retries. Finishing...")
                        break
                else:
                    retry_count = 0
                
                scroll_count += 1
                
                # Add random delay with more variation
                time.sleep(random.uniform(1.5, 4.0))
                
        except Exception as e:
            self.logger.error(f"Error during scraping: {str(e)}")
        finally:
            self.driver.quit()
            
        return all_links

    def save_links(self, links, filename):
        """Save extracted links to a JSON file"""
        with open(filename, "w") as f:
            json.dump(list(links), f, indent=2)
        self.logger.info(f"Saved {len(links)} links to {filename}")

def main():
    # Example usage
    url = "https://www.asos.com/men/accessories/scarves/cat/?cid=6518"  # Replace with the target website
    
    scraper = DynamicScraper(
        headless=True,
        scroll_pause=2,
        max_retries=3,
        user_agent_rotation_frequency=5  # Rotate User-Agent every 5 requests
    )
    
    links = scraper.scrape_website(
        url=url,
        max_scrolls=10  # Set to None for unlimited scrolling
    )
    
    scraper.save_links(links, "all_links.json")

if __name__ == "__main__":
    main()