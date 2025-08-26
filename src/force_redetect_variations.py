"""Force re-detect variations for all existing records"""
from database.connection import SessionLocal, init_database
from database.models import WatchListing
from scrapers.bobs_watches import BobsWatchesScraper
from loguru import logger
from typing import Dict

def detect_variations_for_existing_record(listing: WatchListing) -> Dict:
    """Apply variation detection logic to existing database record"""
    # Get title from raw_data or URL as fallback
    title = ''
    if listing.raw_data and isinstance(listing.raw_data, dict):
        title = listing.raw_data.get('name', '')
    
    # If no title in raw_data, try to extract from URL
    if not title and listing.url:
        # Extract meaningful text from URL
        url_parts = listing.url.split('/')[-1].replace('.html', '').replace('-', ' ')
        title = url_parts
    
    # Create a temporary dict to mimic scraped data structure
    temp_listing = {
        'title': title,
        'reference_number': listing.reference_number or 'unknown',
        'url': listing.url  # Include URL for additional detection
    }
    
    # Use the same variation detection logic from the scraper
    scraper = BobsWatchesScraper()
    scraper.detect_watch_variations(temp_listing)
    
    return {
        'dial_type': temp_listing.get('dial_type'),
        'special_edition': temp_listing.get('special_edition'),
        'comparison_key': temp_listing.get('comparison_key')
    }

def force_redetect_all_variations():
    """Force re-detect variations for ALL existing records"""
    logger.info("Force re-detecting variations for all existing data...")
    
    db = SessionLocal()
    try:
        # Get ALL existing records (ignore comparison_key status)
        existing_records = db.query(WatchListing).all()
        
        logger.info(f"Found {len(existing_records)} records to re-analyze")
        
        updated_count = 0
        tiffany_found = 0
        special_variations_found = 0
        
        for record in existing_records:
            try:
                # Store old comparison key for comparison
                old_key = record.comparison_key
                
                # Apply variation detection
                variations = detect_variations_for_existing_record(record)
                
                # Update the record
                record.dial_type = variations['dial_type']
                record.special_edition = variations['special_edition']
                record.comparison_key = variations['comparison_key']
                
                # Track special findings
                if variations['special_edition']:
                    special_variations_found += 1
                    logger.success(f"Found special variation: {variations['special_edition']} - {record.url}")
                    
                if 'tiffany' in variations['comparison_key'].lower():
                    tiffany_found += 1
                    logger.success(f"🎯 TIFFANY DETECTED: {record.url}")
                
                # Log if comparison key changed
                if old_key != variations['comparison_key']:
                    logger.info(f"Updated: {old_key} → {variations['comparison_key']}")
                
                updated_count += 1
                
                if updated_count % 10 == 0:
                    logger.info(f"Re-analyzed {updated_count} records...")
                    
            except Exception as e:
                logger.error(f"Error re-analyzing record {record.id}: {e}")
                continue
        
        # Commit all changes
        db.commit()
        logger.success(f"Successfully re-analyzed {updated_count} records")
        logger.success(f"Found {special_variations_found} special variations")
        logger.success(f"Found {tiffany_found} Tiffany dials")
        
        # Show updated statistics
        show_updated_migration_stats(db)
        
    except Exception as e:
        logger.error(f"Force re-detection failed: {e}")
        db.rollback()
    finally:
        db.close()

def show_updated_migration_stats(db):
    """Show statistics after re-detection"""
    logger.info("\n=== Updated Migration Statistics ===")
    
    # Total records with comparison_key
    total_with_key = db.query(WatchListing).filter(
        WatchListing.comparison_key != None
    ).count()
    
    # Records by variation type
    variation_stats = {}
    
    # Standard watches
    standard_count = db.query(WatchListing).filter(
        WatchListing.comparison_key.like('%-standard')
    ).count()
    variation_stats['Standard'] = standard_count
    
    # Special variations
    special_variations = ['tiffany', 'tropical', 'spider', 'comex', 'dominos', 'military', 'kermit', 'hulk']
    for variation in special_variations:
        count = db.query(WatchListing).filter(
            WatchListing.comparison_key.like(f'%-{variation}')
        ).count()
        if count > 0:
            variation_stats[variation.title()] = count
    
    logger.info(f"Total records with comparison_key: {total_with_key}")
    for variation, count in variation_stats.items():
        logger.info(f"  {variation}: {count} records")
    
    # Show any special edition examples
    special_records = db.query(WatchListing).filter(
        WatchListing.special_edition != None
    ).limit(5).all()
    
    if special_records:
        logger.info(f"\nSpecial Edition Examples:")
        for record in special_records:
            logger.info(f"  {record.special_edition}: {record.url}")

if __name__ == "__main__":
    # Make sure database is initialized
    init_database()
    force_redetect_all_variations()