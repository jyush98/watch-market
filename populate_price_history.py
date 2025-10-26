"""Populate price_history table from watch_listings"""
import sys
sys.path.append('src')

from database.connection import SessionLocal
from database.models import WatchListing, PriceHistory
from datetime import datetime

def populate_price_history():
    """Create price history records from current watch listings"""
    session = SessionLocal()

    try:
        # Get all active watch listings
        listings = session.query(WatchListing).filter(
            WatchListing.is_active == True
        ).all()

        print(f"Found {len(listings)} active watch listings")

        added_count = 0
        for listing in listings:
            # Create a price history record for each listing
            history = PriceHistory(
                listing_id=listing.id,
                source_id=listing.source_id,
                comparison_key=listing.comparison_key,
                brand=listing.brand,
                model=listing.model,
                reference_number=listing.reference_number,
                price_usd=listing.price_usd,
                source=listing.source,
                url=listing.url,
                source_type=listing.source_type,
                timestamp=listing.first_seen or datetime.now()
            )
            session.add(history)
            added_count += 1

        session.commit()
        print(f"✅ Successfully added {added_count} price history records")

        # Verify the data
        total_history = session.query(PriceHistory).count()
        wholesale_history = session.query(PriceHistory).filter(
            PriceHistory.source_type == 'wholesale'
        ).count()
        retail_history = session.query(PriceHistory).filter(
            PriceHistory.source_type == 'retail'
        ).count()

        print(f"\nPrice History Summary:")
        print(f"  Total records: {total_history}")
        print(f"  Wholesale: {wholesale_history}")
        print(f"  Retail: {retail_history}")

    except Exception as e:
        session.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    populate_price_history()
