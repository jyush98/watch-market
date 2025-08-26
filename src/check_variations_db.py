"""Check variation data in database"""
from database.connection import SessionLocal
from database.models import WatchListing
from loguru import logger

def check_variation_data():
    """Check if variation data is properly stored"""
    db = SessionLocal()
    try:
        # Check for special variations
        special_watches = db.query(WatchListing).filter(
            WatchListing.special_edition != None
        ).all()
        
        logger.info(f"Found {len(special_watches)} watches with special editions:")
        for watch in special_watches:
            logger.info(f"  ID: {watch.id}")
            logger.info(f"  URL: {watch.url}")
            logger.info(f"  Special Edition: {watch.special_edition}")
            logger.info(f"  Dial Type: {watch.dial_type}")
            logger.info(f"  Comparison Key: {watch.comparison_key}")
            logger.info("")
            
        # Check Tiffany specifically
        tiffany = db.query(WatchListing).filter(
            WatchListing.comparison_key.like('%-tiffany')
        ).all()
        
        logger.info(f"Found {len(tiffany)} Tiffany watches:")
        for watch in tiffany:
            logger.info(f"  Price: ${watch.price_usd}")
            logger.info(f"  Comparison Key: {watch.comparison_key}")
            logger.info(f"  URL: {watch.url}")
            
    finally:
        db.close()

if __name__ == "__main__":
    check_variation_data()