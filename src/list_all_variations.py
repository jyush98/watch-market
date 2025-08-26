"""List all detected variations"""
from database.connection import SessionLocal
from database.models import WatchListing
from loguru import logger

def list_all_variations():
    """List all detected variations"""
    db = SessionLocal()
    try:
        # Get all special variations
        variations = db.query(
            WatchListing.comparison_key, 
            WatchListing.special_edition,
            WatchListing.price_usd,
            WatchListing.url
        ).filter(
            WatchListing.special_edition != None
        ).order_by(WatchListing.comparison_key).all()
        
        logger.info("🎯 All Special Variations Detected:")
        logger.info("=" * 70)
        
        current_key = None
        for var in variations:
            if var.comparison_key != current_key:
                current_key = var.comparison_key
                logger.info(f"\n{var.comparison_key}:")
            logger.info(f"  ${var.price_usd:,.0f} - {var.special_edition}")
            logger.info(f"  URL: {var.url}")
        
        # Get count by type
        type_counts = {}
        for var in variations:
            suffix = var.comparison_key.split('-')[-1]
            type_counts[suffix] = type_counts.get(suffix, 0) + 1
        
        logger.info("\n" + "=" * 70)
        logger.info("📊 Summary by Variation Type:")
        for var_type, count in sorted(type_counts.items()):
            logger.info(f"  {var_type}: {count} watches")
            
        logger.info(f"\n🎉 Total special variations: {len(variations)}")
        logger.info(f"🎉 Total variation types: {len(type_counts)}")
        
        # Standard watches count
        standard_count = db.query(WatchListing).filter(
            WatchListing.comparison_key.like('%-standard')
        ).count()
        logger.info(f"🎉 Standard watches: {standard_count}")
        
    finally:
        db.close()

if __name__ == "__main__":
    list_all_variations()