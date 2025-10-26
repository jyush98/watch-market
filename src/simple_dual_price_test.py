#!/usr/bin/env python3
"""
Simple dual-market price display using basic endpoint
"""
import requests
import json
from typing import Dict, List

def create_dual_price_display(watches: List[Dict]) -> None:
    """Create dual-market price display from basic watch data"""
    
    print("🔍 DUAL-MARKET PRICE SEARCH RESULTS")
    print("=" * 50)
    
    if not watches:
        print("No results found.")
        return
    
    # Group by comparison_key and calculate dual-market pricing
    grouped_watches = {}
    
    for watch in watches:
        key = watch.get('comparison_key', f"{watch['reference_number']}-standard")
        if key not in grouped_watches:
            grouped_watches[key] = {
                'display_name': f"{watch['brand']} {watch['model']} {watch.get('reference_number', '')}",
                'wholesale_listings': [],
                'retail_listings': []
            }
        
        # Group by source type
        source_type = watch.get('source_type', 'retail')  # Default to retail if not specified
        if source_type == 'wholesale':
            grouped_watches[key]['wholesale_listings'].append(watch)
        else:
            grouped_watches[key]['retail_listings'].append(watch)
    
    # Display results with separate lines
    for key, data in list(grouped_watches.items())[:5]:  # Show top 5
        print(f"\n🔹 {data['display_name']}")
        print(f"   Key: {key}")
        
        # Wholesale line
        if data['wholesale_listings']:
            prices = [w['price_usd'] for w in data['wholesale_listings']]
            avg_price = sum(prices) / len(prices)
            min_price = min(prices)
            max_price = max(prices)
            
            if min_price == max_price:
                print(f"   📦 Wholesale: ${avg_price:,.0f} • {len(prices)} listings")
            else:
                print(f"   📦 Wholesale: ${avg_price:,.0f} (${min_price:,.0f}-${max_price:,.0f}) • {len(prices)} listings")
        else:
            print(f"   📦 Wholesale: Not available")
        
        # Retail line  
        if data['retail_listings']:
            prices = [w['price_usd'] for w in data['retail_listings']]
            avg_price = sum(prices) / len(prices)
            min_price = min(prices)
            max_price = max(prices)
            
            if min_price == max_price:
                print(f"   🏬 Retail:    ${avg_price:,.0f} • {len(prices)} listings")
            else:
                print(f"   🏬 Retail:    ${avg_price:,.0f} (${min_price:,.0f}-${max_price:,.0f}) • {len(prices)} listings")
        else:
            print(f"   🏬 Retail:    Not available")
        
        # Margin calculation
        if data['wholesale_listings'] and data['retail_listings']:
            wholesale_avg = sum(w['price_usd'] for w in data['wholesale_listings']) / len(data['wholesale_listings'])
            retail_avg = sum(w['price_usd'] for w in data['retail_listings']) / len(data['retail_listings'])
            margin = retail_avg - wholesale_avg
            margin_percent = (margin / wholesale_avg) * 100
            arbitrage_flag = " 🚀" if margin > 1000 else ""
            print(f"   💰 Margin:    ${margin:,.0f} ({margin_percent:.1f}%){arbitrage_flag}")

def test_basic_dual_search():
    """Test using basic watch endpoint and create dual display"""
    
    # Test different basic endpoints
    endpoints_to_try = [
        "http://localhost:8000/api/watches?limit=20",
        "http://localhost:8000/api/dual-market-search?q=rolex&limit=10"
    ]
    
    for endpoint in endpoints_to_try:
        print(f"\n🌐 Testing endpoint: {endpoint}")
        print("-" * 40)
        
        try:
            response = requests.get(endpoint, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and data:
                    create_dual_price_display(data)
                    return  # Success, exit
                else:
                    print(f"   No data returned or wrong format")
            else:
                print(f"   HTTP {response.status_code}: {response.text}")
                
        except requests.exceptions.ConnectionError:
            print(f"   ❌ Cannot connect - API server not running")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print(f"\n💡 API Server Start Command:")
    print(f"   cd src && python3 -m uvicorn api.main:app --reload --port 8000")

if __name__ == "__main__":
    test_basic_dual_search()