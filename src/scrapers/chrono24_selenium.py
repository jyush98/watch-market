"""Chrono24 scraper using Selenium to bypass bot detection"""
from typing import Dict, List, Optional
import re
import time
from loguru import logger
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import hashlib

class Chrono24SeleniumScraper:
    """Selenium-based scraper for Chrono24.com"""
    
    BASE_URL = "https://www.chrono24.com"
    
    def __init__(self, headless=True):
        self.source_name = "chrono24"
        self.headless = headless
        self.driver = None
        self.setup_driver()
        
    def setup_driver(self):
        """Set up Chrome driver with stealth options"""
        options = Options()
        
        if self.headless:
            options.add_argument("--headless")
        
        # Anti-detection options
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")
        
        # Additional stealth options
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-plugins-discovery")
        options.add_argument("--disable-web-security")
        options.add_argument("--allow-running-insecure-content")
        
        try:
            # Use webdriver manager to auto-download ChromeDriver
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            
            # Execute script to remove webdriver property
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            logger.info("Chrome driver initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Chrome driver: {e}")
            raise
    
    def close(self):
        """Close the browser"""
        if self.driver:
            self.driver.quit()
            logger.info("Browser closed")
    
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def _wait_for_page_load(self) -> bool:
        """Wait for Cloudflare challenge to complete and page to fully load"""
        logger.info("Waiting for page to load (handling Cloudflare if present)...")
        
        max_wait = 30  # seconds
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            current_title = self.driver.title.lower()
            current_url = self.driver.current_url
            
            # Check if we're still on a challenge page
            if 'just a moment' in current_title or 'checking your browser' in current_title:
                logger.info(f"Challenge page detected: '{self.driver.title}'. Waiting...")
                time.sleep(2)
                continue
            
            # Check if page has loaded properly
            if 'rolex' in current_title or 'chrono24' in current_title:
                logger.info(f"Page loaded successfully: '{self.driver.title}'")
                time.sleep(2)  # Give it a bit more time to fully render
                return True
                
            time.sleep(1)
        
        logger.warning(f"Page load timeout after {max_wait}s. Title: '{self.driver.title}'")
        return False
    
    def scrape_search_results(self, search_url: str = None, max_pages: int = 1, max_results: int = 100) -> List[Dict]:
        """Scrape Rolex listings from search results"""
        listings = []
        
        # Default search for Rolex watches
        if not search_url:
            search_url = "https://www.chrono24.com/rolex/index.htm"
        
        logger.info(f"Scraping Chrono24 search: {search_url}")
        
        try:
            # Navigate to the search page
            self.driver.get(search_url)
            
            # Wait for Cloudflare challenge to complete
            if not self._wait_for_page_load():
                logger.error("Failed to pass Cloudflare challenge")
                return listings
            
            # Handle any cookie banners or popups
            self._handle_popups()
            
            results_count = 0
            for page in range(1, max_pages + 1):
                if results_count >= max_results:
                    break
                    
                if page > 1:
                    # Navigate to next page
                    if not self._go_to_next_page():
                        logger.info("No more pages available")
                        break
                
                logger.info(f"Scraping page {page}")
                page_listings = self._scrape_current_page()
                
                for listing in page_listings:
                    if results_count >= max_results:
                        break
                    listings.append(listing)
                    results_count += 1
                
                logger.info(f"Found {len(page_listings)} listings on page {page}, total: {results_count}")
                
                # Random delay between pages
                time.sleep(2 + len(str(page)))  # Longer delay for later pages
        
        except Exception as e:
            logger.error(f"Error during scraping: {e}")
        
        logger.info(f"Scraped {len(listings)} total listings")
        return listings
    
    def _handle_popups(self):
        """Handle cookie banners and other popups"""
        try:
            # Wait a bit for popups to appear
            time.sleep(2)
            
            # Try to find and close cookie banner
            cookie_selectors = [
                '[data-testid="cookie-banner-accept"]',
                '.cookie-accept',
                '#cookie-accept',
                'button[class*="cookie"]',
                'button[class*="accept"]'
            ]
            
            for selector in cookie_selectors:
                try:
                    button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if button.is_displayed():
                        button.click()
                        logger.info("Clicked cookie accept button")
                        time.sleep(1)
                        break
                except NoSuchElementException:
                    continue
                    
        except Exception as e:
            logger.debug(f"Could not handle popups: {e}")
    
    def _scrape_current_page(self) -> List[Dict]:
        """Scrape all listings from the current page"""
        listings = []
        
        # Debug: Print current URL and page title
        logger.info(f"Current URL: {self.driver.current_url}")
        logger.info(f"Page title: {self.driver.title}")
        
        # Take screenshot for debugging (optional)
        try:
            self.driver.save_screenshot("/tmp/chrono24_debug.png")
            logger.info("Screenshot saved to /tmp/chrono24_debug.png")
        except:
            pass
        
        # Wait for listings to load with more selectors
        potential_selectors = [
            '[data-testid="search-result-item"]',
            '.article-item-container', 
            '.js-article-item',
            '[class*="article-item"]',
            '[class*="search-result"]',
            '.search-results .listing',
            'div[data-article-id]',
            '.wt-search-result'
        ]
        
        # Try to find any element that might be a listing
        found_elements = False
        for selector in potential_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    logger.info(f"Found {len(elements)} elements with selector: {selector}")
                    found_elements = True
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")
        
        if not found_elements:
            # Debug: Print page source snippet
            page_source = self.driver.page_source
            logger.warning(f"No known selectors found. Page source length: {len(page_source)}")
            logger.debug(f"Page source preview: {page_source[:500]}...")
            return listings
        
        # Wait for listings to load
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ', '.join(potential_selectors)))
            )
        except TimeoutException:
            logger.warning("Timeout waiting for listings to load")
            return listings
        
        # Try multiple selectors for listing elements
        listing_selectors = [
            '[data-testid="search-result-item"]',
            '.article-item-container',
            '.js-article-item',
            '[class*="article-item"]'
        ]
        
        listing_elements = []
        for selector in listing_selectors:
            listing_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
            if listing_elements:
                logger.info(f"Found {len(listing_elements)} listings using selector: {selector}")
                break
        
        if not listing_elements:
            logger.warning("No listing elements found on page")
            return listings
        
        for i, element in enumerate(listing_elements):
            try:
                listing_data = self._parse_listing_element(element)
                if listing_data:
                    listings.append(listing_data)
                    logger.debug(f"Parsed listing {i+1}: {listing_data.get('title', 'Unknown')[:50]}")
            except Exception as e:
                logger.error(f"Error parsing listing element {i}: {e}")
                continue
        
        return listings
    
    def _parse_listing_element(self, element) -> Optional[Dict]:
        """Parse a single listing element"""
        data = {
            'source': self.source_name,
            'scraped_at': datetime.now().isoformat()
        }
        
        try:
            # Get URL
            link_element = element.find_element(By.TAG_NAME, 'a')
            if link_element:
                href = link_element.get_attribute('href')
                data['url'] = href
                data['source_id'] = self.generate_source_id(href)
            
            # Get title/name
            title_selectors = [
                '[data-testid="search-result-title"]',
                '.article-item-title',
                '.js-article-title',
                'h3',
                '[class*="title"]'
            ]
            
            for selector in title_selectors:
                try:
                    title_element = element.find_element(By.CSS_SELECTOR, selector)
                    if title_element:
                        data['title'] = title_element.text.strip()
                        self._parse_title(data['title'], data)
                        break
                except NoSuchElementException:
                    continue
            
            # Get price
            price_selectors = [
                '[data-testid="search-result-price"]',
                '.article-item-price',
                '.js-article-price', 
                '[class*="price"]'
            ]
            
            for selector in price_selectors:
                try:
                    price_element = element.find_element(By.CSS_SELECTOR, selector)
                    if price_element:
                        price_text = price_element.text.strip()
                        data['price_usd'] = self._clean_price(price_text)
                        break
                except NoSuchElementException:
                    continue
            
            # Get additional details
            try:
                details_element = element.find_element(By.CSS_SELECTOR, '[class*="description"], [class*="details"], .article-item-info')
                if details_element:
                    data['details'] = details_element.text.strip()
                    self._parse_details(data['details'], data)
            except NoSuchElementException:
                pass
            
            # Apply watch variation detection (like in bobs_watches.py)
            self.detect_watch_variations(data)
            
            return data if 'url' in data and 'price_usd' in data else None
            
        except Exception as e:
            logger.error(f"Error parsing listing element: {e}")
            return None
    
    def _parse_title(self, title: str, data: Dict):
        """Extract brand, model, and reference from title"""
        if 'Rolex' in title:
            data['brand'] = 'Rolex'
            
            # Common Rolex models
            models = ['Submariner', 'GMT-Master', 'Daytona', 'Datejust', 'Explorer', 
                     'Sea-Dweller', 'Yacht-Master', 'Milgauss', 'Air-King', 'Day-Date',
                     'Oyster Perpetual', 'Sky-Dweller', 'Cosmograph', 'GMT Master']
            
            for model in models:
                if model in title:
                    data['model'] = model
                    break
            
            # Try to extract reference number
            ref_match = re.search(r'\b(\d{4,6}[A-Z]*)\b', title)
            if ref_match:
                data['reference_number'] = ref_match.group(1)
        
        # Handle other brands as needed
        other_brands = ['Omega', 'Tudor', 'Breitling', 'TAG Heuer', 'Cartier', 'Patek Philippe', 'Audemars Piguet']
        for brand in other_brands:
            if brand in title:
                data['brand'] = brand
                break
    
    def _parse_details(self, details: str, data: Dict):
        """Extract additional details from description text"""
        details_lower = details.lower()
        
        # Extract year
        year_match = re.search(r'\b(19\d{2}|20\d{2})\b', details)
        if year_match:
            data['year'] = int(year_match.group(1))
        
        # Condition
        if any(word in details_lower for word in ['new', 'unworn']):
            data['condition'] = 'new'
        elif 'excellent' in details_lower or 'mint' in details_lower:
            data['condition'] = 'excellent'
        elif 'very good' in details_lower:
            data['condition'] = 'very good'
        elif 'good' in details_lower:
            data['condition'] = 'good'
        
        # Box and papers
        data['has_box'] = 'box' in details_lower
        data['has_papers'] = any(word in details_lower for word in ['papers', 'certificate', 'warranty'])
    
    def detect_watch_variations(self, listing: Dict) -> None:
        """Detect watch variations for accurate price comparison (adapted from bobs_watches.py)"""
        title = listing.get('title', '').lower()
        url = listing.get('url', '').lower()
        reference = listing.get('reference_number', 'unknown')
        
        # Combine title and URL for detection
        search_text = f"{title} {url}".lower()
        
        # Define variation patterns (same as bobs_watches.py)
        variations = {
            'tiffany': {
                'keywords': ['tiffany', 'tiffany & co', 'tiffany dial'],
                'dial_type': 'Tiffany',
                'special_edition': 'Tiffany & Co',
                'suffix': 'tiffany'
            },
            'tropical': {
                'keywords': ['tropical', 'brown dial', 'chocolate dial'],
                'dial_type': 'Tropical',
                'special_edition': 'Tropical Dial',
                'suffix': 'tropical'
            },
            'spider': {
                'keywords': ['spider dial', 'patina'],
                'dial_type': 'Spider',
                'special_edition': 'Spider Dial',
                'suffix': 'spider'
            },
            'gold': {
                'keywords': ['yellow gold', 'gold', 'yg'],
                'dial_type': None,
                'special_edition': 'Gold',
                'suffix': 'gold'
            },
            'blue_dial': {
                'keywords': ['blue dial', 'blue-dial', 'blue submariner'],
                'dial_type': 'Blue',
                'special_edition': 'Blue Dial',
                'suffix': 'blue'
            },
            'white_dial': {
                'keywords': ['white dial', 'white-dial', 'white-submariner'],
                'dial_type': 'White',
                'special_edition': 'White Dial',
                'suffix': 'white'
            },
            # Add more variations as needed
        }
        
        # Check for variations
        detected_variation = None
        for var_key, var_info in variations.items():
            if any(keyword in search_text for keyword in var_info['keywords']):
                detected_variation = var_info
                break
        
        if detected_variation:
            if detected_variation['dial_type']:
                listing['dial_type'] = detected_variation['dial_type']
            listing['special_edition'] = detected_variation['special_edition']
            listing['comparison_key'] = f"{reference}-{detected_variation['suffix']}"
        else:
            listing['comparison_key'] = f"{reference}-standard"
    
    def _go_to_next_page(self) -> bool:
        """Navigate to the next page"""
        try:
            # Look for next page button
            next_selectors = [
                '[data-testid="pagination-next"]',
                '.pagination-next',
                '.js-next-page',
                'a[aria-label="Next"]',
                'a[title*="Next"]'
            ]
            
            for selector in next_selectors:
                try:
                    next_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if next_button.is_enabled():
                        next_button.click()
                        time.sleep(3)  # Wait for page to load
                        return True
                except NoSuchElementException:
                    continue
                    
            return False
        except Exception as e:
            logger.error(f"Error navigating to next page: {e}")
            return False
    
    def _clean_price(self, price_text: str) -> Optional[float]:
        """Extract numeric price from text"""
        if not price_text:
            return None
            
        # Remove currency symbols and formatting
        cleaned = re.sub(r'[^\d.,]', '', price_text)
        # Handle different decimal separators
        cleaned = cleaned.replace(',', '')
        
        try:
            return float(cleaned)
        except (ValueError, AttributeError):
            logger.debug(f"Could not parse price: {price_text}")
            return None
    
    def generate_source_id(self, url: str) -> str:
        """Generate unique ID for a listing"""
        return hashlib.md5(url.encode()).hexdigest()[:16]

# Test function
if __name__ == "__main__":
    with Chrono24SeleniumScraper(headless=True) as scraper:  # Set to False to see the browser
        results = scraper.scrape_search_results(max_pages=1, max_results=10)
        
        print(f"\n=== Found {len(results)} listings ===")
        for i, listing in enumerate(results, 1):
            print(f"\n{i}. {listing.get('title', 'Unknown')}")
            print(f"   Brand: {listing.get('brand', 'N/A')}")
            print(f"   Model: {listing.get('model', 'N/A')}")
            print(f"   Reference: {listing.get('reference_number', 'N/A')}")
            print(f"   Price: ${listing.get('price_usd', 0):,.0f}")
            print(f"   Comparison Key: {listing.get('comparison_key', 'N/A')}")
            print(f"   URL: {listing.get('url', 'N/A')}")