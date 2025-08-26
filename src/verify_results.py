#!/usr/bin/env python3
"""Quick verification of automated scraper results"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.connection import SessionLocal
from sqlalchemy import func, text
from database.models import WatchListing, PriceHistory

def main():
    db = SessionLocal()
    
    # Check database stats
    total_listings = db.query(func.count(WatchListing.id)).scalar()
    total_history = db.query(func.count(PriceHistory.id)).scalar()
    
    print("Database Status:")
    print(f"• Total listings: {total_listings}")
    print(f"• Price history records: {total_history}")
    
    # Check arbitrage opportunities  
    query = text("""
        SELECT 
            comparison_key,
            brand,
            model,
            COUNT(*) as listings_count,
            MIN(price_usd) as min_price,
            MAX(price_usd) as max_price,
            MAX(price_usd) - MIN(price_usd) as profit_potential
        FROM watch_listings 
        WHERE comparison_key IS NOT NULL 
        GROUP BY comparison_key, brand, model
        HAVING COUNT(*) >= 2 
        AND (MAX(price_usd) - MIN(price_usd)) >= 1000
        ORDER BY profit_potential DESC
        LIMIT 5
    """)
    
    arbitrage = db.execute(query).fetchall()
    print(f"\nTop Arbitrage Opportunities:")
    for row in arbitrage:
        print(f"• {row.brand} {row.model} ({row.comparison_key}): Buy ${row.min_price:,.0f}, Sell ${row.max_price:,.0f} = ${row.profit_potential:,.0f} profit ({row.listings_count} listings)")
    
    # Check variations detected
    variations_query = text("""
        SELECT special_edition, COUNT(*) as count
        FROM watch_listings 
        WHERE special_edition IS NOT NULL
        GROUP BY special_edition
        ORDER BY count DESC
        LIMIT 10
    """)
    
    variations = db.execute(variations_query).fetchall()
    print(f"\nSpecial Edition Variations Detected:")
    for row in variations:
        print(f"• {row.special_edition}: {row.count} listings")
    
    db.close()

if __name__ == "__main__":
    main()