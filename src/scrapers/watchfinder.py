"""Watchfinder & Co scraper - premium UK luxury watch dealer"""
from typing import Dict, List, Optional
import re
import json
import requests
import time
from bs4 import BeautifulSoup
from loguru import logger
from datetime import datetime

# Browser automation imports
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

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
    
    def __init__(self, use_browser=False):
        super().__init__(delay_range=(2, 4))  # Be respectful - UK site
        self.source_name = "watchfinder"
        self.use_browser = use_browser
        self.driver = None
        
        # GBP to USD conversion (approximate - could be enhanced with real-time rates)
        self.gbp_to_usd_rate = 1.27  # As of 2024
    
    def setup_browser(self):
        """Setup headless Chrome browser for JavaScript rendering"""
        if self.driver:
            return
            
        logger.info("🌐 Setting up headless Chrome browser...")
        
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            logger.success("✅ Browser ready for JavaScript rendering")
        except Exception as e:
            logger.error(f"❌ Failed to setup browser: {e}")
            self.use_browser = False
    
    def cleanup_browser(self):
        """Clean up browser resources"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("🧹 Browser cleaned up")
            except:
                pass
            finally:
                self.driver = None
    
    def get_page_with_browser(self, url: str, wait_for_js=True):
        """Get page content after JavaScript execution"""
        try:
            logger.info(f"🌐 Loading {url} with browser automation...")
            self.driver.get(url)
            
            if wait_for_js:
                # Wait for the product container to be populated
                logger.info("⏳ Waiting for JavaScript to populate product data...")
                
                # Wait up to 15 seconds for products to load
                try:
                    # Wait for either products to appear or timeout
                    WebDriverWait(self.driver, 15).until(
                        lambda driver: (
                            # Check if _stockSearchArray has items
                            driver.execute_script("return window._stockSearchArray && window._stockSearchArray.length > 0") or
                            # Or check if DOM has product elements
                            len(driver.find_elements(By.CSS_SELECTOR, ".products_-container > *")) > 0
                        )
                    )
                    logger.success("✅ JavaScript execution completed")
                except Exception as timeout_error:
                    logger.warning(f"⚠️ Timeout waiting for JS completion: {timeout_error}")
                    # Continue anyway, might still have some data
                
                # Additional short wait to ensure rendering is complete
                time.sleep(3)
            
            # Get the rendered HTML
            html_content = self.driver.page_source
            soup = BeautifulSoup(html_content, 'html.parser')
            
            return soup
            
        except Exception as e:
            logger.error(f"❌ Browser error loading {url}: {e}")
            return None
    
    def scrape_search_results(self, search_url: str = None, max_pages: int = 1) -> List[Dict]:
        """Scrape Watchfinder watch listings with enhanced URL discovery"""
        listings = []
        
        # Setup browser if using browser automation
        if self.use_browser:
            self.setup_browser()
            if not self.driver:
                logger.error("❌ Browser setup failed, falling back to regular scraping")
                self.use_browser = False
        
        try:
            # Test different URL patterns to find where Watchfinder has actual product data
            if not search_url:
                # For browser automation, focus on the main page we know has data
                if self.use_browser:
                    search_urls = [f"{self.BASE_URL}/Rolex/watches"]
                else:
                    # Test various URL patterns
                    test_urls = [
                        f"{self.BASE_URL}/Rolex/watches",  # Main Rolex page
                        f"{self.BASE_URL}/Rolex/Submariner/watches",
                        f"{self.BASE_URL}/Rolex/GMT-Master/watches", 
                        f"{self.BASE_URL}/Rolex/Daytona/watches",
                        f"{self.BASE_URL}/Rolex/Explorer/watches",
                        f"{self.BASE_URL}/Rolex/Datejust/watches",
                        f"{self.BASE_URL}/watches?brand=Rolex",  # Query param format
                        f"{self.BASE_URL}/search?q=Rolex",  # Search format
                    ]
                    
                    # Find the best URL with actual product data
                    best_url = self.find_best_product_url(test_urls)
                    search_urls = [best_url] if best_url else test_urls[:3]
            else:
                search_urls = [search_url]
            
            for url in search_urls[:max_pages]:
                logger.info(f"🔍 Scraping Watchfinder: {url}")
                
                try:
                    # Use browser automation if enabled
                    if self.use_browser:
                        soup = self.get_page_with_browser(url, wait_for_js=True)
                    else:
                        soup = self.get_page(url)
                        
                    if not soup:
                        logger.warning(f"❌ Failed to get content from {url}")
                        continue
                    
                    page_title = soup.title.get_text() if soup.title else 'No title'
                    logger.info(f"📄 Page title: {page_title[:80]}...")
                    
                    # Extract listings using our enhanced methods
                    if self.use_browser:
                        # With browser, try DOM extraction first since JS should be executed
                        page_listings = self.extract_rendered_products(soup, url)
                    else:
                        # Without browser, try JavaScript parsing
                        page_listings = self.extract_stock_array(soup, url)
                    
                    listings.extend(page_listings)
                    
                    if page_listings:
                        logger.success(f"✅ Found {len(page_listings)} listings from {url}")
                    else:
                        logger.warning(f"⚠️ No listings found from {url}")
                    
                except Exception as e:
                    logger.error(f"❌ Error scraping {url}: {e}")
                    continue
            
        finally:
            # Always cleanup browser resources
            if self.use_browser:
                self.cleanup_browser()
        
        logger.info(f"🎉 Scraped {len(listings)} total listings from Watchfinder")
        return listings
    
    def find_best_product_url(self, test_urls: List[str]) -> Optional[str]:
        """Test different URLs to find one with actual product data"""
        logger.info("🧪 Testing URLs to find best product data source...")
        
        for url in test_urls[:6]:  # Test more URLs to find better data
            try:
                logger.debug(f"🧪 Testing: {url}")
                soup = self.get_page(url)
                
                if not soup:
                    continue
                
                # Quick test for product indicators
                scripts = soup.find_all('script')
                product_indicators = 0
                
                for script in scripts:
                    if script.string:
                        text = script.string.lower()
                        # Count indicators of product data
                        if 'stocksearcharray' in text:
                            product_indicators += 5
                        if 'productcards' in text:
                            product_indicators += 3
                        if 'watches' in text and 'price' in text:
                            product_indicators += 2
                        if 'rolex' in text:
                            product_indicators += 1
                
                logger.debug(f"📊 {url} - Product indicators: {product_indicators}")
                
                if product_indicators >= 5:
                    logger.success(f"✅ Best URL found: {url} (score: {product_indicators})")
                    return url
                    
            except Exception as e:
                logger.debug(f"Error testing {url}: {e}")
                continue
        
        logger.warning("⚠️ No optimal URL found, using default")
        return None
    
    def extract_rendered_products(self, soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """Extract products from JavaScript-rendered DOM"""
        listings = []
        
        try:
            logger.info("🔍 Extracting products from rendered DOM...")
            
            # Look for rendered product containers
            product_containers = soup.select('.products_-container')
            logger.info(f"📦 Found {len(product_containers)} product containers")
            
            for i, container in enumerate(product_containers):
                data_stock = container.get('data-stock', '0')
                logger.info(f"📦 Container {i+1}: data-stock={data_stock}")
                
                # Look for individual product elements within containers
                product_selectors = [
                    # Look for common product element patterns
                    '.product-item',
                    '.watch-item',
                    '.inventory-item', 
                    '[class*="item-"]',
                    '[class*="product"]',
                    'a[href*="/watch/"]',
                    'div[data-product-id]',
                    'div[data-stockid]',
                    # Look for any divs with substantial content
                    'div:has(img)',  # Divs with images (likely products)
                    'div:has(a[href])'  # Divs with links
                ]
                
                found_products = []
                for selector in product_selectors:
                    try:
                        items = container.select(selector)
                        if items:
                            logger.success(f"✅ Found {len(items)} items with selector: {selector}")
                            found_products.extend(items)
                            break  # Use the first successful selector
                    except:
                        continue
                
                # If no specific selectors worked, get all child elements
                if not found_products:
                    found_products = container.find_all(recursive=False)  # Direct children only
                    logger.info(f"📝 Using {len(found_products)} direct child elements")
                
                # Process found product elements
                for j, product_element in enumerate(found_products):
                    try:
                        listing = self.extract_listing_from_rendered_element(product_element, base_url)
                        if listing:
                            listings.append(listing)
                            logger.debug(f"✅ Extracted listing from container {i+1}, product {j+1}")
                    except Exception as e:
                        logger.debug(f"❌ Error processing product {j+1}: {e}")
                        continue
            
            # Fallback: look for product links anywhere on the page
            if not listings:
                logger.info("🔍 No container products found, trying page-wide link extraction...")
                product_links = soup.find_all('a', href=True)
                for link in product_links:
                    href = link.get('href', '').lower()
                    if any(pattern in href for pattern in ['/watch/', '/rolex-', '/ref-']):
                        try:
                            listing = self.extract_listing_from_rendered_element(link, base_url)
                            if listing:
                                listings.append(listing)
                        except:
                            continue
                        
                        if len(listings) >= 10:  # Limit fallback results
                            break
            
            logger.success(f"🎉 Extracted {len(listings)} total listings from rendered DOM")
            
        except Exception as e:
            logger.error(f"❌ Error extracting rendered products: {e}")
        
        return listings
    
    def extract_listing_from_rendered_element(self, element, base_url: str) -> Optional[Dict]:
        """Extract listing data from a rendered DOM element (after JavaScript execution)"""
        try:
            listing = {
                'source': self.source_name,
                'scraped_at': datetime.now().isoformat(),
                'brand': 'Rolex',  # Assuming this is from Rolex page
                'model': 'Unknown',
                'reference_number': 'Unknown',
                'price_usd': 0,
                'comparison_key': 'unknown-standard',
                'condition': 'unknown',
                'has_box': False,
                'has_papers': False,
                'title': 'Unknown',
                'url': base_url,
                'source_id': 'unknown'
            }
            
            # Extract URL from href if it's a link
            if element.name == 'a' and element.get('href'):
                href = element.get('href')
                if not href.startswith('http'):
                    href = self.BASE_URL + href
                listing['url'] = href
                listing['source_id'] = self.generate_source_id(href)
            
            # Extract title/text content
            element_text = element.get_text(strip=True)
            if element_text and len(element_text) > 5:
                listing['title'] = element_text[:100]  # Limit title length
            
            # Look for price information
            price_patterns = [r'£([\d,]+)', r'GBP\s*([\d,]+)', r'(\d{1,3}(?:,\d{3})+)']
            for pattern in price_patterns:
                price_match = re.search(pattern, element_text)
                if price_match:
                    try:
                        price_str = price_match.group(1).replace(',', '')
                        gbp_value = float(price_str)
                        listing['price_usd'] = int(gbp_value * self.gbp_to_usd_rate)
                        listing['original_currency'] = 'GBP'
                        listing['original_price'] = gbp_value
                        break
                    except (ValueError, TypeError):
                        continue
            
            # Extract data from attributes
            attrs = element.attrs
            for attr_name, attr_value in attrs.items():
                if 'stockid' in attr_name.lower() or 'product-id' in attr_name.lower():
                    listing['source_id'] = str(attr_value)
                elif 'price' in attr_name.lower():
                    try:
                        price_val = float(str(attr_value).replace('£', '').replace(',', ''))
                        listing['price_usd'] = int(price_val * self.gbp_to_usd_rate)
                        listing['original_price'] = price_val
                        listing['original_currency'] = 'GBP'
                    except:
                        pass
            
            # Parse title for model/reference information
            if listing['title'] != 'Unknown':
                self.enhanced_parse_title_info(listing)
                
                # Additional parsing for Watchfinder's specific format
                title_text = listing['title'].lower()
                
                # Extract reference number (look for patterns like 116613, 126660, etc.)
                ref_patterns = [
                    r'(\d{6})',  # 6-digit references
                    r'(\d{5})',  # 5-digit references  
                    r'(\d{4}[a-z]*)', # 4-digit with optional letters
                ]
                
                for pattern in ref_patterns:
                    ref_match = re.search(pattern, listing['title'])
                    if ref_match:
                        listing['reference_number'] = ref_match.group(1)
                        break
                
                # Extract year if present (look for Year2019, Year2017, etc.)
                year_match = re.search(r'year(\d{4})', listing['title'], re.IGNORECASE)
                if year_match:
                    listing['year'] = int(year_match.group(1))
                
                # Check for box/papers indicators
                if any(indicator in title_text for indicator in ['box', 'papers']):
                    if 'box' in title_text:
                        listing['has_box'] = True
                    if 'papers' in title_text:
                        listing['has_papers'] = True
                
                # Clean up title (remove redundant parts)
                clean_title = listing['title']
                clean_title = re.sub(r'boxpapers', 'Box/Papers', clean_title, flags=re.IGNORECASE)
                clean_title = re.sub(r'year\d{4}', '', clean_title, flags=re.IGNORECASE)
                clean_title = re.sub(r'£[\d,]+', '', clean_title)  # Remove price
                listing['title'] = clean_title.strip()
            
            # Only return if we got meaningful data
            if (listing['title'] != 'Unknown' or 
                listing['price_usd'] > 0 or 
                listing['url'] != base_url or
                listing['source_id'] != 'unknown'):
                return listing
            
            return None
            
        except Exception as e:
            logger.debug(f"Error extracting from rendered element: {e}")
            return None
    
    def extract_stock_array(self, soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """Extract watch data from JavaScript _stockSearchArray"""
        listings = []
        
        try:
            # Find script tags containing the stock array or any watch data
            scripts = soup.find_all('script')
            stock_data = None
            
            # Enhanced patterns for Watchfinder - try different approach
            patterns = [
                # Look for completed arrays (try these first)
                r'window\.stock_search_array\s*=\s*(\[.*?\]);',
                r'_stockSearchArrayComplete\s*=\s*(\[.*?\]);',
                r'watchData\s*=\s*(\[.*?\]);',
                r'products\s*:\s*(\[.*?\])',
                r'"watches"\s*:\s*(\[.*?\])',
                r'var\s+watches\s*=\s*(\[.*?\]);',
                r'window\.stockData\s*=\s*(\[.*?\]);',
                r'inventory\s*:\s*(\[.*?\])',
                # Then try the simple push operations (simplified to avoid multiline issues)
                r'_stockSearchArray\.push\(\s*(\{[^}]+stockId[^}]+\})\s*\)',
                r'stockSearchArray\.push\(\s*(\{[^}]+stockId[^}]+\})\s*\)',
                r'productCards\.push\(\s*(\{[^}]+\})\s*\)',
                # Skip the empty initial arrays for now
                # r'_stockSearchArray\s*=\s*(\[.*?\]);',
                # r'stockSearchArray\s*=\s*(\[.*?\]);'
            ]
            
            # Look for product data in script tags
            all_products = []
            
            for script in scripts:
                if script.string:
                    script_text = script.string
                    
                    # Debug: log scripts that mention watch-related terms
                    if any(keyword in script_text.lower() for keyword in ['watch', 'stock', 'product', 'submariner', 'rolex']):
                        logger.debug(f"🔍 Found script with watch references ({len(script_text)} chars)")
                        
                        # First try push patterns (individual product objects)
                        found_via_push = False
                        for pattern in patterns:
                            if any(push_pattern in pattern for push_pattern in ['push(', '.push']):
                                # Handle individual product objects from push operations
                                matches = re.finditer(pattern, script_text, re.DOTALL)
                                push_count = 0
                                for match in matches:
                                    try:
                                        json_text = match.group(1)
                                        # Try to fix common JavaScript to JSON issues
                                        json_text = self.js_to_json(json_text)
                                        product_obj = json.loads(json_text)
                                        all_products.append(product_obj)
                                        push_count += 1
                                    except json.JSONDecodeError as e:
                                        logger.debug(f"JSON decode error in push pattern: {e}")
                                        logger.debug(f"Failed to parse: {match.group(1)[:100]}...")
                                        continue
                                if push_count > 0:
                                    logger.success(f"✅ Found {push_count} products via {pattern} push operations")
                                    found_via_push = True
                                    break  # Found products, stop trying other patterns
                        
                        # Only try array patterns if push patterns didn't work
                        if not found_via_push:
                            for pattern in patterns:
                                if not any(push_pattern in pattern for push_pattern in ['push(', '.push']):
                                    # Handle array patterns
                                    match = re.search(pattern, script_text, re.DOTALL)
                                    if match:
                                        try:
                                            array_data = json.loads(match.group(1))
                                            if isinstance(array_data, list):
                                                if array_data:  # Only log if array has items
                                                    all_products.extend(array_data)
                                                    logger.success(f"✅ Found {len(array_data)} products with pattern: {pattern}")
                                                    break
                                                else:
                                                    logger.debug(f"📝 Skipping empty array with pattern: {pattern}")
                                                    continue  # Try next pattern instead of breaking
                                            else:
                                                all_products.append(array_data)
                                                logger.success(f"✅ Found 1 product with pattern: {pattern}")
                                                break
                                        except json.JSONDecodeError as e:
                                            logger.debug(f"JSON decode error with pattern {pattern}: {e}")
                                            continue
                        
                        if all_products:
                            break
            
            if not all_products:
                logger.warning("🔍 No stock array found in any pattern, trying enhanced fallback method")
                return self.enhanced_fallback_scraping(soup, base_url)
            
            logger.success(f"🎉 Found {len(all_products)} watches total")
            
            # Process each watch in the collected data
            for watch_data in all_products:
                listing = self.parse_stock_item(watch_data, base_url)
                if listing:
                    listings.append(listing)
                    
        except Exception as e:
            logger.error(f"❌ Error extracting stock array: {e}")
            return self.enhanced_fallback_scraping(soup, base_url)
        
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
    
    def enhanced_fallback_scraping(self, soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """Enhanced fallback method with better Watchfinder-specific parsing"""
        listings = []
        
        logger.info("🔍 Attempting enhanced fallback scraping for Watchfinder...")
        
        # Method 1: Look for modern Watchfinder product selectors
        watchfinder_selectors = [
            # Try specific product item selectors first
            '[data-product-id]',
            '.product-tile',
            '.watch-card',
            '.product-card',
            '.inventory-item',
            '.watch-listing',
            # Look inside product containers
            '.products_-container [class*="item"]',
            '.products_ [class*="item"]',
            '.products_-container > div',
            '.products_ > div',
            # Generic selectors (broader)
            '[class*="product"]:not(.products_):not(.products_-container)',
            '[class*="watch"]',
            '[class*="item"]',
            # Look for links to individual watch pages
            'a[href*="/watch/"]',
            'a[href*="/watches/"]',
            'a[href*="/rolex-"]'
        ]
        
        products = []
        for selector in watchfinder_selectors:
            products = soup.select(selector)
            if products:
                logger.success(f"🎯 Enhanced fallback: Found {len(products)} products using {selector}")
                # Debug: let's see what we actually found
                for i, product in enumerate(products[:3]):
                    logger.debug(f"🔍 Product {i+1}: tag={product.name}, classes={product.get('class', [])}, href={product.get('href', 'N/A')[:50]}, text_start='{product.get_text()[:50]}...'")
                break
        
        # Process found products from Method 1
        if products:
            logger.info(f"🔨 Processing {len(products)} containers found via DOM elements...")
            for i, container_element in enumerate(products[:25]):  # Limit to avoid overload
                try:
                    # Check if this is a container with multiple products
                    data_stock = container_element.get('data-stock')
                    if data_stock and int(data_stock) > 1:
                        logger.info(f"📦 Container {i+1} has {data_stock} products, extracting individual items...")
                        # Look for individual product items within this container
                        individual_items = container_element.find_all(['div', 'article', 'a'], 
                                                                    recursive=True)
                        
                        # Debug: let's see what's actually inside the container
                        logger.debug(f"🔍 Container has {len(individual_items)} total elements")
                        
                        # Filter for likely product items with relaxed criteria
                        product_items = []
                        for j, item in enumerate(individual_items[:20]):  # Check first 20 items
                            item_classes = ' '.join(item.get('class', [])).lower()
                            item_href = item.get('href', '').lower()
                            item_text = item.get_text(strip=True)[:50]
                            
                            logger.debug(f"    Item {j+1}: tag={item.name}, classes='{item_classes}', href='{item_href[:30]}', text='{item_text}'")
                            
                            # Look for product indicators (relaxed criteria)
                            is_product = (
                                any(keyword in item_classes for keyword in ['item', 'product', 'watch', 'card', 'tile']) or
                                any(pattern in item_href for pattern in ['/watch/', '/rolex-', '/watches/', '/ref-']) or
                                len(item_href) > 10  # Any substantial link might be a product
                            )
                            
                            if is_product:
                                product_items.append(item)
                                logger.debug(f"        ✅ Marked as potential product")
                        
                        logger.info(f"🔍 Found {len(product_items)} potential product items in container")
                        
                        # Process each individual product item
                        for j, product_item in enumerate(product_items[:10]):  # Limit per container
                            listing = self.extract_listing_from_element(product_item, base_url)
                            if listing:
                                listings.append(listing)
                                logger.debug(f"✅ Created listing from container {i+1}, item {j+1}")
                    else:
                        # Process as single product
                        listing = self.extract_listing_from_element(container_element, base_url)
                        if listing:
                            listings.append(listing)
                            logger.debug(f"✅ Created listing from element {i+1}")
                            
                except Exception as e:
                    logger.debug(f"❌ Error processing product element {i+1}: {e}")
                    continue
            
            if listings:
                logger.success(f"🎉 Enhanced fallback method 1: Created {len(listings)} listings from DOM elements")
                return listings
        
        # Method 2: Look for product links with better filtering
        if not products:
            all_links = soup.find_all('a', href=True)
            watch_links = []
            
            # Enhanced URL patterns for Watchfinder
            watch_patterns = [
                '/watch/',
                '/watches/',
                '/ref-',
                '/model-',
                '/rolex-',
                '/product/',
                '/item/'
            ]
            
            # Filter out navigation and generic links
            exclude_patterns = [
                '/watches/all',
                '/watches/new',
                '/watches/under/',
                '/watches/between/',
                '/watches/from/',
                '/brand/',
                '/series/',
                '#',
                'javascript:',
                'mailto:',
                'tel:'
            ]
            
            for link in all_links:
                href = link.get('href', '').lower()
                link_text = link.get_text(strip=True)
                
                # Include if matches watch patterns and doesn't match exclude patterns
                if (any(pattern in href for pattern in watch_patterns) and
                    not any(exclude in href for exclude in exclude_patterns) and
                    link_text and len(link_text) > 5):  # Ensure meaningful link text
                    
                    watch_links.append(link)
            
            logger.info(f"🔍 Enhanced fallback: Found {len(watch_links)} filtered watch links")
            
            # Create listings from filtered links
            for link in watch_links[:25]:  # Limit but allow more than before
                href = link.get('href')
                if not href.startswith('http'):
                    href = self.BASE_URL + href
                
                link_text = link.get_text(strip=True)
                
                listing = {
                    'source': self.source_name,
                    'url': href,
                    'source_id': self.generate_source_id(href),
                    'scraped_at': datetime.now().isoformat(),
                    'title': link_text,
                    'brand': 'Rolex',  # Assumption for Rolex pages
                    'model': 'Unknown',
                    'reference_number': 'Unknown',
                    'price_usd': 0,  # Would need individual page scraping
                    'comparison_key': 'unknown-standard',
                    'condition': 'unknown',
                    'has_box': False,
                    'has_papers': False
                }
                
                # Enhanced parsing from link text and URL
                self.enhanced_parse_title_info(listing)
                listings.append(listing)
        
        # Method 3: Look for JSON-LD and other structured data
        if not listings:
            logger.info("🔍 Trying structured data approach...")
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
                logger.success(f"✅ Enhanced fallback: Found {len(listings)} products from JSON-LD")
        
        # Method 4: Direct API endpoint attempt (if Watchfinder has one)
        if not listings:
            logger.info("🌐 Attempting to find API endpoints...")
            # This would be where we might try to find their search API
            # For now, we'll leave this as a placeholder
        
        return listings
    
    def enhanced_parse_title_info(self, listing: Dict):
        """Enhanced parsing of title and URL information"""
        title = listing.get('title', '').lower()
        url = listing.get('url', '').lower()
        
        # Extract model from title with better patterns
        model_patterns = {
            'submariner': ['submariner', 'sub'],
            'gmt-master': ['gmt', 'gmt-master', 'gmt master'],
            'daytona': ['daytona', 'cosmograph'],
            'datejust': ['datejust', 'dj'],
            'explorer': ['explorer', 'exp'],
            'sea-dweller': ['sea-dweller', 'seadweller', 'sea dweller'],
            'yacht-master': ['yacht-master', 'yachtmaster', 'yacht master'],
            'day-date': ['day-date', 'daydate', 'day date', 'president']
        }
        
        for model_key, patterns in model_patterns.items():
            if any(pattern in title or pattern in url for pattern in patterns):
                listing['model'] = model_key.title()
                break
        
        # Enhanced reference number extraction
        ref_patterns = [
            r'\b(\d{4,6}[A-Z]*)\b',  # Standard format
            r'ref\.?\s*(\d{4,6}[A-Z]*)',  # With "ref"
            r'reference\s*(\d{4,6}[A-Z]*)',  # With "reference"
        ]
        
        for pattern in ref_patterns:
            match = re.search(pattern, listing.get('title', ''), re.IGNORECASE)
            if match:
                listing['reference_number'] = match.group(1)
                break
        
        # Generate comparison key
        ref = listing.get('reference_number', 'unknown')
        listing['comparison_key'] = f"{ref}-standard"
        
        # Try to extract condition from title
        condition_patterns = {
            'new': ['new', 'unworn', 'brand new'],
            'excellent': ['excellent', 'mint', 'pristine'],
            'very good': ['very good', 'near mint'],
            'good': ['good condition', ' good '],
            'fair': ['fair', 'worn']
        }
        
        for condition, patterns in condition_patterns.items():
            if any(pattern in title for pattern in patterns):
                listing['condition'] = condition
                break

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
    
    def js_to_json(self, js_text: str) -> str:
        """Convert JavaScript object syntax to JSON"""
        try:
            json_text = js_text
            
            # Remove any trailing commas
            json_text = re.sub(r',(\s*[}\]])', r'\1', json_text)
            
            # Quote unquoted property names
            json_text = re.sub(r'(\w+):\s*', r'"\1": ', json_text)
            
            # Handle empty string values properly
            json_text = re.sub(r': \'\'([,}])', r': ""\1', json_text)
            json_text = re.sub(r': \"\"([,}])', r': ""\1', json_text)
            
            # Handle single quotes around strings
            json_text = re.sub(r": '([^']*)'", r': "\1"', json_text)
            
            # Handle unquoted string values (be more careful)
            # First handle numbers that should stay numbers
            json_text = re.sub(r': (\d+)([,}\s])', r': \1\2', json_text)
            
            # Then handle string values that aren't quoted
            json_text = re.sub(r': ([^",{\[\]\s}][^,}]*?)([,}])', r': "\1"\2', json_text)
            
            # Clean up any mess from the above operations
            json_text = re.sub(r'""([^"]*)"": ', r'"\1": ', json_text)
            json_text = re.sub(r': """([^"]*?)"""', r': "\1"', json_text)
            
            # Handle boolean values
            json_text = re.sub(r': "true"', r': true', json_text)
            json_text = re.sub(r': "false"', r': false', json_text)
            json_text = re.sub(r': "null"', r': null', json_text)
            
            return json_text
            
        except Exception as e:
            logger.debug(f"Error converting JS to JSON: {e}")
            return js_text
    
    def extract_listing_from_element(self, element, base_url: str) -> Optional[Dict]:
        """Extract watch listing data from a DOM element"""
        try:
            listing = {
                'source': self.source_name,
                'scraped_at': datetime.now().isoformat(),
                'brand': 'Rolex',  # Assuming this is from Rolex page
                'model': 'Unknown',
                'reference_number': 'Unknown',
                'price_usd': 0,
                'comparison_key': 'unknown-standard',
                'condition': 'unknown',
                'has_box': False,
                'has_papers': False,
                'title': 'Unknown',
                'url': base_url,
                'source_id': 'unknown'
            }
            
            # Try to extract product data from data attributes
            element_attrs = element.attrs
            logger.debug(f"🔍 Element attributes: {element_attrs}")
            
            # Look for product links within this element
            product_links = element.find_all('a', href=True)
            for link in product_links:
                href = link.get('href', '')
                if any(pattern in href.lower() for pattern in ['/watch/', '/watches/', '/rolex-']):
                    if not href.startswith('http'):
                        href = self.BASE_URL + href
                    listing['url'] = href
                    listing['source_id'] = self.generate_source_id(href)
                    
                    # Try to extract title from link text or nearby elements
                    link_text = link.get_text(strip=True)
                    if link_text and len(link_text) > 5:
                        listing['title'] = link_text
                    break
            
            # Look for price information in text or data attributes
            element_text = element.get_text()
            price_match = re.search(r'£([\d,]+)', element_text)
            if price_match:
                try:
                    gbp_value = float(price_match.group(1).replace(',', ''))
                    listing['price_usd'] = int(gbp_value * self.gbp_to_usd_rate)
                    listing['original_currency'] = 'GBP'
                    listing['original_price'] = gbp_value
                except (ValueError, TypeError):
                    pass
            
            # Try to extract data from any JSON embedded in data attributes
            for attr_name, attr_value in element.attrs.items():
                if 'data' in attr_name.lower() and isinstance(attr_value, str):
                    try:
                        if attr_value.startswith('{') or attr_value.startswith('['):
                            data = json.loads(attr_value)
                            if isinstance(data, dict):
                                # Extract fields if they exist
                                if 'stockId' in data:
                                    listing['source_id'] = str(data['stockId'])
                                if 'price' in data:
                                    try:
                                        price_val = float(str(data['price']).replace('£', '').replace(',', ''))
                                        listing['price_usd'] = int(price_val * self.gbp_to_usd_rate)
                                        listing['original_price'] = price_val
                                        listing['original_currency'] = 'GBP'
                                    except:
                                        pass
                                if 'brand' in data:
                                    listing['brand'] = data['brand']
                                if 'model' in data:
                                    listing['model'] = data['model']
                                if 'reference' in data:
                                    listing['reference_number'] = data['reference']
                    except (json.JSONDecodeError, KeyError):
                        continue
            
            # Enhanced title parsing if we got a title
            if listing['title'] != 'Unknown':
                self.enhanced_parse_title_info(listing)
            
            # Only return if we got meaningful data
            if (listing['title'] != 'Unknown' or 
                listing['price_usd'] > 0 or 
                listing['url'] != base_url or
                listing['source_id'] != 'unknown'):
                return listing
            
            return None
            
        except Exception as e:
            logger.debug(f"Error extracting listing from element: {e}")
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
    import sys
    
    # Check if browser automation should be used (default to True for production)
    use_browser = '--no-browser' not in sys.argv
    
    if use_browser:
        print("🌐 Using browser automation for JavaScript rendering...")
        scraper = WatchfinderScraper(use_browser=True)
    else:
        print("📄 Using traditional scraping (no browser)...")
        scraper = WatchfinderScraper(use_browser=False)
    
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