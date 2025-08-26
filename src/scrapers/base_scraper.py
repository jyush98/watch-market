"""Base scraper class with common functionality"""
import time
import random
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import requests
from bs4 import BeautifulSoup
from loguru import logger
from datetime import datetime
import hashlib

class BaseScraper(ABC):
    """Base class for all watch scrapers"""
    
    def __init__(self, delay_range=(1, 3)):
        self.session = requests.Session()
        self.delay_range = delay_range
        self.setup_session()
        
    def setup_session(self):
        """Configure session with headers"""
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
        })
    
    def get_page(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch and parse a page with retry logic"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Random delay to avoid rate limiting
                delay = random.uniform(*self.delay_range)
                time.sleep(delay)
                
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                
                return BeautifulSoup(response.content, 'html.parser')
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt == max_retries - 1:
                    logger.error(f"Failed to fetch {url} after {max_retries} attempts")
                    return None
                time.sleep(2 ** attempt)  # Exponential backoff
    
    def generate_source_id(self, url: str) -> str:
        """Generate unique ID for a listing"""
        return hashlib.md5(url.encode()).hexdigest()[:16]
    
    @abstractmethod
    def scrape_listing(self, url: str) -> Optional[Dict]:
        """Scrape a single listing - implement in subclass"""
        pass
    
    @abstractmethod
    def scrape_search_results(self, search_url: str, max_pages: int = 1) -> List[Dict]:
        """Scrape search results - implement in subclass"""
        pass
    
    def clean_price(self, price_text: str) -> Optional[float]:
        """Extract numeric price from text"""
        import re
        # Remove common currency symbols and commas
        cleaned = re.sub(r'[^\d.]', '', price_text)
        try:
            return float(cleaned)
        except (ValueError, AttributeError):
            return None