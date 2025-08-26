"""Complete scraping and storage pipeline for pricing engine"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scrapers.bobs_watches import BobsWatchesScraper
from database.connection import SessionLocal, init_database
from database.models import WatchListing
from services.price_history import PriceHistoryService
from loguru import logger
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from typing import List, Dict

class PricingEngineUpdater:
    """Complete pipeline for scraping, storing, and tracking price changes"""
    
    def __init__(self):
        # Initialize database
        init_database()
        self.db = SessionLocal()
        self.price_history_service = PriceHistoryService(self.db)
        
        # Initialize scrapers
        self.bobs_scraper = BobsWatchesScraper()
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.db:
            self.db.close()
    
    def run_full_update(self, max_pages: int = 3) -> Dict:
        """Run complete pricing engine update"""
        logger.info("🚀 Starting full pricing engine update...")
        
        results = {
            'scraped_listings': 0,
            'new_listings': 0,
            'updated_listings': 0,
            'price_changes': 0,
            'errors': 0
        }
        
        try:
            # 1. Scrape Bob's Watches
            logger.info("Step 1: Scraping Bob's Watches...")
            bobs_listings = self.scrape_bobs_watches_multiple_pages(max_pages)
            results['scraped_listings'] = len(bobs_listings)
            
            if not bobs_listings:
                logger.warning("No listings scraped from Bob's Watches")
                return results
            
            # 2. Process and store listings
            logger.info("Step 2: Processing and storing listings...")
            new_count, updated_count, price_changes = self.process_listings(bobs_listings)
            results['new_listings'] = new_count
            results['updated_listings'] = updated_count
            results['price_changes'] = price_changes
            
            # 3. Generate summary stats
            logger.info("Step 3: Generating summary...")
            self.log_summary(results)
            
            logger.success("✅ Pricing engine update completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Error during pricing engine update: {e}")
            results['errors'] = 1
            
        return results
    
    def scrape_bobs_watches_multiple_pages(self, max_pages: int = 3) -> List[Dict]:
        """Scrape multiple watch categories from Bob's Watches"""
        all_listings = []
        
        # Comprehensive Rolex model pages for complete market coverage
        urls_to_scrape = [
            "https://www.bobswatches.com/rolex-submariner-1.html",
            "https://www.bobswatches.com/rolex-gmt-master-1.html", 
            "https://www.bobswatches.com/rolex-daytona-1.html",
            "https://www.bobswatches.com/rolex-datejust-1.html",
            "https://www.bobswatches.com/rolex-explorer-1.html",
            "https://www.bobswatches.com/rolex-sea-dweller-1.html",
            "https://www.bobswatches.com/rolex-yacht-master-1.html",
            "https://www.bobswatches.com/rolex-day-date-1.html",
            "https://www.bobswatches.com/rolex-milgauss-1.html",
            "https://www.bobswatches.com/rolex-air-king-1.html",
            "https://www.bobswatches.com/rolex-oyster-perpetual-1.html",
            "https://www.bobswatches.com/rolex-sky-dweller-1.html"
        ]
        
        for i, url in enumerate(urls_to_scrape[:max_pages]):
            logger.info(f"Scraping page {i+1}/{min(max_pages, len(urls_to_scrape))}: {url}")
            try:
                listings = self.bobs_scraper.scrape_search_results(url)
                all_listings.extend(listings)
                logger.info(f"Got {len(listings)} listings from {url}")
            except Exception as e:
                logger.error(f"Error scraping {url}: {e}")
                continue
        
        # Remove duplicates by source_id
        unique_listings = {}
        for listing in all_listings:
            source_id = listing.get('source_id')
            if source_id and source_id not in unique_listings:
                unique_listings[source_id] = listing
        
        logger.info(f"Total unique listings: {len(unique_listings)}")
        return list(unique_listings.values())
    
    def process_listings(self, listings: List[Dict]) -> tuple[int, int, int]:
        """Process scraped listings and update database with price tracking"""
        new_count = 0
        updated_count = 0
        price_changes = 0
        
        for listing_data in listings:
            try:
                result = self.process_single_listing(listing_data)
                if result == 'new':
                    new_count += 1
                elif result == 'updated':
                    updated_count += 1
                elif result == 'price_change':
                    updated_count += 1
                    price_changes += 1
                    
            except Exception as e:
                logger.error(f"Error processing listing {listing_data.get('source_id', 'unknown')}: {e}")
                continue
        
        # Commit all changes
        self.db.commit()
        
        return new_count, updated_count, price_changes
    
    def process_single_listing(self, listing_data: Dict) -> str:
        """Process a single listing and return what happened (new/updated/price_change)"""
        source_id = listing_data.get('source_id')
        if not source_id:
            logger.warning("Listing missing source_id, skipping")
            return 'error'
        
        # Check if listing already exists
        existing_listing = self.db.query(WatchListing).filter(
            WatchListing.source_id == source_id
        ).first()
        
        if existing_listing:
            return self.update_existing_listing(existing_listing, listing_data)
        else:
            return self.create_new_listing(listing_data)
    
    def create_new_listing(self, listing_data: Dict) -> str:
        """Create a new watch listing"""
        try:
            # Create new listing (map fields correctly to database schema)
            new_listing = WatchListing(
                brand=listing_data.get('brand'),
                model=listing_data.get('model'),
                reference_number=listing_data.get('reference_number'),
                price_usd=listing_data.get('price_usd'),
                source=listing_data.get('source'),
                source_id=listing_data.get('source_id'),
                url=listing_data.get('url'),
                condition=listing_data.get('condition'),
                material=listing_data.get('material'),
                year=listing_data.get('year'),
                has_box=listing_data.get('has_box', False),
                has_papers=listing_data.get('has_papers', False),
                dial_type=listing_data.get('dial_type'),
                special_edition=listing_data.get('special_edition'),
                comparison_key=listing_data.get('comparison_key')
            )
            
            self.db.add(new_listing)
            self.db.flush()  # Get the ID
            
            # Record initial price history
            self.price_history_service.record_price_change(new_listing, previous_price=None)
            
            logger.info(f"✅ Created new listing: {listing_data.get('brand', 'Unknown')} {listing_data.get('model', 'Unknown')} - ${listing_data.get('price_usd', 0):,.0f}")
            return 'new'
            
        except IntegrityError as e:
            self.db.rollback()
            logger.warning(f"Listing already exists (integrity error): {source_id}")
            return 'duplicate'
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating new listing: {e}")
            return 'error'
    
    def update_existing_listing(self, existing_listing: WatchListing, listing_data: Dict) -> str:
        """Update an existing watch listing and track price changes"""
        try:
            previous_price = existing_listing.price_usd
            new_price = listing_data.get('price_usd')
            
            # Update listing fields (no title field in WatchListing model)
            existing_listing.brand = listing_data.get('brand', existing_listing.brand)
            existing_listing.model = listing_data.get('model', existing_listing.model)
            existing_listing.reference_number = listing_data.get('reference_number', existing_listing.reference_number)
            existing_listing.price_usd = new_price
            existing_listing.condition = listing_data.get('condition', existing_listing.condition)
            existing_listing.material = listing_data.get('material', existing_listing.material)
            existing_listing.year = listing_data.get('year', existing_listing.year)
            existing_listing.has_box = listing_data.get('has_box', existing_listing.has_box)
            existing_listing.has_papers = listing_data.get('has_papers', existing_listing.has_papers)
            existing_listing.dial_type = listing_data.get('dial_type', existing_listing.dial_type)
            existing_listing.special_edition = listing_data.get('special_edition', existing_listing.special_edition)
            existing_listing.comparison_key = listing_data.get('comparison_key', existing_listing.comparison_key)
            
            # Check for price change
            if previous_price != new_price and new_price is not None:
                # Record price change
                self.price_history_service.record_price_change(existing_listing, previous_price)
                
                change_amount = new_price - previous_price
                change_percent = (change_amount / previous_price) * 100 if previous_price > 0 else 0
                
                logger.info(f"💰 Price change: {existing_listing.brand} {existing_listing.model} - ${previous_price:,.0f} → ${new_price:,.0f} ({change_percent:+.1f}%)")
                return 'price_change'
            else:
                logger.debug(f"Updated listing (no price change): {existing_listing.brand} {existing_listing.model}")
                return 'updated'
                
        except Exception as e:
            logger.error(f"Error updating existing listing: {e}")
            return 'error'
    
    def log_summary(self, results: Dict):
        """Log summary of the update process"""
        logger.info("📊 PRICING ENGINE UPDATE SUMMARY:")
        logger.info(f"   • Scraped listings: {results['scraped_listings']}")
        logger.info(f"   • New listings added: {results['new_listings']}")
        logger.info(f"   • Existing listings updated: {results['updated_listings']}")
        logger.info(f"   • Price changes detected: {results['price_changes']}")
        logger.info(f"   • Errors: {results['errors']}")
        
        # Database stats
        total_listings = self.db.query(func.count(WatchListing.id)).scalar()
        try:
            from database.models import PriceHistory
            total_price_history = self.db.query(func.count(PriceHistory.id)).scalar()
        except:
            total_price_history = 0
        
        logger.info(f"   • Total listings in database: {total_listings}")
        logger.info(f"   • Total price history records: {total_price_history}")

def main():
    """Main entry point for running the pricing engine update"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Update watch pricing engine with latest data')
    parser.add_argument('--pages', type=int, default=3, help='Number of pages to scrape (default: 3)')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logger.remove()
        logger.add(sys.stderr, level="DEBUG")
    
    try:
        with PricingEngineUpdater() as updater:
            results = updater.run_full_update(max_pages=args.pages)
            
            # Exit with error code if there were errors
            if results['errors'] > 0:
                sys.exit(1)
                
    except KeyboardInterrupt:
        logger.info("Update interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()