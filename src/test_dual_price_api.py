#!/usr/bin/env python3
"""
Test dual-market price search directly with database
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

def test_dual_market_query():
    """Test the dual-market SQL query directly"""
    
    # Connect to database
    db_url = "sqlite:///watchmarket.db"  # One level up from src
    engine = create_engine(f"sqlite:///../watchmarket.db")
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    print("🔍 TESTING DUAL-MARKET PRICE SEARCH QUERY")
    print("=" * 50)
    
    # Test the SQL query directly
    sql = text("""
        SELECT 
            w.comparison_key,
            w.brand,
            w.model,
            w.reference_number,
            w.special_edition,
            
            -- Wholesale data
            AVG(CASE WHEN w.source_type = 'wholesale' THEN w.price_usd END) as avg_wholesale_price,
            MIN(CASE WHEN w.source_type = 'wholesale' THEN w.price_usd END) as min_wholesale_price,
            MAX(CASE WHEN w.source_type = 'wholesale' THEN w.price_usd END) as max_wholesale_price,
            COUNT(CASE WHEN w.source_type = 'wholesale' THEN 1 END) as wholesale_count,
            
            -- Retail data
            AVG(CASE WHEN w.source_type = 'retail' THEN w.price_usd END) as avg_retail_price,
            MIN(CASE WHEN w.source_type = 'retail' THEN w.price_usd END) as min_retail_price,
            MAX(CASE WHEN w.source_type = 'retail' THEN w.price_usd END) as max_retail_price,
            COUNT(CASE WHEN w.source_type = 'retail' THEN 1 END) as retail_count
            
        FROM watch_listings w
        WHERE w.comparison_key IS NOT NULL 
        AND w.is_active = true
        AND (w.comparison_key ILIKE :search_term 
             OR w.brand ILIKE :search_term 
             OR w.model ILIKE :search_term 
             OR w.reference_number ILIKE :search_term)
        GROUP BY w.comparison_key, w.brand, w.model, w.reference_number, w.special_edition
        HAVING COUNT(w.id) > 0
        ORDER BY COUNT(w.id) DESC
        LIMIT 5
    """)
    
    # Test different searches
    search_terms = ['daytona', 'submariner', '116520', '1675']
    
    for term in search_terms:
        print(f"\n🔎 Searching for: '{term}'")
        print("-" * 30)
        
        try:
            result = db.execute(sql, {'search_term': f'%{term}%'})
            rows = result.fetchall()
            
            if not rows:
                print("   No results found")
                continue
                
            for row in rows:
                display_parts = [row.brand, row.model]
                if row.reference_number:
                    display_parts.append(row.reference_number)
                if row.special_edition:
                    display_parts.append(f"({row.special_edition})")
                display_name = " ".join(display_parts)
                
                print(f"   📍 {display_name}")
                print(f"       Key: {row.comparison_key}")
                
                # Wholesale line
                if row.avg_wholesale_price and row.wholesale_count > 0:
                    print(f"       📦 Wholesale: ${row.avg_wholesale_price:,.0f} • {row.wholesale_count} listings")
                    if row.min_wholesale_price != row.max_wholesale_price:
                        print(f"                   Range: ${row.min_wholesale_price:,.0f} - ${row.max_wholesale_price:,.0f}")
                else:
                    print(f"       📦 Wholesale: Not available")
                
                # Retail line
                if row.avg_retail_price and row.retail_count > 0:
                    print(f"       🏬 Retail:    ${row.avg_retail_price:,.0f} • {row.retail_count} listings")
                    if row.min_retail_price != row.max_retail_price:
                        print(f"                   Range: ${row.min_retail_price:,.0f} - ${row.max_retail_price:,.0f}")
                else:
                    print(f"       🏬 Retail:    Not available")
                
                # Margin calculation
                if row.avg_retail_price and row.avg_wholesale_price:
                    margin = row.avg_retail_price - row.avg_wholesale_price
                    margin_percent = (margin / row.avg_wholesale_price) * 100
                    print(f"       💰 Margin:    ${margin:,.0f} ({margin_percent:.1f}%)")
                
                print()
                
        except Exception as e:
            print(f"   ❌ Query error: {e}")
    
    # Show database summary
    print(f"\n📊 DATABASE SUMMARY:")
    print("-" * 20)
    
    try:
        total_listings = db.execute(text("SELECT COUNT(*) FROM watch_listings WHERE is_active = true")).scalar()
        wholesale_count = db.execute(text("SELECT COUNT(*) FROM watch_listings WHERE is_active = true AND source_type = 'wholesale'")).scalar()
        retail_count = db.execute(text("SELECT COUNT(*) FROM watch_listings WHERE is_active = true AND source_type = 'retail'")).scalar()
        
        print(f"   Total active listings: {total_listings}")
        print(f"   Wholesale listings: {wholesale_count}")
        print(f"   Retail listings: {retail_count}")
        
        # Check for dual-market opportunities
        dual_market = db.execute(text("""
            SELECT COUNT(DISTINCT comparison_key) 
            FROM watch_listings w1 
            WHERE EXISTS (
                SELECT 1 FROM watch_listings w2 
                WHERE w2.comparison_key = w1.comparison_key 
                AND w2.source_type != w1.source_type
                AND w2.is_active = true
            ) AND w1.is_active = true
        """)).scalar()
        
        print(f"   Dual-market watches: {dual_market}")
        
    except Exception as e:
        print(f"   ❌ Summary error: {e}")
    
    db.close()

if __name__ == "__main__":
    test_dual_market_query()