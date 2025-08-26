"""Migration script to update existing data with comparison_key"""
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

def migrate_existing_data():
    """Update existing records with comparison_key and variation fields"""
    logger.info("Starting migration of existing data...")
    
    db = SessionLocal()
    try:
        # Get all existing records that don't have comparison_key
        existing_records = db.query(WatchListing).filter(
            WatchListing.comparison_key == None
        ).all()
        
        logger.info(f"Found {len(existing_records)} records to migrate")
        
        updated_count = 0
        for record in existing_records:
            try:
                # Apply variation detection
                variations = detect_variations_for_existing_record(record)
                
                # Update the record
                record.dial_type = variations['dial_type']
                record.special_edition = variations['special_edition']
                record.comparison_key = variations['comparison_key']
                
                updated_count += 1
                
                if updated_count % 100 == 0:
                    logger.info(f"Migrated {updated_count} records...")
                    
            except Exception as e:
                logger.error(f"Error migrating record {record.id}: {e}")
                continue
        
        # Commit all changes
        db.commit()
        logger.success(f"Successfully migrated {updated_count} records")
        
        # Show statistics
        show_migration_stats(db)
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        db.rollback()
    finally:
        db.close()

def show_migration_stats(db):
    """Show statistics after migration"""
    logger.info("\n=== Migration Statistics ===")
    
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
    
    # Sample comparison keys
    sample_keys = db.query(WatchListing.comparison_key).distinct().limit(10).all()
    logger.info(f"\nSample comparison keys:")
    for key in sample_keys:
        if key[0]:  # Check if key is not None
            logger.info(f"  {key[0]}")

if __name__ == "__main__":
    # Make sure database is initialized
    init_database()
    migrate_existing_data()