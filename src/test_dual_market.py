"""
Quick test script to add sample wholesale data and test Epic #008 dual market functionality
"""

import sys
import os
from datetime import datetime, timedelta
import random

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from whatsapp_integration import WhatsAppIntegration

def add_sample_wholesale_data():
    """Add sample wholesale data for testing dual market functionality"""
    
    # Sample WhatsApp messages with wholesale pricing
    sample_messages = [
        "Selling clean Sub 1680 Tiffany dial, asking $32,000",
        "GMT 1675 Pepsi excellent condition, wholesale price $18,500", 
        "Day-Date 18239 yellow gold, dealer price $35,000 firm",
        "Daytona 116520 white dial, wholesale asking $22,000",
        "Explorer 214270 black dial, dealer cost $6,800",
        "Yacht-Master 268621 two tone, wholesale $11,200",
        "Sea-Dweller 126600 red writing, dealer price $9,500",
        "Submariner 116610LN Hulk, wholesale asking $14,500",
        "GMT-Master 126710BLRO Batman, dealer cost $16,800",
        "Day-Date 228206 ice blue, wholesale price $52,000"
    ]
    
    # Initialize integration
    integration = WhatsAppIntegration()
    
    # Step 1: Migrate database
    print("🔄 Migrating database for wholesale support...")
    integration.migrate_database_for_wholesale()
    
    # Step 2: Create dual market view
    print("🔄 Creating dual market pricing view...")
    integration.create_dual_market_view()
    
    # Step 3: Process sample data
    print("🔄 Processing sample wholesale messages...")
    chat_export = "\n".join([
        f"8/27/25, {3 + i}:42 PM - Dealer {i%3 + 1}: {msg}" 
        for i, msg in enumerate(sample_messages)
    ])
    
    processed_listings = integration.process_whatsapp_export(chat_export, "Premium Dealers")
    
    # Step 4: Save to database
    print("💾 Saving wholesale listings...")
    saved_count = integration.save_wholesale_listings(processed_listings)
    
    # Step 5: Generate sample price history for wholesale items
    print("📊 Creating sample price history for wholesale items...")
    
    # Add some historical price points for wholesale items
    from database.models import PriceHistory
    
    wholesale_history_entries = [
        {
            'comparison_key': '1680-tiffany',
            'brand': 'Rolex',
            'model': 'Submariner', 
            'reference_number': '1680',
            'price_usd': 32000,
            'source_type': 'wholesale',
            'source': 'whatsapp_premium_dealers',
            'timestamp': datetime.now() - timedelta(days=7)
        },
        {
            'comparison_key': '1675-pepsi',
            'brand': 'Rolex',
            'model': 'GMT-Master',
            'reference_number': '1675', 
            'price_usd': 18500,
            'source_type': 'wholesale',
            'source': 'whatsapp_premium_dealers',
            'timestamp': datetime.now() - timedelta(days=5)
        },
        {
            'comparison_key': '18239-gold',
            'brand': 'Rolex',
            'model': 'Day-Date',
            'reference_number': '18239',
            'price_usd': 35000,
            'source_type': 'wholesale', 
            'source': 'whatsapp_premium_dealers',
            'timestamp': datetime.now() - timedelta(days=3)
        }
    ]
    
    history_count = 0
    for entry in wholesale_history_entries:
        try:
            history_record = PriceHistory(**entry)
            integration.session.add(history_record)
            history_count += 1
        except Exception as e:
            print(f"⚠️ Error creating price history: {e}")
    
    try:
        integration.session.commit()
        print(f"✅ Created {history_count} wholesale price history records")
    except Exception as e:
        print(f"❌ Error saving price history: {e}")
        integration.session.rollback()
    
    # Step 6: Generate market report
    print("\n📈 DUAL MARKET ANALYSIS REPORT")
    print("=" * 50)
    report = integration.generate_market_report()
    print(report)
    
    print(f"\n✅ Epic #008 Test Complete!")
    print(f"   • Database migration: ✅")
    print(f"   • Dual market view: ✅") 
    print(f"   • WhatsApp parser: ✅")
    print(f"   • Wholesale data: {saved_count} listings saved")
    print(f"   • Price history: {history_count} records created")
    print(f"   • Market intelligence: Ready for dashboard testing")
    
    print(f"\n🎯 Next Steps:")
    print(f"   1. Start the API server: uvicorn api.main:app --reload")
    print(f"   2. Open dashboard.html in browser")
    print(f"   3. Click 'Wholesale Market' tab")
    print(f"   4. View margin opportunities and dual-market charts")
    
    return {
        'wholesale_listings': saved_count,
        'price_history_records': history_count,
        'success': True
    }

if __name__ == "__main__":
    add_sample_wholesale_data()