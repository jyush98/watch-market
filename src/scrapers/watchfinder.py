"""Watchfinder & Co scraper - premium UK luxury watch dealer"""
from typing import Dict, List, Optional
import re
import json
import requests
from bs4 import BeautifulSoup
from loguru import logger
from datetime import datetime
try:
    from .base_scraper import BaseScraper
except ImportError:
    # For standalone testing
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from base_scraper import BaseScraper

class WatchfinderScraper(BaseScraper):
    """Scraper for Watchfinder & Co - UK luxury watch marketplace"""
    
    BASE_URL = "https://www.watchfinder.co.uk"
    
    def __init__(self):
        super().__init__(delay_range=(2, 4))  # Be respectful - UK site
        self.source_name = "watchfinder"
        
        # GBP to USD conversion (approximate - could be enhanced with real-time rates)
        self.gbp_to_usd_rate = 1.27  # As of 2024
    
    def scrape_search_results(self, search_url: str = None, max_pages: int = 1) -> List[Dict]:
        """Scrape Watchfinder watch listings"""
        listings = []
        
        # Watchfinder has category-specific URLs
        if not search_url:
            search_urls = [
                f"{self.BASE_URL}/Rolex/Submariner/watches",
                f"{self.BASE_URL}/Rolex/GMT-Master/watches", 
                f"{self.BASE_URL}/Rolex/Daytona/watches",
                f"{self.BASE_URL}/Rolex/Datejust/watches",
                f"{self.BASE_URL}/Rolex/Explorer/watches",
                f"{self.BASE_URL}/Rolex/Sea-Dweller/watches"
            ]
        else:
            search_urls = [search_url]
        
        for url in search_urls[:max_pages]:
            logger.info(f"Scraping Watchfinder: {url}")
            
            try:
                soup = self.get_page(url)
                if not soup:
                    logger.warning(f"Failed to get content from {url}")
                    continue
                
                logger.info(f"Page title: {soup.title.get_text() if soup.title else 'No title'}")
                
                # Look for the JavaScript _stockSearchArray 
                page_listings = self.extract_stock_array(soup, url)
                listings.extend(page_listings)
                
            except Exception as e:
                logger.error(f"Error scraping {url}: {e}")
                continue
        
        logger.info(f"Scraped {len(listings)} listings from Watchfinder")
        return listings
    
    def extract_stock_array(self, soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """Extract watch data from JavaScript _stockSearchArray"""
        listings = []
        
        try:
            # Find script tags containing the stock array or any watch data
            scripts = soup.find_all('script')
            stock_data = None
            
            # Look for various patterns of data
            patterns = [
                r'_stockSearchArray\s*=\s*(\[.*?\]);',
                r'stockSearchArray\s*=\s*(\[.*?\]);',
                r'watchData\s*=\s*(\[.*?\]);',
                r'products\s*:\s*(\[.*?\])',
                r'"watches"\s*:\s*(\[.*?\])'
            ]
            
            for script in scripts:
                if script.string:
                    script_text = script.string
                    
                    # Debug: log if we find any promising patterns
                    if any(keyword in script_text.lower() for keyword in ['watch', 'stock', 'product', 'submariner']):
                        logger.debug(f"Found potentially relevant script with {len(script_text)} characters")
                    
                    for pattern in patterns:
                        match = re.search(pattern, script_text, re.DOTALL)
                        if match:
                            try:
                                stock_data = json.loads(match.group(1))
                                logger.info(f"Successfully parsed data with pattern: {pattern}")
                                break
                            except json.JSONDecodeError as e:
                                logger.debug(f"JSON decode error with pattern {pattern}: {e}")
                                continue
                    
                    if stock_data:
                        break
            
            if not stock_data:
                logger.warning("No stock array found in any pattern, trying fallback method")
                return self.fallback_scraping(soup, base_url)
            
            logger.info(f"Found {len(stock_data)} watches in stock array")
            
            # Process each watch in the stock array
            for watch_data in stock_data:
                listing = self.parse_stock_item(watch_data, base_url)
                if listing:
                    listings.append(listing)
                    
        except Exception as e:
            logger.error(f"Error extracting stock array: {e}")
            return self.fallback_scraping(soup, base_url)
        
        return listings
    
    def parse_stock_item(self, watch_data: Dict, base_url: str) -> Optional[Dict]:
        """Parse individual watch from stock array"""
        try:
            listing = {
                'source': self.source_name,
                'scraped_at': datetime.now().isoformat()
            }
            
            # Basic information
            listing['source_id'] = str(watch_data.get('id', ''))
            listing['brand'] = watch_data.get('brand', 'Unknown')
            listing['model'] = watch_data.get('series', 'Unknown')
            listing['reference_number'] = watch_data.get('model', 'Unknown')
            listing['year'] = watch_data.get('yearOfBirth')
            
            # Build URL
            if listing['source_id']:
                listing['url'] = f"{base_url}/watch/{listing['source_id']}"
            else:
                listing['url'] = base_url
            
            # Pricing - convert GBP to USD
            gbp_price = watch_data.get('price')
            if gbp_price:
                # Remove currency symbols and parse
                gbp_price_clean = re.sub(r'[£,]', '', str(gbp_price))
                try:
                    gbp_value = float(gbp_price_clean)
                    listing['price_usd'] = int(gbp_value * self.gbp_to_usd_rate)
                    listing['original_currency'] = 'GBP'
                    listing['original_price'] = gbp_value
                except (ValueError, TypeError):
                    logger.debug(f"Could not parse price: {gbp_price}")
                    listing['price_usd'] = 0
            else:
                listing['price_usd'] = 0
            
            # Accessories
            listing['has_box'] = bool(watch_data.get('box'))
            listing['has_papers'] = bool(watch_data.get('papers'))
            
            # Condition (Watchfinder grades their watches)
            condition_map = {
                'A+': 'excellent',
                'A': 'very good', 
                'A-': 'good',
                'B+': 'good',
                'B': 'fair',
                'B-': 'fair'
            }
            condition_code = watch_data.get('condition', 'unknown')
            listing['condition'] = condition_map.get(condition_code, 'unknown')
            
            # Generate title for parsing
            listing['title'] = f"{listing['brand']} {listing['model']} {listing['reference_number']}"
            
            # Extract watch variations and comparison key
            self.detect_watch_variations(listing)
            
            return listing
            
        except Exception as e:
            logger.error(f"Error parsing stock item: {e}")
            return None
    
    def fallback_scraping(self, soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """Fallback method if JavaScript parsing fails"""
        listings = []
        
        logger.info("Attempting fallback scraping methods...")
        
        # Method 1: Look for common product selectors
        product_selectors = [
            '.product-item',
            '.watch-item', 
            '[data-product]',
            '.product-card',
            '.listing',
            '.item',
            'article'
        ]
        
        products = []
        for selector in product_selectors:
            products = soup.find_all(selector)
            if products:
                logger.info(f"Fallback: Found {len(products)} products using {selector}")
                break
        
        # Method 2: Look for any links that might be watch pages
        if not products:
            all_links = soup.find_all('a', href=True)
            watch_links = []
            
            # Look for different URL patterns
            patterns = ['/watch/', '/watches/', '/ref-', '/model-', '/rolex-']
            
            for link in all_links:
                href = link.get('href', '')
                if any(pattern in href.lower() for pattern in patterns):
                    watch_links.append(link)
            
            logger.info(f"Fallback: Found {len(watch_links)} potential watch links")
            
            # Create minimal listings from links
            for link in watch_links[:15]:  # Limit to prevent overload
                href = link.get('href')
                if not href.startswith('http'):
                    href = self.BASE_URL + href
                
                link_text = link.get_text(strip=True)
                if not link_text or len(link_text) < 3:
                    continue
                    
                listing = {
                    'source': self.source_name,
                    'url': href,
                    'source_id': self.generate_source_id(href),
                    'scraped_at': datetime.now().isoformat(),
                    'title': link_text,
                    'brand': 'Rolex',  # Assumption for Rolex category pages
                    'model': 'Unknown',
                    'reference_number': 'Unknown',
                    'price_usd': 0,  # Would need individual page scraping
                    'comparison_key': 'unknown-standard',
                    'condition': 'unknown',
                    'has_box': False,
                    'has_papers': False
                }
                
                # Try to extract basic info from link text
                self.parse_title_info(listing)
                listings.append(listing)
        
        # Method 3: Look for JSON-LD structured data
        if not listings:
            json_scripts = soup.find_all('script', type='application/ld+json')
            for script in json_scripts:
                try:
                    data = json.loads(script.string)
                    if isinstance(data, list):
                        for item in data:
                            if item.get('@type') == 'Product':
                                listing = self.parse_json_ld(item, base_url)
                                if listing:
                                    listings.append(listing)
                    elif data.get('@type') == 'Product':
                        listing = self.parse_json_ld(data, base_url)
                        if listing:
                            listings.append(listing)
                except (json.JSONDecodeError, KeyError) as e:
                    logger.debug(f"Error parsing JSON-LD: {e}")
                    continue
            
            if listings:
                logger.info(f"Fallback: Found {len(listings)} products from JSON-LD")
        
        return listings
    
    def parse_title_info(self, listing: Dict):
        """Extract basic info from title text"""
        title = listing.get('title', '').lower()
        
        # Extract model from title
        models = ['submariner', 'gmt', 'daytona', 'datejust', 'explorer', 'sea-dweller', 'yacht-master', 'day-date']
        for model in models:
            if model.replace('-', '') in title.replace('-', '').replace(' ', ''):
                listing['model'] = model.title().replace('-', '-')
                break
        
        # Extract reference number (look for 5-6 digit numbers)
        ref_match = re.search(r'\b(\d{4,6}[A-Z]*)\b', listing.get('title', ''))
        if ref_match:
            listing['reference_number'] = ref_match.group(1)
            
        # Generate comparison key
        listing['comparison_key'] = f"{listing['reference_number']}-standard"
    
    def parse_json_ld(self, data: Dict, base_url: str) -> Optional[Dict]:
        """Parse JSON-LD structured data"""
        try:
            listing = {
                'source': self.source_name,
                'scraped_at': datetime.now().isoformat(),
                'brand': data.get('brand', {}).get('name', 'Unknown'),
                'title': data.get('name', 'Unknown'),
                'model': 'Unknown',
                'reference_number': data.get('model', 'Unknown'),
                'url': data.get('url', base_url),
                'source_id': self.generate_source_id(data.get('url', base_url)),
                'price_usd': 0,
                'comparison_key': 'unknown-standard',
                'condition': 'unknown',
                'has_box': False,
                'has_papers': False
            }
            
            # Parse offers for price
            offers = data.get('offers')
            if offers:
                if isinstance(offers, list) and offers:
                    offers = offers[0]
                
                price = offers.get('price')
                currency = offers.get('priceCurrency', 'GBP')
                
                if price:
                    try:
                        price_value = float(price)
                        if currency == 'GBP':
                            listing['price_usd'] = int(price_value * self.gbp_to_usd_rate)
                            listing['original_currency'] = 'GBP'
                            listing['original_price'] = price_value
                        else:
                            listing['price_usd'] = int(price_value)
                    except (ValueError, TypeError):
                        pass
            
            self.parse_title_info(listing)
            return listing
            
        except Exception as e:
            logger.debug(f"Error parsing JSON-LD item: {e}")
            return None
    
    def detect_watch_variations(self, listing: Dict):
        """Detect watch variations for Watchfinder listings"""
        title = listing.get('title', '').lower()
        url = listing.get('url', '').lower()
        reference = listing.get('reference_number', 'unknown')
        
        search_text = f"{title} {url}".lower()
        
        # UK market variations (similar to other scrapers but UK-specific)
        variations = {
            'tiffany': {
                'keywords': ['tiffany', 'tiffany & co', 'tiffany dial'],
                'dial_type': 'Tiffany',
                'special_edition': 'Tiffany & Co',
                'suffix': 'tiffany'
            },
            'gold': {
                'keywords': ['18k', '18ct', 'yellow gold', 'rose gold', 'white gold', 'solid gold'],
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
            'green': {
                'keywords': ['green dial', 'green bezel', 'hulk', 'kermit'],
                'dial_type': 'Green',
                'special_edition': 'Hulk (Green Dial)',
                'suffix': 'hulk'
            },
            'vintage': {
                'keywords': ['vintage', '1960s', '1970s', '1980s'],
                'dial_type': 'Vintage',
                'special_edition': 'Vintage',
                'suffix': 'vintage'
            }
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
                logger.info(f"Detected {var_info['special_edition']} variation in Watchfinder listing")
                break
        
        listing['comparison_key'] = f"{reference}-{detected_suffix}"
    
    def scrape_listing(self, url: str) -> Optional[Dict]:
        """Required by base class - could enhance for individual page scraping"""
        return None

# Test function
if __name__ == "__main__":
    scraper = WatchfinderScraper()
    results = scraper.scrape_search_results(max_pages=1)
    
    print(f"\n=== Found {len(results)} listings from Watchfinder ===" )
    for i, listing in enumerate(results[:5], 1):
        print(f"\n{i}. {listing.get('title', 'Unknown')}")
        print(f"   Brand: {listing.get('brand', 'N/A')}")
        print(f"   Model: {listing.get('model', 'N/A')}")
        print(f"   Reference: {listing.get('reference_number', 'N/A')}")
        print(f"   Price: ${listing.get('price_usd', 0):,.0f} (£{listing.get('original_price', 0):,.0f})")
        print(f"   Year: {listing.get('year', 'N/A')}")
        print(f"   Condition: {listing.get('condition', 'N/A')}")
        print(f"   Box/Papers: {listing.get('has_box', False)}/{listing.get('has_papers', False)}")
        print(f"   URL: {listing.get('url', 'N/A')[:80]}...")