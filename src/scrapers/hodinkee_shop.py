"""Hodinkee Shop scraper - premium curated watch marketplace"""
from typing import Dict, List, Optional
import re
import json
import requests
from bs4 import BeautifulSoup
from loguru import logger
from datetime import datetime
from .base_scraper import BaseScraper

class HodinkeeShopScraper(BaseScraper):
    """Scraper for Hodinkee Shop - premium watch marketplace"""
    
    BASE_URL = "https://shop.hodinkee.com"
    
    def __init__(self):
        super().__init__(delay_range=(2, 4))  # Be respectful to Hodinkee
        self.source_name = "hodinkee_shop"
    
    def scrape_search_results(self, search_url: str = None, max_pages: int = 1) -> List[Dict]:
        """Scrape Hodinkee Shop watch listings"""
        listings = []
        
        # Hodinkee has curated collections
        if not search_url:
            search_urls = [
                "https://shop.hodinkee.com/collections/watches",
                "https://shop.hodinkee.com/collections/rolex"
            ]
        else:
            search_urls = [search_url]
        
        for url in search_urls[:max_pages]:
            logger.info(f"Scraping Hodinkee Shop: {url}")
            
            try:
                soup = self.get_page(url)
                if not soup:
                    logger.warning(f"Failed to get content from {url}")
                    continue
                
                logger.info(f"Page title: {soup.title.get_text() if soup.title else 'No title'}")
                
                # Hodinkee uses Shopify, so look for typical Shopify product patterns
                product_selectors = [
                    '.product-card',
                    '.product-item',
                    '[data-product-id]',
                    '.grid-product',
                    'article',
                    '.product'
                ]
                
                products = []
                for selector in product_selectors:
                    products = soup.find_all(selector)
                    if products:
                        logger.info(f"Found {len(products)} products using selector: {selector}")
                        break
                
                if not products:
                    # Fallback: Look for product links
                    all_links = soup.find_all('a', href=True)
                    product_links = [link for link in all_links if '/products/' in link.get('href', '')]
                    logger.info(f"Fallback: Found {len(product_links)} product links")
                    
                    for link in product_links[:20]:  # Limit to prevent overload
                        href = link.get('href')
                        if not href.startswith('http'):
                            href = self.BASE_URL + href
                        
                        listing = {
                            'source': self.source_name,
                            'url': href,
                            'source_id': self.generate_source_id(href),
                            'scraped_at': datetime.now().isoformat(),
                            'title': link.get_text(strip=True) or 'Unknown',
                        }
                        
                        # Try to extract basic info from link text
                        self.parse_basic_info(listing)
                        if 'brand' in listing and 'price_usd' not in listing:
                            listing['price_usd'] = 0  # Placeholder - would need individual page scraping
                        
                        if 'brand' in listing:  # Only add if we found basic watch info
                            listings.append(listing)
                else:
                    # Parse product cards
                    for product in products:
                        try:
                            listing_data = self.parse_product_card(product)
                            if listing_data:
                                listings.append(listing_data)
                        except Exception as e:
                            logger.debug(f"Error parsing product: {e}")
                            continue
                
            except Exception as e:
                logger.error(f"Error scraping {url}: {e}")
                continue
        
        logger.info(f"Scraped {len(listings)} listings from Hodinkee Shop")
        return listings
    
    def parse_product_card(self, element) -> Optional[Dict]:
        """Parse Shopify product card"""
        try:
            listing = {
                'source': self.source_name,
                'scraped_at': datetime.now().isoformat()
            }
            
            # Get product URL
            link = element.find('a', href=True)
            if link:
                href = link.get('href')
                if not href.startswith('http'):
                    href = self.BASE_URL + href
                listing['url'] = href
                listing['source_id'] = self.generate_source_id(href)
            
            # Get title
            title_selectors = [
                '.product-title', '.card-title', 'h3', 'h2', '.title', '.product-card-title'
            ]
            for selector in title_selectors:
                title_elem = element.find(selector)
                if title_elem:
                    listing['title'] = title_elem.get_text(strip=True)
                    break
            
            # Get price
            price_selectors = [
                '.price', '.product-price', '.money', '[data-price]', '.price-item'
            ]
            for selector in price_selectors:
                price_elem = element.find(selector)
                if price_elem:
                    price_text = price_elem.get_text(strip=True)
                    listing['price_usd'] = self.clean_price(price_text)
                    break
            
            # Parse watch details
            if 'title' in listing:
                self.parse_basic_info(listing)
                self.detect_watch_variations(listing)
            
            return listing if 'url' in listing and 'title' in listing else None
            
        except Exception as e:
            logger.error(f"Error parsing product card: {e}")
            return None
    
    def parse_basic_info(self, listing: Dict):
        """Extract basic watch info from title"""
        title = listing.get('title', '').lower()
        
        # Extract brand
        brands = ['rolex', 'omega', 'tudor', 'patek philippe', 'audemars piguet', 
                 'vacheron constantin', 'jaeger-lecoultre', 'cartier', 'breitling']
        
        for brand in brands:
            if brand in title:
                listing['brand'] = brand.title()
                break
        
        # For Rolex, extract model and reference
        if listing.get('brand') == 'Rolex':
            models = {
                'submariner': 'Submariner',
                'gmt-master': 'GMT-Master',
                'gmt master': 'GMT-Master', 
                'daytona': 'Daytona',
                'datejust': 'Datejust',
                'explorer': 'Explorer',
                'sea-dweller': 'Sea-Dweller',
                'yacht-master': 'Yacht-Master',
                'day-date': 'Day-Date'
            }
            
            for key, model in models.items():
                if key in title:
                    listing['model'] = model
                    break
            
            # Extract reference number
            ref_match = re.search(r'\b(\d{4,6}[A-Z]*)\b', listing.get('title', ''))
            if ref_match:
                listing['reference_number'] = ref_match.group(1)
    
    def detect_watch_variations(self, listing: Dict):
        """Detect watch variations (same logic as other scrapers)"""
        title = listing.get('title', '').lower()
        url = listing.get('url', '').lower()
        reference = listing.get('reference_number', 'unknown')
        
        search_text = f"{title} {url}".lower()
        
        # Basic variations for Hodinkee (they tend to have unique/special pieces)
        variations = {
            'tiffany': {
                'keywords': ['tiffany', 'tiffany & co'],
                'dial_type': 'Tiffany',
                'special_edition': 'Tiffany & Co',
                'suffix': 'tiffany'
            },
            'tropical': {
                'keywords': ['tropical', 'brown dial'],
                'dial_type': 'Tropical',
                'special_edition': 'Tropical Dial',
                'suffix': 'tropical'
            },
            'vintage': {
                'keywords': ['vintage', '1960s', '1970s'],
                'dial_type': 'Vintage',
                'special_edition': 'Vintage',
                'suffix': 'vintage'
            },
            'rare': {
                'keywords': ['rare', 'exceptional', 'unique'],
                'dial_type': 'Rare',
                'special_edition': 'Rare/Unique',
                'suffix': 'rare'
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
                logger.info(f"Detected {var_info['special_edition']} variation in Hodinkee listing")
                break
        
        listing['comparison_key'] = f"{reference}-{detected_suffix}"
    
    def scrape_listing(self, url: str) -> Optional[Dict]:
        """Required by base class - simple implementation"""
        return None

# Test function
if __name__ == "__main__":
    scraper = HodinkeeShopScraper()
    results = scraper.scrape_search_results(max_pages=1)
    
    print(f"\n=== Found {len(results)} listings from Hodinkee Shop ===")
    for i, listing in enumerate(results[:5], 1):
        print(f"\n{i}. {listing.get('title', 'Unknown')}")
        print(f"   Brand: {listing.get('brand', 'N/A')}")
        print(f"   Model: {listing.get('model', 'N/A')}")
        print(f"   Reference: {listing.get('reference_number', 'N/A')}")
        print(f"   Price: ${listing.get('price_usd', 0):,.0f}")
        print(f"   URL: {listing.get('url', 'N/A')[:80]}...")