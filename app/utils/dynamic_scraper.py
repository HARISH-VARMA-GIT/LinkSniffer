import logging
import random
import time
from urllib.parse import urljoin

from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from helpers.user_agent_list import user_agents


class DynamicScraper:

    def __init__(self, headless=True, scroll_pause=2, max_retries=3, user_agent_rotation_frequency=5):
        self.scroll_pause = scroll_pause
        self.max_retries = max_retries
        self.user_agent_rotation_frequency = user_agent_rotation_frequency
        self.request_count = 0
        self.current_user_agent = None
        self.user_agents = user_agents
        self.setup_logging()
        self.setup_driver(headless)
        
    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
    def get_random_user_agent(self):
        user_agent = random.choice(self.user_agents)
        self.logger.info(f"Selected User-Agent: {user_agent}")
        return user_agent
    
    # a function to check for rotatinf the userr agent based on the multiples of rotation frequency
    def should_rotate_user_agent(self):
        return self.request_count % self.user_agent_rotation_frequency == 0
        
    def setup_driver(self, headless):
        self.current_user_agent = self.get_random_user_agent()
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument('--headless')

        options.add_argument('--disable-gpu')  #### Remove this if using gpu
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument(f'user-agent={self.current_user_agent}')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        self.driver = webdriver.Chrome(options=options)
        
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")  ## not required
        
    def rotate_user_agent_if_needed(self):
        if self.should_rotate_user_agent():
            self.logger.info("Rotating User-Agent...")
            self.driver.quit()
            self.setup_driver(headless=True)

    ## scroll to bottom and check for new content
    def scroll_to_bottom(self):
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(self.scroll_pause)
        new_height = self.driver.execute_script("return document.body.scrollHeight")
        return new_height != last_height

    # main logic for extracting the links
    def extract_all_links(self):
        links = set()
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((By.TAG_NAME, "a"))       ## Sometimes the js might not load content. So delay
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

    def scrape_website(self, url, max_scrolls=None,max_links = None):
        all_links = set()
        scroll_count = 0
        retry_count = 0
        
        try:
            self.rotate_user_agent_if_needed()
            self.driver.get(url)
            self.request_count += 1
            self.logger.info(f"Starting to scrape: {url}")
            
            while True:
                # extract links from the current view
                new_links = self.extract_all_links()
                all_links.update(new_links)
                
                self.logger.info(f"Found {len(new_links)} links")

                if max_links and len(all_links) >= max_links:
                    self.logger.info(f"Reached the maximum links limit ({max_links}). Stopping...")
                    break
                
                # check if we should continue scrolling
                if max_scrolls and scroll_count >= max_scrolls:
                    break
                
                # scroll and check for new content
                has_new_content = self.scroll_to_bottom()
                
                if not has_new_content:
                    retry_count += 1
                    if retry_count >= self.max_retries:
                        self.logger.info("No new content after multiple retries. Finishing...")
                        break
                else:
                    retry_count = 0
                
                scroll_count += 1
                
                # random delay with more variation
                time.sleep(random.uniform(1.5, 4.0))
                
        except Exception as e:
            self.logger.error(f"Error during scraping: {str(e)}")
        finally:
            self.driver.quit()
            
        return all_links

def main():
    # Example usage
    url = "https://www.asos.com/men/accessories/scarves/cat/?cid=6518"  
    
    scraper = DynamicScraper(
        headless=True,
        scroll_pause=2,
        max_retries=3,
        user_agent_rotation_frequency=5  # number of reqs
    )
    
    links = scraper.scrape_website(
        url=url,
        max_scrolls=10  # set to None for unlimited scrolling
    )
    
    print(links)

if __name__ == "__main__":
    main()