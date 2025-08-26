"""Bob's Watches scraper"""
from typing import Dict, List, Optional
import re
import json
import requests
from bs4 import BeautifulSoup
from loguru import logger
from datetime import datetime
from .base_scraper import BaseScraper

class BobsWatchesScraper(BaseScraper):
    """Scraper for Bob's Watches"""
    
    BASE_URL = "https://www.bobswatches.com"
    
    def __init__(self):
        super().__init__(delay_range=(1, 2))
        self.source_name = "bobs_watches"
    
    def scrape_search_results(self, search_url: str = None, max_pages: int = 1) -> List[Dict]:
        """Scrape Rolex listings"""
        listings = []
        
        if not search_url:
            search_url = "https://www.bobswatches.com/rolex-submariner-1.html"
        
        logger.info(f"Scraping Bob's Watches: {search_url}")
        
        # Use requests directly to bypass base scraper issues
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        response = requests.get(search_url, headers=headers)
        if response.status_code != 200:
            logger.error(f"Failed to fetch page: {response.status_code}")
            return listings
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract all JSON-LD scripts
        scripts = soup.find_all('script', type='application/ld+json')
        logger.info(f"Found {len(scripts)} JSON-LD scripts")
        
        for script in scripts:
            try:
                data = json.loads(script.string)
                
                # Check if it's directly a Product
                if isinstance(data, dict) and data.get('@type') == 'Product':
                    listing = self.parse_product_data(data)
                    if listing:
                        listings.append(listing)
                        
            except json.JSONDecodeError as e:
                logger.debug(f"Failed to parse JSON: {e}")
                continue
        
        logger.info(f"Scraped {len(listings)} listings from Bob's Watches")
        return listings
    
    def parse_product_data(self, data: dict) -> Optional[Dict]:
        """Parse structured product data"""
        try:
            listing = {
                'source': self.source_name,
                'brand': 'Rolex',
                'scraped_at': datetime.now().isoformat()
            }
            
            # Extract name and model
            if 'name' in data:
                listing['title'] = data['name']
                # Extract model from name
                listing['model'] = self.extract_model_from_title(data['name'])
                
                # Try to extract reference number from name
                ref_match = re.search(r'\b(\d{4,6}[A-Z]*)\b', data['name'])
                if ref_match:
                    listing['reference_number'] = ref_match.group(1)
            
            # Extract URL
            if 'url' in data:
                listing['url'] = data['url']
                listing['source_id'] = self.generate_source_id(data['url'])
            
            # Extract price
            if 'offers' in data and isinstance(data['offers'], dict):
                price = data['offers'].get('price')
                if price:
                    listing['price_usd'] = float(price)
            
            # Extract SKU
            if 'sku' in data:
                listing['sku'] = data['sku']
            
            # Extract condition
            if 'itemCondition' in data:
                condition = data['itemCondition']
                if 'New' in condition:
                    listing['condition'] = 'new'
                elif 'Used' in condition:
                    listing['condition'] = 'pre-owned'
            
            # Extract MPN as potential reference
            if 'mpn' in data and 'reference_number' not in listing:
                listing['reference_number'] = data['mpn']
            
            # Extract color/material
            if 'color' in data:
                listing['material'] = data['color']
            
            # Detect watch variations for accurate price comparison
            self.detect_watch_variations(listing)
            
            return listing if 'url' in listing and 'price_usd' in listing else None
            
        except Exception as e:
            logger.error(f"Error parsing product data: {e}")
            return None
    
    def extract_model_from_title(self, title: str) -> str:
        """Extract Rolex model from title"""
        models = ['Submariner', 'GMT-Master', 'Daytona', 'Datejust', 'Explorer', 
                  'Sea-Dweller', 'Yacht-Master', 'Milgauss', 'Air-King', 'Day-Date']
        
        title_lower = title.lower()
        for model in models:
            if model.lower() in title_lower:
                return model
        
        return "Unknown"
    
    def scrape_listing(self, url: str) -> Optional[Dict]:
        """Scrape a single listing page (required by base class)"""
        logger.info(f"Scraping single listing: {url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Try to find JSON-LD data
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get('@type') == 'Product':
                    return self.parse_product_data(data)
            except:
                continue
        
        return None
    
    def detect_watch_variations(self, listing: Dict) -> None:
        """Detect watch variations for accurate price comparison"""
        title = listing.get('title', '').lower()
        url = listing.get('url', '').lower()
        reference = listing.get('reference_number', 'unknown')
        
        # Combine title and URL for detection (URL can contain variation info)
        search_text = f"{title} {url}".lower()
        
        # Initialize variation fields
        listing['dial_type'] = None
        listing['special_edition'] = None
        
        # Define variation patterns (order matters - more specific first)
        variations = {
            'tiffany': {
                'keywords': ['tiffany', 'tiffany & co', 'tiffany dial'],
                'dial_type': 'Tiffany',
                'special_edition': 'Tiffany & Co',
                'suffix': 'tiffany'
            },
            'tropical': {
                'keywords': ['tropical', 'tropical dial', 'brown dial'],
                'dial_type': 'Tropical',
                'special_edition': 'Tropical Dial',
                'suffix': 'tropical'
            },
            'spider': {
                'keywords': ['spider', 'spider dial', 'cracked dial'],
                'dial_type': 'Spider',
                'special_edition': 'Spider Dial',
                'suffix': 'spider'
            },
            'sigma': {
                'keywords': ['sigma', 'sigma dial'],
                'dial_type': 'Sigma',
                'special_edition': 'Sigma Dial',
                'suffix': 'sigma'
            },
            'comex': {
                'keywords': ['comex', 'comex dial'],
                'dial_type': 'COMEX',
                'special_edition': 'COMEX',
                'suffix': 'comex'
            },
            'dominos': {
                'keywords': ['domino', "domino's", 'dominos'],
                'dial_type': 'Dominos',
                'special_edition': "Domino's Pizza",
                'suffix': 'dominos'
            },
            'military': {
                'keywords': ['military', 'mil-sub', 'milsub'],
                'dial_type': 'Military',
                'special_edition': 'Military Submariner',
                'suffix': 'military'
            },
            'kermit': {
                'keywords': ['kermit', 'green bezel'],
                'dial_type': 'Kermit',
                'special_edition': 'Kermit (Green Bezel)',
                'suffix': 'kermit'
            },
            'hulk': {
                'keywords': ['hulk', 'green dial'],
                'dial_type': 'Hulk',
                'special_edition': 'Hulk (Green Dial)',
                'suffix': 'hulk'
            },
            # Material variations (these significantly affect price)
            'yellow_gold': {
                'keywords': ['yellow gold', 'gold', '18k gold', 'yellow-gold'],
                'dial_type': 'Gold',
                'special_edition': 'Yellow Gold',
                'suffix': 'gold'
            },
            'two_tone': {
                'keywords': ['two tone', 'two-tone', 'steel gold', 'steel-gold'],
                'dial_type': 'Two-Tone',
                'special_edition': 'Steel & Gold',
                'suffix': 'twotone'
            },
            # Dial color variations (affect value)
            'blue_dial': {
                'keywords': ['blue dial', 'blue-dial', 'blue face'],
                'dial_type': 'Blue',
                'special_edition': 'Blue Dial',
                'suffix': 'blue'
            },
            'white_dial': {
                'keywords': ['white dial', 'white-dial', 'white face', 'white submariner', 'white-submariner'],
                'dial_type': 'White',
                'special_edition': 'White Dial',
                'suffix': 'white'
            },
            'red_writing': {
                'keywords': ['red writing', 'red-writing', 'red text', 'red submariner'],
                'dial_type': 'Red Writing',
                'special_edition': 'Red Writing',
                'suffix': 'red'
            },
            'silver_dial': {
                'keywords': ['silver dial', 'silver-dial', 'silver face'],
                'dial_type': 'Silver',
                'special_edition': 'Silver Dial',
                'suffix': 'silver'
            },
            # Bezel variations (important for value)
            'blue_bezel': {
                'keywords': ['blue bezel', 'blue-bezel'],
                'dial_type': 'Blue Bezel',
                'special_edition': 'Blue Bezel',
                'suffix': 'bluebezel'
            },
            'green_bezel': {
                'keywords': ['green bezel', 'green-bezel'],
                'dial_type': 'Green Bezel', 
                'special_edition': 'Green Bezel',
                'suffix': 'greenbezel'
            },
            'black_bezel': {
                'keywords': ['black bezel', 'black-bezel'],
                'dial_type': 'Black Bezel',
                'special_edition': 'Black Bezel',
                'suffix': 'blackbezel'
            },
            # Special dial configurations
            'slate_serti': {
                'keywords': ['slate serti', 'slate-serti', 'serti'],
                'dial_type': 'Serti',
                'special_edition': 'Slate Serti',
                'suffix': 'serti'
            },
            'champagne_dial': {
                'keywords': ['champagne dial', 'champagne-dial', 'champagne face'],
                'dial_type': 'Champagne',
                'special_edition': 'Champagne Dial',
                'suffix': 'champagne'
            }
        }
        
        # Check for variations in both title and URL
        detected_suffix = 'standard'
        for var_key, var_info in variations.items():
            if any(keyword in search_text for keyword in var_info['keywords']):
                listing['dial_type'] = var_info['dial_type']
                listing['special_edition'] = var_info['special_edition']
                detected_suffix = var_info['suffix']
                logger.info(f"Detected {var_info['special_edition']} variation in: {listing.get('title', '')[:30]}... / URL: {listing.get('url', '')[:50]}...")
                break
        
        # Generate comparison key
        listing['comparison_key'] = f"{reference}-{detected_suffix}"
        logger.debug(f"Generated comparison key: {listing['comparison_key']}")