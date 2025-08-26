"""Test the scraper and save to database"""
from scrapers.bobs_watches import BobsWatchesScraper  # Change this import
from database.connection import SessionLocal, init_database
from database.models import WatchListing
from loguru import logger
import json
from sqlalchemy import func
from datetime import datetime

def test_scraper():
    """Test Bob's Watches scraper"""
    # Initialize database
    init_database()

    # Create scraper - using Bob's Watches instead
    scraper = BobsWatchesScraper()

    # Scrape some listings
    logger.info("Starting scrape test...")
    listings = scraper.scrape_search_results()

    # Save to database
    db = SessionLocal()
    try:
        for listing_data in listings:
            # Check if listing already exists
            existing = (
                db.query(WatchListing)
                .filter_by(source_id=listing_data.get("source_id"))
                .first()
            )

            if not existing:
                listing = WatchListing(
                    source="bobs_watches",  # Changed source
                    source_id=listing_data.get("source_id"),
                    url=listing_data.get("url"),
                    brand=listing_data.get("brand", "Rolex"),
                    model=listing_data.get("model", "Unknown"),
                    reference_number=listing_data.get("reference_number"),
                    year=listing_data.get("year"),
                    price_usd=listing_data.get("price_usd", 0),
                    has_box=listing_data.get("has_box", False),
                    has_papers=listing_data.get("has_papers", False),
                    condition=listing_data.get("condition"),
                    # Add variation tracking fields
                    dial_type=listing_data.get("dial_type"),
                    special_edition=listing_data.get("special_edition"),
                    comparison_key=listing_data.get("comparison_key"),
                    raw_data=listing_data,
                )
                db.add(listing)
                logger.info(f"Added: {listing}")
            else:
                # Update price if changed
                if existing.price_usd != listing_data.get("price_usd"):
                    logger.info(
                        f"Price change for {existing.model}: ${existing.price_usd} -> ${listing_data.get('price_usd')}"
                    )
                    existing.price_usd = listing_data.get("price_usd")

        db.commit()
        logger.success(f"Saved {len(listings)} listings to database")

        # Show summary
        total_listings = db.query(WatchListing).count()
        avg_price = db.query(func.avg(WatchListing.price_usd)).scalar()

        logger.info(f"\nDatabase Summary:")
        logger.info(f"  Total Listings: {total_listings}")
        if avg_price:
            logger.info(f"  Average Price: ${avg_price:,.0f}")
        else:
            logger.info(f"  Average Price: No data yet")

    finally:
        db.close()

    # Create data directory if it doesn't exist
    import os
    os.makedirs('data', exist_ok=True)
    
    # Save to JSON for inspection
    with open("data/sample_scrape.json", "w") as f:
        json.dump(listings[:5], f, indent=2, default=str)

    logger.success("Test complete! Check data/sample_scrape.json")


if __name__ == "__main__":
    test_scraper()