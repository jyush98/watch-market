#!/usr/bin/env python3
"""
Test WhatsApp integration with realistic export format
"""
import sys
import os
sys.path.append('src')

from whatsapp_integration import WhatsAppIntegration

def test_real_whatsapp_format():
    """Test with real WhatsApp export format"""
    
    # Real WhatsApp export format with actual timestamps and dealer names
    realistic_export = """8/27/24, 3:42 PM - Mike from Chicago: Got a clean Sub 116610LN, black dial, 2019 box and papers. Asking $13,500
8/27/24, 3:45 PM - Tony NYC: Looking for Daytona 116500LN white dial, willing to go up to 32K for the right piece
8/27/24, 4:12 PM - West Coast Dealer: Have Pepsi GMT 126710BLRO, full set 2022, asking 18,500 firm
8/27/24, 4:18 PM - Mike from Chicago: Also have vintage 1675 GMT tropical dial, incredible patina. $38K takes it
8/27/24, 5:23 PM - Premium Timepieces: Domino's OP 126000 just came in, authenticated by Bob's. $7200 or best offer
8/27/24, 5:45 PM - Tony NYC: Blue dial Sub 116619LB white gold, mint condition with stickers. Looking for 35K
8/27/24, 6:30 PM - Miami Dealer: Sea-Dweller 126600, red lettering, 2023 unworn. Price: $14,800 USD
8/27/24, 7:15 PM - West Coast Dealer: Paul Newman Daytona 6239, original dial and pushers. Serious offers only, starting at 180K"""
    
    print("🧪 Testing Real WhatsApp Export Format")
    print("="*50)
    
    integration = WhatsAppIntegration()
    
    # Process the realistic export
    processed = integration.process_whatsapp_export(realistic_export, "Premium Dealers WhatsApp")
    
    print(f"\n📊 PROCESSING RESULTS:")
    print(f"• Total messages parsed: 8")
    print(f"• Listings extracted: {len(processed)}")
    
    # Show detailed results
    for i, listing in enumerate(processed, 1):
        print(f"\n{i}. {listing['brand']} {listing['model']} {listing['reference_number']}")
        print(f"   Price: ${listing['price_usd']:,.0f}")
        print(f"   Special: {listing['special_edition'] or 'None'}")
        print(f"   Material: {listing['material'] or 'None'}")
        print(f"   Dial: {listing['dial_type'] or 'None'}")
        print(f"   Comparison Key: {listing['comparison_key']}")
        print(f"   Confidence: {listing['raw_data']['confidence']:.2f}")
    
    # Test edge cases
    print(f"\n🧪 Testing Edge Cases:")
    
    edge_cases = [
        "Just checking prices on Sub 116610",  # No price
        "$45,000 for what model?",  # Price but no model
        "GMT Batman is nice but overpriced",  # Model but no reference
        "Anyone seen 126710BLRO recently?",  # Reference but no price
        "Looking to buy not sell",  # Not a listing
        "Meeting at 3PM tomorrow",  # Random message
    ]
    
    for case in edge_cases:
        fake_export = f"8/27/24, 3:42 PM - Test Dealer: {case}"
        result = integration.process_whatsapp_export(fake_export, "Test Group")
        print(f"   '{case[:30]}...' → {len(result)} listings")

if __name__ == "__main__":
    test_real_whatsapp_format()