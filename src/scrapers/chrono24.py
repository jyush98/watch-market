"""Chrono24 scraper implementation"""
from typing import Dict, List, Optional
import re
from loguru import logger
from datetime import datetime
from .base_scraper import BaseScraper

class Chrono24Scraper(BaseScraper):
   """Scraper for Chrono24.com"""
   
   BASE_URL = "https://www.chrono24.com"
   
   def __init__(self):
       super().__init__(delay_range=(3, 6))  # Longer delays for Chrono24
       self.source_name = "chrono24"
       self.setup_chrono24_session()
   
   def setup_chrono24_session(self):
       """Configure session specifically for Chrono24"""
       # More realistic browser headers
       self.session.headers.update({
           'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
           'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
           'Accept-Language': 'en-US,en;q=0.9',
           'Accept-Encoding': 'gzip, deflate, br',
           'Referer': 'https://www.chrono24.com/',
           'Sec-Ch-Ua': '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
           'Sec-Ch-Ua-Mobile': '?0',
           'Sec-Ch-Ua-Platform': '"macOS"',
           'Sec-Fetch-Dest': 'document',
           'Sec-Fetch-Mode': 'navigate',
           'Sec-Fetch-Site': 'same-origin',
           'Cache-Control': 'max-age=0'
       })
   
   def scrape_search_results(self, search_url: str = None, max_pages: int = 1) -> List[Dict]:
       """Scrape Rolex listings from search results"""
       listings = []
       
       # Use a simpler search URL format - searching for Rolex watches
       if not search_url:
           search_url = "https://www.chrono24.com/rolex/index.htm"
       
       # First, visit homepage to establish session/cookies
       logger.info("Establishing session with Chrono24...")
       homepage = self.get_page("https://www.chrono24.com")
       if not homepage:
           logger.error("Failed to establish session with Chrono24")
           return listings
       
       logger.info(f"Scraping Chrono24 search: {search_url}")
       
       for page in range(1, max_pages + 1):
           # Add pagination
           page_url = f"{search_url}&page={page}" if page > 1 else search_url
           soup = self.get_page(page_url)
           
           if not soup:
               continue
           
           # Find all watch listings on the page
           # Update selectors based on actual Chrono24 HTML structure
           listing_elements = soup.find_all('div', {'class': 'article-item-container'})
           
           # If that doesn't work, try alternative selectors
           if not listing_elements:
               listing_elements = soup.find_all('a', {'class': 'article-item'})
           
           logger.info(f"Found {len(listing_elements)} listings on page {page}")
           
           for element in listing_elements:
               listing_data = self.parse_search_listing(element)
               if listing_data:
                   listings.append(listing_data)
       
       logger.info(f"Scraped {len(listings)} total listings")
       return listings
   
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


# Quick test function
if __name__ == "__main__":
   scraper = Chrono24Scraper()
   results = scraper.scrape_search_results(max_pages=1)
   
   for listing in results[:5]:  # Print first 5
       print(f"\n{listing.get('title', 'Unknown')}")
       print(f"  Price: ${listing.get('price_usd', 0):,.0f}")
       print(f"  URL: {listing.get('url', 'N/A')}")