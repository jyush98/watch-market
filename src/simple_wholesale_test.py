"""
Simple test to add wholesale data directly to test Epic #008 dual market functionality
"""

import sys
import os
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.models import WatchListing, PriceHistory

def add_sample_wholesale_data():
    """Add sample wholesale data directly to database"""
    
    # Database connection
    db_url = "postgresql://jonathan@localhost:5432/watch_platform"
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    print("🔄 Adding wholesale market columns to database...")
    
    # Add columns if they don't exist
    migration_sql = [
        """
        ALTER TABLE watch_listings 
        ADD COLUMN IF NOT EXISTS source_type VARCHAR(20) NOT NULL DEFAULT 'retail';
        """,
        """
        ALTER TABLE watch_listings 
        ADD COLUMN IF NOT EXISTS communication_type VARCHAR(50);
        """,
        """
        ALTER TABLE watch_listings 
        ADD COLUMN IF NOT EXISTS dealer_group VARCHAR(100);
        """,
        """
        ALTER TABLE price_history 
        ADD COLUMN IF NOT EXISTS source_type VARCHAR(20);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_source_type_comparison_key 
        ON watch_listings(source_type, comparison_key);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_price_history_source_type 
        ON price_history(source_type);
        """
    ]
    
    for sql in migration_sql:
        try:
            session.execute(text(sql))
            session.commit()
        except Exception as e:
            print(f"⚠️ Migration note: {e}")
            session.rollback()
    
    print("✅ Database migration completed!")
    
    # Sample wholesale data
    wholesale_watches = [
        {
            'source': 'whatsapp_premium_dealers',
            'source_id': 'whatsapp_1680_tiffany_001',
            'url': 'whatsapp://group/premium_dealers',
            'brand': 'Rolex',
            'model': 'Submariner',
            'reference_number': '1680',
            'price_usd': 32000.0,
            'source_type': 'wholesale',
            'communication_type': 'whatsapp_group',
            'dealer_group': 'Premium Dealers',
            'special_edition': 'Tiffany & Co',
            'dial_type': 'Tiffany',
            'comparison_key': '1680-tiffany',
            'is_active': True
        },
        {
            'source': 'whatsapp_premium_dealers',
            'source_id': 'whatsapp_1675_pepsi_001',
            'url': 'whatsapp://group/premium_dealers',
            'brand': 'Rolex',
            'model': 'GMT-Master',
            'reference_number': '1675',
            'price_usd': 18500.0,
            'source_type': 'wholesale',
            'communication_type': 'whatsapp_group',
            'dealer_group': 'Premium Dealers',
            'special_edition': 'Pepsi',
            'dial_type': 'Blue/Red',
            'comparison_key': '1675-pepsi',
            'is_active': True
        },
        {
            'source': 'whatsapp_premium_dealers',
            'source_id': 'whatsapp_18239_gold_001',
            'url': 'whatsapp://group/premium_dealers',
            'brand': 'Rolex',
            'model': 'Day-Date',
            'reference_number': '18239',
            'price_usd': 35000.0,
            'source_type': 'wholesale',
            'communication_type': 'whatsapp_group',
            'dealer_group': 'Premium Dealers',
            'material': 'Yellow Gold',
            'comparison_key': '18239-gold',
            'is_active': True
        },
        {
            'source': 'whatsapp_premium_dealers', 
            'source_id': 'whatsapp_116520_white_001',
            'url': 'whatsapp://group/premium_dealers',
            'brand': 'Rolex',
            'model': 'Daytona',
            'reference_number': '116520',
            'price_usd': 22000.0,
            'source_type': 'wholesale',
            'communication_type': 'whatsapp_group',
            'dealer_group': 'Premium Dealers',
            'dial_type': 'White',
            'comparison_key': '116520-whitedial',
            'is_active': True
        },
        {
            'source': 'whatsapp_premium_dealers',
            'source_id': 'whatsapp_126000_dominos_001', 
            'url': 'whatsapp://group/premium_dealers',
            'brand': 'Rolex',
            'model': 'Oyster Perpetual',
            'reference_number': '126000',
            'price_usd': 5200.0,
            'source_type': 'wholesale',
            'communication_type': 'whatsapp_group',
            'dealer_group': 'Premium Dealers',
            'special_edition': "Domino's",
            'comparison_key': '126000-dominos',
            'is_active': True
        }
    ]
    
    print("💾 Adding wholesale watch listings...")
    
    # Add wholesale listings
    saved_count = 0
    for watch_data in wholesale_watches:
        try:
            # Check if already exists
            existing = session.query(WatchListing).filter_by(source_id=watch_data['source_id']).first()
            if existing:
                print(f"   ⚠️ {watch_data['comparison_key']} already exists, skipping")
                continue
                
            watch = WatchListing(**watch_data)
            session.add(watch)
            saved_count += 1
            print(f"   ✅ Added {watch_data['brand']} {watch_data['model']} ({watch_data['comparison_key']}) - ${watch_data['price_usd']:,.0f}")
        except Exception as e:
            print(f"   ❌ Error adding {watch_data.get('comparison_key', 'unknown')}: {e}")
    
    # Add corresponding price history entries
    print("📊 Adding wholesale price history...")
    
    history_count = 0
    for watch_data in wholesale_watches:
        try:
            # Create price history entry
            history_data = {
                'comparison_key': watch_data['comparison_key'],
                'brand': watch_data['brand'],
                'model': watch_data['model'],
                'reference_number': watch_data['reference_number'],
                'price_usd': watch_data['price_usd'],
                'source_type': 'wholesale',
                'source': watch_data['source'],
                'url': watch_data['url'],
                'timestamp': datetime.now() - timedelta(days=1)
            }
            
            history = PriceHistory(**history_data)
            session.add(history)
            history_count += 1
        except Exception as e:
            print(f"   ❌ Error adding price history for {watch_data.get('comparison_key')}: {e}")
    
    # Commit all changes
    try:
        session.commit()
        print(f"\n✅ Successfully saved:")
        print(f"   • {saved_count} wholesale listings")
        print(f"   • {history_count} price history records")
    except Exception as e:
        print(f"❌ Error saving to database: {e}")
        session.rollback()
        return
    
    # Create dual market view
    print("\n🔄 Creating dual market pricing view...")
    
    view_sql = """
    DROP VIEW IF EXISTS dual_market_pricing;
    
    CREATE VIEW dual_market_pricing AS
    SELECT 
        comparison_key,
        brand,
        model,
        reference_number,
        AVG(CASE WHEN source_type = 'retail' THEN price_usd END) as avg_retail_price,
        AVG(CASE WHEN source_type = 'wholesale' THEN price_usd END) as avg_wholesale_price,
        COUNT(CASE WHEN source_type = 'retail' THEN 1 END) as retail_listings_count,
        COUNT(CASE WHEN source_type = 'wholesale' THEN 1 END) as wholesale_listings_count,
        -- Calculate margin insights
        (AVG(CASE WHEN source_type = 'retail' THEN price_usd END) - 
         AVG(CASE WHEN source_type = 'wholesale' THEN price_usd END)) as avg_dealer_margin,
        ((AVG(CASE WHEN source_type = 'retail' THEN price_usd END) - 
          AVG(CASE WHEN source_type = 'wholesale' THEN price_usd END)) / 
          NULLIF(AVG(CASE WHEN source_type = 'wholesale' THEN price_usd END), 0) * 100) as margin_percentage
    FROM watch_listings 
    WHERE comparison_key IS NOT NULL AND is_active = true
    GROUP BY comparison_key, brand, model, reference_number;
    """
    
    try:
        session.execute(text(view_sql))
        session.commit()
        print("✅ Dual market pricing view created successfully!")
    except Exception as e:
        print(f"❌ Error creating view: {e}")
        session.rollback()
    
    # Query for margin opportunities
    print("\n📈 DUAL MARKET ANALYSIS")
    print("=" * 50)
    
    opportunities_sql = """
    SELECT 
        comparison_key,
        brand,
        model,
        reference_number,
        avg_retail_price,
        avg_wholesale_price,
        avg_dealer_margin,
        margin_percentage,
        retail_listings_count,
        wholesale_listings_count
    FROM dual_market_pricing 
    WHERE avg_wholesale_price IS NOT NULL 
    AND avg_retail_price IS NOT NULL
    ORDER BY avg_dealer_margin DESC;
    """
    
    try:
        result = session.execute(text(opportunities_sql))
        opportunities = result.fetchall()
        
        if opportunities:
            total_profit = 0
            for opp in opportunities:
                margin_dollars = float(opp.avg_dealer_margin) if opp.avg_dealer_margin else 0
                margin_percent = float(opp.margin_percentage) if opp.margin_percentage else 0
                wholesale_price = float(opp.avg_wholesale_price) if opp.avg_wholesale_price else 0
                retail_price = float(opp.avg_retail_price) if opp.avg_retail_price else 0
                
                print(f"🎯 {opp.brand} {opp.model} ({opp.comparison_key})")
                print(f"   Wholesale: ${wholesale_price:,.0f} | Retail: ${retail_price:,.0f}")
                print(f"   Margin: ${margin_dollars:,.0f} ({margin_percent:.1f}%)")
                print(f"   Sources: {opp.wholesale_listings_count} wholesale, {opp.retail_listings_count} retail")
                print()
                
                total_profit += margin_dollars
            
            print(f"💰 TOTAL POTENTIAL PROFIT: ${total_profit:,.0f}")
        else:
            print("No dual market opportunities found yet.")
            
    except Exception as e:
        print(f"❌ Error analyzing opportunities: {e}")
    
    session.close()
    
    print("\n🎯 Epic #008 Test Complete!")
    print("✅ Wholesale market integration ready for testing")
    print("\n📋 Next Steps:")
    print("1. Start API server: uvicorn api.main:app --reload --port 8000")
    print("2. Open dashboard.html in browser")
    print("3. Click '🏪 Wholesale Market' tab")
    print("4. View margin opportunities and search dual-market pricing")

if __name__ == "__main__":
    add_sample_wholesale_data()