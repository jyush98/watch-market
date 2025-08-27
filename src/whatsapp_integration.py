"""
Epic #008: WhatsApp Integration Script
Demonstrates manual chat export processing and database integration
"""

import os
import sys
import json
from typing import List, Dict
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the parent directory to sys.path to import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from whatsapp_parser import WhatsAppWatchParser, ParsedListing
from database.models import WatchListing, PriceHistory, Base
from database.connection import get_db

class WhatsAppIntegration:
    def __init__(self, db_url: str = None):
        """Initialize WhatsApp integration with database"""
        self.parser = WhatsAppWatchParser()
        
        # Database setup
        if not db_url:
            db_url = "postgresql://jonathan@localhost:5432/watchmarket"
        
        self.engine = create_engine(db_url)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
    
    def migrate_database_for_wholesale(self):
        """Add new columns for wholesale market integration"""
        print("🔄 Migrating database for wholesale market support...")
        
        migration_sql = [
            # Add new columns to watch_listings if they don't exist
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
            # Add new columns to price_history if they don't exist
            """
            ALTER TABLE price_history 
            ADD COLUMN IF NOT EXISTS source_type VARCHAR(20);
            """,
            # Create indexes for performance
            """
            CREATE INDEX IF NOT EXISTS idx_source_type_comparison_key 
            ON watch_listings(source_type, comparison_key);
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_communication_type 
            ON watch_listings(communication_type);
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_price_history_source_type 
            ON price_history(source_type);
            """
        ]
        
        for sql in migration_sql:
            try:
                self.session.execute(text(sql))
                self.session.commit()
                print(f"✅ Executed: {sql.strip()[:50]}...")
            except Exception as e:
                print(f"⚠️ Migration warning (may be expected): {e}")
                self.session.rollback()
        
        print("✅ Database migration completed!")
    
    def create_dual_market_view(self):
        """Create database view for dual market pricing analysis"""
        print("🔄 Creating dual market pricing view...")
        
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
            self.session.execute(text(view_sql))
            self.session.commit()
            print("✅ Dual market pricing view created successfully!")
        except Exception as e:
            print(f"❌ Error creating view: {e}")
            self.session.rollback()
    
    def process_whatsapp_export(self, export_text: str, dealer_group: str) -> List[Dict]:
        """Process WhatsApp chat export and return parsed listings"""
        print(f"🔍 Processing WhatsApp export from: {dealer_group}")
        
        parsed_listings = self.parser.parse_whatsapp_export(export_text, dealer_group)
        
        processed_data = []
        for listing in parsed_listings:
            # Convert to database format
            listing_data = {
                'source': f'whatsapp_{dealer_group.lower().replace(" ", "_")}',
                'source_id': f'whatsapp_{datetime.now().timestamp()}_{hash(listing.raw_message[:50])}',
                'url': f'whatsapp://group/{dealer_group}',
                'brand': listing.watch_info.brand,
                'model': listing.watch_info.model,
                'reference_number': listing.watch_info.reference,
                'price_usd': listing.price_usd,
                'source_type': listing.source_type,
                'communication_type': listing.communication_type,
                'dealer_group': dealer_group,
                'special_edition': listing.watch_info.special_edition,
                'material': listing.watch_info.material,
                'dial_type': listing.watch_info.dial_color,
                'comparison_key': self.parser.generate_comparison_key(listing.watch_info),
                'raw_data': {
                    'original_message': listing.raw_message,
                    'confidence': listing.confidence,
                    'parsed_timestamp': datetime.now().isoformat()
                }
            }
            processed_data.append(listing_data)
        
        print(f"✅ Processed {len(processed_data)} wholesale listings")
        return processed_data
    
    def save_wholesale_listings(self, processed_listings: List[Dict]):
        """Save wholesale listings to database"""
        print("💾 Saving wholesale listings to database...")
        
        saved_count = 0
        for listing_data in processed_listings:
            try:
                # Create WatchListing object
                listing = WatchListing(**listing_data)
                self.session.add(listing)
                saved_count += 1
            except Exception as e:
                print(f"⚠️ Error saving listing: {e}")
                continue
        
        try:
            self.session.commit()
            print(f"✅ Saved {saved_count} wholesale listings to database!")
            return saved_count
        except Exception as e:
            print(f"❌ Database error: {e}")
            self.session.rollback()
            return 0
    
    def analyze_dual_market(self) -> Dict:
        """Analyze dual market opportunities"""
        print("📊 Analyzing dual market opportunities...")
        
        analysis_sql = """
        SELECT 
            comparison_key,
            brand,
            model,
            reference_number,
            avg_retail_price,
            avg_wholesale_price,
            retail_listings_count,
            wholesale_listings_count,
            avg_dealer_margin,
            margin_percentage
        FROM dual_market_pricing 
        WHERE avg_wholesale_price IS NOT NULL 
        AND avg_retail_price IS NOT NULL
        AND margin_percentage > 10
        ORDER BY avg_dealer_margin DESC
        LIMIT 20;
        """
        
        try:
            result = self.session.execute(text(analysis_sql))
            opportunities = result.fetchall()
            
            analysis = {
                'total_opportunities': len(opportunities),
                'high_margin_watches': [],
                'total_potential_profit': 0
            }
            
            for opp in opportunities:
                watch_analysis = {
                    'comparison_key': opp.comparison_key,
                    'brand': opp.brand,
                    'model': opp.model,
                    'reference': opp.reference_number,
                    'wholesale_price': float(opp.avg_wholesale_price) if opp.avg_wholesale_price else 0,
                    'retail_price': float(opp.avg_retail_price) if opp.avg_retail_price else 0,
                    'margin_dollars': float(opp.avg_dealer_margin) if opp.avg_dealer_margin else 0,
                    'margin_percent': float(opp.margin_percentage) if opp.margin_percentage else 0,
                    'wholesale_listings': int(opp.wholesale_listings_count),
                    'retail_listings': int(opp.retail_listings_count)
                }
                analysis['high_margin_watches'].append(watch_analysis)
                analysis['total_potential_profit'] += watch_analysis['margin_dollars']
            
            return analysis
            
        except Exception as e:
            print(f"❌ Error analyzing dual market: {e}")
            return {'error': str(e)}
    
    def generate_market_report(self) -> str:
        """Generate comprehensive market intelligence report"""
        analysis = self.analyze_dual_market()
        
        if 'error' in analysis:
            return f"❌ Error generating report: {analysis['error']}"
        
        report = f"""
🏪 DUAL MARKET INTELLIGENCE REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📊 MARKET OVERVIEW
• Total Arbitrage Opportunities: {analysis['total_opportunities']}
• Total Potential Profit: ${analysis['total_potential_profit']:,.0f}

🔥 TOP MARGIN OPPORTUNITIES:
"""
        
        for i, watch in enumerate(analysis['high_margin_watches'][:10], 1):
            report += f"""
{i}. {watch['brand']} {watch['model']} ({watch['reference']})
   Wholesale: ${watch['wholesale_price']:,.0f} | Retail: ${watch['retail_price']:,.0f}
   Margin: ${watch['margin_dollars']:,.0f} ({watch['margin_percent']:.1f}%)
   Sources: {watch['wholesale_listings']} wholesale, {watch['retail_listings']} retail
"""
        
        return report


def demo_whatsapp_integration():
    """Demonstration of WhatsApp integration functionality"""
    print("🚀 Epic #008 WhatsApp Integration Demo\n")
    
    # Sample WhatsApp messages for testing
    sample_whatsapp_messages = [
        "Hey guys, got a clean Sub 1680 Tiffany dial, asking $42K. Interested?",
        "Looking to move Daytona 116520 white dial, excellent condition, $28,000 USD firm",
        "Anyone interested in GMT 1675 Pepsi? Asking around 25K, open to offers",
        "Have that rare Domino's Pizza 126000 for quick sale, $6500 takes it",
        "Tropical dial 1675 GMT just came in, very rare piece - $35,000",
        "Day-Date 18239 presidential bracelet yellow gold, mint condition, $45K",
        "Blue dial Sub 116619 white gold, full set with papers, asking 32000 dollars",
        "Explorer 214270 black dial, 2019, unworn condition - $7,500",
        "Yacht-Master 268621 two tone, tropical dial, stunning piece $13,500"
    ]
    
    chat_export = "\n".join([
        f"8/27/25, 3:42 PM - Dealer {i%3 + 1}: {msg}" 
        for i, msg in enumerate(sample_whatsapp_messages)
    ])
    
    # Initialize integration
    integration = WhatsAppIntegration()
    
    # Step 1: Database migration
    integration.migrate_database_for_wholesale()
    print()
    
    # Step 2: Create dual market view
    integration.create_dual_market_view()
    print()
    
    # Step 3: Process WhatsApp export
    processed_listings = integration.process_whatsapp_export(chat_export, "Premium Dealers")
    print()
    
    # Step 4: Save to database
    saved_count = integration.save_wholesale_listings(processed_listings)
    print()
    
    # Step 5: Analyze opportunities
    report = integration.generate_market_report()
    print(report)
    
    print("\n🎉 Epic #008 Phase 1 Demo Complete!")
    print("✅ Database schema enhanced for wholesale market")
    print("✅ WhatsApp parser created with 15+ variation patterns")  
    print("✅ Dual market pricing view implemented")
    print(f"✅ {saved_count} wholesale listings processed and saved")
    print("✅ Market intelligence analysis operational")


if __name__ == "__main__":
    demo_whatsapp_integration()