"""Crown & Caliber scraper - major pre-owned luxury watch dealer"""
from typing import Dict, List, Optional
import re
import json
import requests
from bs4 import BeautifulSoup
from loguru import logger
from datetime import datetime
from .base_scraper import BaseScraper

class CrownCaliberScraper(BaseScraper):
    """Scraper for Crown & Caliber"""
    
    BASE_URL = "https://www.crownandcaliber.com"
    
    def __init__(self):
        super().__init__(delay_range=(1, 3))
        self.source_name = "crown_caliber"
    
    def scrape_search_results(self, search_url: str = None, max_pages: int = 1) -> List[Dict]:
        """Scrape Crown & Caliber listings"""
        listings = []
        
        # Test with a simple URL first
        if not search_url:
            search_url = "https://www.crownandcaliber.com/collections/rolex-submariner"
        
        logger.info(f"Scraping Crown & Caliber: {search_url}")
        
        try:
            soup = self.get_page(search_url)
            if not soup:
                logger.error("Failed to get page content")
                return listings
                
            logger.info(f"Page title: {soup.title.get_text() if soup.title else 'No title'}")
            
            # Look for product links as a simple test
            all_links = soup.find_all('a', href=True)
            product_links = [link for link in all_links if '/products/' in link.get('href', '')]
            logger.info(f"Found {len(product_links)} product links")
            
            # Test with first few product links
            for i, link in enumerate(product_links[:5]):
                href = link.get('href')
                if not href.startswith('http'):
                    href = self.BASE_URL + href
                    
                logger.info(f"Testing product link {i+1}: {href}")
                
                # Basic listing structure
                listing = {
                    'source': self.source_name,
                    'url': href,
                    'source_id': self.generate_source_id(href),
                    'scraped_at': datetime.now().isoformat(),
                    'title': link.get_text(strip=True) if link else 'Unknown',
                    'brand': 'Rolex',  # Assumption for initial test
                    'model': 'Unknown',
                    'reference_number': 'Unknown',
                    'price_usd': 0,  # We'll need to scrape individual pages
                    'comparison_key': 'unknown-standard'
                }
                listings.append(listing)
        
        except Exception as e:
            logger.error(f"Error scraping Crown & Caliber: {e}")
        
        logger.info(f"Found {len(listings)} listings from Crown & Caliber")
        return listings
    
    def scrape_listing(self, url: str) -> Optional[Dict]:
        """Required by base class - simple implementation for now"""
        return None

# Test function
if __name__ == "__main__":
    scraper = CrownCaliberScraper()
    results = scraper.scrape_search_results(max_pages=1)
    
    print(f"\n=== Found {len(results)} listings ===")
    for i, listing in enumerate(results[:3], 1):
        print(f"\n{i}. {listing.get('title', 'Unknown')}")
        print(f"   URL: {listing.get('url', 'N/A')[:80]}...")