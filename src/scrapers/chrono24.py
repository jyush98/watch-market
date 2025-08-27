"""Chrono24 scraper - respectful approach following robots.txt guidelines"""
from typing import Dict, List, Optional
import re
import json
import time
import random
from loguru import logger
from datetime import datetime
from urllib.parse import urljoin
try:
    from .base_scraper import BaseScraper
except ImportError:
    # For standalone testing
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from base_scraper import BaseScraper

class Chrono24Scraper(BaseScraper):
   """Respectful Chrono24 scraper following their robots.txt guidelines"""
   
   BASE_URL = "https://www.chrono24.com"
   
   def __init__(self):
       # Increase delays to be more respectful (well above their 0.1s minimum)
       super().__init__(delay_range=(3, 8))  
       self.source_name = "chrono24"
       self.setup_chrono24_session()
   
   def setup_chrono24_session(self):
       """Configure session with enhanced headers to mimic legitimate browser"""
       # Enhanced headers to mimic legitimate browser behavior
       self.session.headers.update({
           'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
           'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
           'Accept-Language': 'en-US,en;q=0.9',
           'Accept-Encoding': 'gzip, deflate, br',
           'Connection': 'keep-alive',
           'Upgrade-Insecure-Requests': '1',
           'Sec-Fetch-Dest': 'document',
           'Sec-Fetch-Mode': 'navigate',
           'Sec-Fetch-Site': 'none',
           'Sec-Fetch-User': '?1',
           'Cache-Control': 'max-age=0',
           'DNT': '1'
       })
   
   def get_page(self, url: str, retries: int = 3):
       """Override with enhanced error handling and respectful delays"""
       for attempt in range(retries):
           try:
               # Respect robots.txt delay (0.1s minimum) + buffer for being respectful
               delay = random.uniform(0.5, 2.0)
               time.sleep(delay)
               
               logger.info(f"🔍 Attempt {attempt + 1}: Requesting {url}")
               response = self.session.get(url, timeout=30)
               
               logger.info(f"📊 Response status: {response.status_code}")
               
               if response.status_code == 200:
                   logger.success(f"✅ Successfully accessed {url}")
                   from bs4 import BeautifulSoup
                   return BeautifulSoup(response.content, 'html.parser')
                   
               elif response.status_code == 403:
                   logger.warning(f"🚫 403 Forbidden - Bot detection triggered")
                   if attempt < retries - 1:
                       # Exponential backoff for 403s
                       wait_time = (2 ** attempt) * 10
                       logger.info(f"⏱️ Waiting {wait_time}s before retry...")
                       time.sleep(wait_time)
                       continue
                   else:
                       logger.error(f"❌ All retries failed - Chrono24 blocking access")
                       return None
                       
               elif response.status_code == 429:
                   logger.warning(f"🐌 429 Rate Limited")
                   wait_time = (2 ** attempt) * 15
                   logger.info(f"⏱️ Rate limit - waiting {wait_time}s...")
                   time.sleep(wait_time)
                   continue
                   
               else:
                   logger.warning(f"⚠️ Unexpected status: {response.status_code}")
                   
           except Exception as e:
               logger.error(f"🌐 Request exception: {e}")
               if attempt < retries - 1:
                   time.sleep(10)
                   continue
                   
       logger.error(f"❌ Failed to access {url} after {retries} attempts")
       return None
   
   def test_basic_access(self) -> bool:
       """Test basic access to Chrono24 with respectful approach"""
       logger.info("🧪 Testing respectful access to Chrono24...")
       
       # Step 1: Check robots.txt first (being respectful)
       robots_url = f"{self.BASE_URL}/robots.txt"
       logger.info(f"📋 First checking robots.txt: {robots_url}")
       
       try:
           robots_response = self.session.get(robots_url, timeout=10)
           if robots_response.status_code == 200:
               logger.success("✅ robots.txt accessible - following guidelines")
               # Log relevant parts for debugging
               if 'Disallow: /search' in robots_response.text:
                   logger.warning("⚠️ /search path is disallowed in robots.txt")
           else:
               logger.warning(f"⚠️ robots.txt returned {robots_response.status_code}")
       except Exception as e:
           logger.debug(f"robots.txt check failed: {e}")
       
       # Step 2: Test homepage access
       logger.info("🏠 Testing homepage access...")
       homepage = self.get_page(self.BASE_URL)
       if homepage:
           title = homepage.title.get_text() if homepage.title else "No title"
           logger.success(f"✅ Homepage accessible - Title: {title[:50]}...")
           return True
       else:
           logger.error("❌ Homepage not accessible")
           return False
   
   def scrape_search_results(self, search_url: str = None, max_pages: int = 1) -> List[Dict]:
       """Main scraping method with respectful, incremental approach"""
       listings = []
       
       logger.info("🚀 Starting respectful Chrono24 scraping approach...")
       
       # Step 1: Test basic access first
       if not self.test_basic_access():
           logger.error("❌ Basic access test failed - aborting scraping")
           return listings
       
       # Step 2: Try to find a valid Rolex URL (respecting robots.txt)
       if not search_url:
           search_url = self.find_valid_rolex_url()
           if not search_url:
               logger.error("❌ Could not find valid Rolex URL - aborting")
               return listings
       
       # Step 3: Attempt to scrape the found URL
       logger.info(f"🎯 Attempting to scrape: {search_url}")
       soup = self.get_page(search_url)
       
       if not soup:
           logger.error("❌ Could not access search results page")
           return listings
       
       # Step 4: Parse the page for watch listings
       try:
           parsed_listings = self.parse_search_page(soup, search_url)
           listings.extend(parsed_listings)
           logger.success(f"✅ Successfully parsed {len(parsed_listings)} listings")
           
       except Exception as e:
           logger.error(f"❌ Error parsing search page: {e}")
       
       logger.info(f"🎉 Chrono24 scraping completed: {len(listings)} listings found")
       return listings
   
   def find_valid_rolex_url(self) -> Optional[str]:
       """Try to find a valid Rolex URL that respects robots.txt"""
       logger.info("🔍 Looking for valid Rolex URL...")
       
       # Try sitemap approach first (mentioned in their robots.txt)
       sitemap_url = f"{self.BASE_URL}/chrono24_sitemap_index.xml"
       logger.info(f"📋 Checking sitemap: {sitemap_url}")
       
       try:
           sitemap_response = self.session.get(sitemap_url, timeout=15)
           if sitemap_response.status_code == 200:
               logger.success("✅ Sitemap accessible")
               # Look for Rolex URLs in sitemap
               if 'rolex' in sitemap_response.text.lower():
                   logger.info("🎯 Found Rolex references in sitemap")
                   # Extract Rolex URLs from sitemap
                   rolex_matches = re.findall(r'<loc>(.*?rolex.*?)</loc>', sitemap_response.text, re.IGNORECASE)
                   if rolex_matches:
                       rolex_url = rolex_matches[0]
                       logger.success(f"🎯 Found Rolex URL from sitemap: {rolex_url}")
                       return rolex_url
           else:
               logger.warning(f"⚠️ Sitemap returned {sitemap_response.status_code}")
       except Exception as e:
           logger.debug(f"Sitemap approach failed: {e}")
       
       # Fallback: Test common URL patterns (but check if allowed)
       potential_urls = [
           f"{self.BASE_URL}/rolex/index.htm",
           f"{self.BASE_URL}/rolex-watches/index.htm", 
           f"{self.BASE_URL}/rolex/",
           f"{self.BASE_URL}/brand-rolex/index.htm"
       ]
       
       for url in potential_urls:
           logger.info(f"🧪 Testing potential URL: {url}")
           # Check if this path might be allowed
           if '/search' not in url:  # Avoid disallowed paths
               test_page = self.get_page(url)
               if test_page and 'rolex' in test_page.get_text().lower():
                   logger.success(f"🎯 Found working Rolex URL: {url}")
                   return url
               # Be respectful between tests
               time.sleep(3)
       
       logger.warning("⚠️ Could not find valid Rolex listings URL")
       return None
   
   def parse_search_page(self, soup, base_url: str) -> List[Dict]:
       """Parse Chrono24 search results page"""
       listings = []
       
       logger.info("🔍 Analyzing Chrono24 page structure...")
       
       # Try multiple selector strategies for Chrono24's structure
       selectors_to_try = [
           # Modern Chrono24 selectors
           '[data-testid*="listing"]',
           '[data-testid*="watch"]', 
           '[data-testid*="product"]',
           'article[data-testid]',
           # Classic selectors
           '.article-item-container',
           '.article-item',
           '.watch-item',
           '.product-item',
           '.listing-item',
           # Generic patterns
           '[class*="listing"]',
           '[class*="watch"]',
           '[class*="product"]',
           '[class*="article"]'
       ]
       
       products = []
       for selector in selectors_to_try:
           products = soup.select(selector)
           if products:
               logger.success(f"🎯 Found {len(products)} products with selector: {selector}")
               break
       
       # If no products found with CSS selectors, try JSON-LD
       if not products:
           logger.info("🔍 No products found with selectors, trying JSON-LD...")
           json_scripts = soup.find_all('script', type='application/ld+json')
           for script in json_scripts:
               try:
                   data = json.loads(script.string)
                   if self.is_product_data(data):
                       listing = self.parse_json_ld(data, base_url)
                       if listing:
                           listings.append(listing)
               except (json.JSONDecodeError, AttributeError) as e:
                   logger.debug(f"JSON-LD parsing error: {e}")
                   continue
       
       # Parse found product elements
       for i, product in enumerate(products[:30]):  # Limit for testing
           try:
               listing = self.parse_product_element(product, base_url)
               if listing:
                   listings.append(listing)
                   logger.debug(f"📦 Parsed product {i+1}: {listing.get('title', 'Unknown')[:50]}...")
           except Exception as e:
               logger.debug(f"Error parsing product {i+1}: {e}")
               continue
       
       return listings
   
   def parse_product_element(self, element, base_url: str) -> Optional[Dict]:
       """Parse individual product element from Chrono24"""
       try:
           listing = {
               'source': self.source_name,
               'scraped_at': datetime.now().isoformat()
           }
           
           # Extract product URL
           link = element.find('a', href=True)
           if not link and element.name == 'a':
               link = element
           
           if link:
               href = link.get('href')
               if href:
                   if not href.startswith('http'):
                       href = urljoin(base_url, href)
                   listing['url'] = href
                   listing['source_id'] = self.generate_source_id(href)
           
           # Extract title - try multiple selectors
           title_selectors = [
               'h3', 'h2', 'h1', 
               '.title', '[class*="title"]', 
               '.article-title', '[class*="article-title"]',
               '[data-testid*="title"]',
               '.text-bold', '[class*="text-bold"]'
           ]
           
           for selector in title_selectors:
               title_elem = element.select_one(selector)
               if title_elem:
                   listing['title'] = title_elem.get_text(strip=True)
                   break
           
           # Extract price - try multiple selectors
           price_selectors = [
               '.price', '[class*="price"]',
               '.text-price', '[class*="text-price"]',  
               '[data-testid*="price"]',
               '.amount', '[class*="amount"]'
           ]
           
           for selector in price_selectors:
               price_elem = element.select_one(selector)
               if price_elem:
                   price_text = price_elem.get_text(strip=True)
                   listing['price_usd'] = self.clean_price(price_text)
                   break
           
           # Extract details/description
           details_selectors = [
               '.text-muted', '[class*="text-muted"]',
               '.article-details', '[class*="article-details"]',
               '.description', '[class*="description"]'
           ]
           
           for selector in details_selectors:
               details_elem = element.select_one(selector)
               if details_elem:
                   details = details_elem.get_text(strip=True)
                   if details:
                       listing['details'] = details
                   break
           
           # Parse extracted information
           if 'title' in listing:
               self.parse_title(listing['title'], listing)
           
           if 'details' in listing:
               self.parse_details(listing['details'], listing)
           
           # Apply variation detection
           if listing.get('brand') and listing.get('model'):
               self.detect_watch_variations(listing)
           
           return listing if 'title' in listing and 'url' in listing else None
           
       except Exception as e:
           logger.debug(f"Error parsing product element: {e}")
           return None
   
   def is_product_data(self, data) -> bool:
       """Check if JSON-LD data represents a product"""
       if isinstance(data, dict):
           return data.get('@type') == 'Product'
       elif isinstance(data, list):
           return any(item.get('@type') == 'Product' for item in data if isinstance(item, dict))
       return False
   
   def parse_json_ld(self, data: Dict, base_url: str) -> Optional[Dict]:
       """Parse JSON-LD structured data"""
       try:
           # Handle both single product and list
           products = data if isinstance(data, list) else [data]
           
           for item in products:
               if item.get('@type') == 'Product':
                   listing = {
                       'source': self.source_name,
                       'scraped_at': datetime.now().isoformat(),
                       'title': item.get('name', 'Unknown'),
                       'url': item.get('url', base_url),
                       'source_id': self.generate_source_id(item.get('url', base_url))
                   }
                   
                   # Parse brand
                   brand = item.get('brand')
                   if isinstance(brand, dict):
                       listing['brand'] = brand.get('name', 'Unknown')
                   else:
                       listing['brand'] = str(brand) if brand else 'Unknown'
                   
                   # Parse offers for price
                   offers = item.get('offers', {})
                   if isinstance(offers, list) and offers:
                       offers = offers[0]
                   
                   price = offers.get('price', 0)
                   currency = offers.get('priceCurrency', 'USD')
                   
                   if price:
                       try:
                           listing['price_usd'] = self.convert_to_usd(float(price), currency)
                           listing['original_currency'] = currency
                           listing['original_price'] = float(price)
                       except (ValueError, TypeError):
                           listing['price_usd'] = 0
                   
                   # Extract additional info
                   if 'title' in listing:
                       self.parse_title(listing['title'], listing)
                   
                   return listing
                   
       except Exception as e:
           logger.debug(f"Error parsing JSON-LD: {e}")
       
       return None
   
   def convert_to_usd(self, price: float, currency: str) -> int:
       """Convert price to USD (simplified conversion)"""
       # Simplified conversion rates - could use real-time API
       rates = {
           'USD': 1.0,
           'EUR': 1.10,
           'GBP': 1.27,
           'CHF': 1.12,
           'CAD': 0.74,
           'AUD': 0.67
       }
       
       rate = rates.get(currency, 1.0)
       return int(price * rate)
   
   def detect_watch_variations(self, listing: Dict):
       """Apply our sophisticated variation detection to Chrono24 data"""
       title = listing.get('title', '').lower()
       url = listing.get('url', '').lower()
       reference = listing.get('reference_number', 'unknown')
       
       # Use the same variation patterns as our other scrapers
       search_text = f"{title} {url}".lower()
       
       variations = {
           'tiffany': {
               'keywords': ['tiffany', 'tiffany & co', 'tiffany dial'],
               'dial_type': 'Tiffany',
               'special_edition': 'Tiffany & Co',
               'suffix': 'tiffany'
           },
           'tropical': {
               'keywords': ['tropical', 'brown dial', 'aged dial'],
               'dial_type': 'Tropical',
               'special_edition': 'Tropical Dial',
               'suffix': 'tropical'
           },
           'gold': {
               'keywords': ['18k', 'yellow gold', 'rose gold', 'white gold', 'solid gold'],
               'dial_type': 'Gold',
               'special_edition': 'Yellow Gold',
               'suffix': 'gold'
           },
           'blue': {
               'keywords': ['blue dial', 'blue face', 'blue bezel'],
               'dial_type': 'Blue',
               'special_edition': 'Blue Dial',
               'suffix': 'blue'
           },
           'hulk': {
               'keywords': ['hulk', 'green dial', 'green bezel'],
               'dial_type': 'Green',
               'special_edition': 'Hulk (Green Dial)',
               'suffix': 'hulk'
           }
           # Add more as needed
       }
       
       # Initialize fields
       listing['dial_type'] = None
       listing['special_edition'] = None
       
       # Check for variations
       detected_suffix = 'standard'
       for var_key, var_info in variations.items():
           if any(keyword in search_text for keyword in var_info['keywords']):
               listing['dial_type'] = var_info['dial_type']
               listing['special_edition'] = var_info['special_edition']
               detected_suffix = var_info['suffix']
               logger.info(f"🎯 Detected {var_info['special_edition']} variation in Chrono24 listing")
               break
       
       listing['comparison_key'] = f"{reference}-{detected_suffix}"
   
   def parse_search_listing(self, element) -> Optional[Dict]:
       """Parse a single listing from search results"""
       try:
           # Extract basic info from search result
           data = {
               'source': self.source_name,
               'scraped_at': datetime.now().isoformat()
           }
           
           # Get URL
           link = element.find('a', href=True)
           if not link:
               # If the element itself is an 'a' tag
               if element.name == 'a' and element.get('href'):
                   link = element
           
           if link:
               href = link.get('href', '')
               data['url'] = self.BASE_URL + href if href.startswith('/') else href
               data['source_id'] = self.generate_source_id(data['url'])
           
           # Get title (contains brand and model)
           title_elem = element.find(['h3', 'div'], class_=re.compile('text-bold|article-title|title'))
           if title_elem:
               data['title'] = title_elem.get_text(strip=True)
               # Parse brand and model from title
               self.parse_title(data['title'], data)
           
           # Get price - try multiple possible selectors
           price_elem = element.find('div', class_=re.compile('price|text-price'))
           if not price_elem:
               price_elem = element.find('span', class_=re.compile('price'))
           
           if price_elem:
               price_text = price_elem.get_text(strip=True)
               data['price_usd'] = self.clean_price(price_text)
           
           # Get additional details if available
           details_elem = element.find('div', class_=re.compile('text-muted|article-details|description'))
           if details_elem:
               data['details'] = details_elem.get_text(strip=True)
               self.parse_details(data['details'], data)
           
           return data if 'url' in data and 'price_usd' in data else None
           
       except Exception as e:
           logger.error(f"Error parsing listing: {e}")
           return None
   
   def parse_title(self, title: str, data: Dict):
       """Extract brand, model, and reference from title"""
       # Rolex specific parsing
       if 'Rolex' in title:
           data['brand'] = 'Rolex'
           
           # Common Rolex models
           models = ['Submariner', 'GMT-Master', 'Daytona', 'Datejust', 'Explorer', 
                    'Sea-Dweller', 'Yacht-Master', 'Milgauss', 'Air-King', 'Day-Date',
                    'Oyster Perpetual', 'Sky-Dweller']
           
           for model in models:
               if model in title:
                   data['model'] = model
                   break
           
           # Try to extract reference number (e.g., 116610LN, 126610LV)
           ref_match = re.search(r'\b(\d{4,6}[A-Z]*)\b', title)
           if ref_match:
               data['reference_number'] = ref_match.group(1)
   
   def parse_details(self, details: str, data: Dict):
       """Extract year, condition, etc. from details text"""
       # Extract year
       year_match = re.search(r'\b(19\d{2}|20\d{2})\b', details)
       if year_match:
           data['year'] = int(year_match.group(1))
       
       # Check for box and papers
       details_lower = details.lower()
       data['has_box'] = 'box' in details_lower
       data['has_papers'] = 'paper' in details_lower or 'certificate' in details_lower
       
       # Condition keywords
       if 'new' in details_lower or 'unworn' in details_lower:
           data['condition'] = 'new'
       elif 'excellent' in details_lower or 'mint' in details_lower:
           data['condition'] = 'excellent'
       elif 'very good' in details_lower:
           data['condition'] = 'very good'
       elif 'good' in details_lower:
           data['condition'] = 'good'
       elif 'fair' in details_lower:
           data['condition'] = 'fair'
   
   def scrape_listing(self, url: str) -> Optional[Dict]:
       """Scrape detailed information from a single listing page"""
       logger.info(f"Scraping listing: {url}")
       soup = self.get_page(url)
       
       if not soup:
           return None
       
       # This would scrape the full listing page
       # Implementation depends on Chrono24's current structure
       # For MVP, we can just use search results data
       pass


# Test function with comprehensive testing
if __name__ == "__main__":
    logger.info("🧪 Testing respectful Chrono24 scraper...")
    
    scraper = Chrono24Scraper()
    
    # Test 1: Basic access
    logger.info("\n" + "="*60)
    logger.info("🧪 TEST 1: Basic Access Test")
    logger.info("="*60)
    
    access_ok = scraper.test_basic_access()
    
    if access_ok:
        # Test 2: Search for listings
        logger.info("\n" + "="*60)
        logger.info("🧪 TEST 2: Respectful Scraping Test")  
        logger.info("="*60)
        
        results = scraper.scrape_search_results(max_pages=1)
        
        print(f"\n🎉 === CHRONO24 SCRAPING RESULTS ===")
        print(f"📊 Total listings found: {len(results)}")
        
        if results:
            print(f"\n📦 Sample listings:")
            for i, listing in enumerate(results[:5], 1):
                print(f"\n{i}. {listing.get('title', 'Unknown')}")
                print(f"   🏷️  Brand: {listing.get('brand', 'N/A')}")
                print(f"   ⌚ Model: {listing.get('model', 'N/A')}")
                print(f"   🔢 Reference: {listing.get('reference_number', 'N/A')}")
                print(f"   💰 Price: ${listing.get('price_usd', 0):,.0f}")
                print(f"   🔗 URL: {listing.get('url', 'N/A')[:80]}...")
                if listing.get('special_edition'):
                    print(f"   ✨ Special: {listing.get('special_edition')}")
        else:
            print("\n⚠️ No listings found - this could mean:")
            print("   • Chrono24 is blocking access (403/429 errors)")
            print("   • Page structure has changed")
            print("   • Search URL not found or invalid")
            print("   • robots.txt restrictions preventing access")
            
    else:
        print("\n❌ === ACCESS BLOCKED ===")
        print("Chrono24 appears to be blocking our respectful requests.")
        print("This suggests they have sophisticated bot detection.")
        print("\nOptions:")
        print("• Try again later (temporary blocking)")
        print("• Implement more advanced techniques (Selenium, proxies)")
        print("• Focus on alternative sources (Watchfinder, European dealers)")
        
    logger.info("\n🏁 Chrono24 testing completed.")