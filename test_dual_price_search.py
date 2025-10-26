#!/usr/bin/env python3
"""
Test the new dual-market price search API endpoint
Shows how wholesale and retail prices display as separate lines
"""
import requests
import json

def test_dual_price_search():
    """Test the /api/price-search-dual endpoint"""
    
    # Test different searches
    search_queries = [
        "submariner",
        "daytona", 
        "116520",
        "GMT",
        "1675"
    ]
    
    base_url = "http://localhost:8000/api/price-search-dual"
    
    print("🔍 DUAL-MARKET PRICE SEARCH TEST")
    print("=" * 60)
    
    for query in search_queries:
        print(f"\n🔎 Searching for: '{query}'")
        print("-" * 40)
        
        try:
            response = requests.get(base_url, params={'q': query, 'limit': 3})
            
            if response.status_code == 200:
                results = response.json()
                
                if not results:
                    print("   No results found")
                    continue
                
                for i, result in enumerate(results, 1):
                    print(f"\n   {i}. {result['display_name']}")
                    print(f"      Comparison Key: {result['comparison_key']}")
                    
                    # Display wholesale line
                    if result['wholesale_line']:
                        wl = result['wholesale_line']
                        price_range = ""
                        if wl.get('price_range'):
                            price_range = f" (${wl['price_range']['min']:,}-${wl['price_range']['max']:,})"
                        print(f"      📦 Wholesale: ${wl['price']:,}{price_range} • {wl['count']} listings")
                        
                        # Show dealer intelligence if available
                        if wl.get('dealer_intel'):
                            intel = wl['dealer_intel']
                            intel_parts = []
                            if intel['naked_available'] > 0:
                                intel_parts.append(f"{intel['naked_available']} naked")
                            if intel['complete_sets'] > 0:
                                intel_parts.append(f"{intel['complete_sets']} complete sets")
                            if intel['pristine_bracelets'] > 0:
                                intel_parts.append(f"{intel['pristine_bracelets']} no-stretch")
                            if intel_parts:
                                print(f"         └─ Dealer Intel: {', '.join(intel_parts)}")
                    else:
                        print(f"      📦 Wholesale: Not available")
                    
                    # Display retail line
                    if result['retail_line']:
                        rl = result['retail_line']
                        price_range = ""
                        if rl.get('price_range'):
                            price_range = f" (${rl['price_range']['min']:,}-${rl['price_range']['max']:,})"
                        print(f"      🏬 Retail:    ${rl['price']:,}{price_range} • {rl['count']} listings")
                    else:
                        print(f"      🏬 Retail:    Not available")
                    
                    # Display margin information
                    if result['margin_info']:
                        margin = result['margin_info']
                        arbitrage_flag = " 🚀" if margin['arbitrage_potential'] else ""
                        print(f"      💰 Margin:    ${margin['dollars']:,} ({margin['percent']}%){arbitrage_flag}")
                        
            else:
                print(f"   API Error: {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            print(f"   ❌ Cannot connect to API at {base_url}")
            print(f"      Make sure the FastAPI server is running:")
            print(f"      cd src && python -m uvicorn api.main:app --reload")
            break
        except Exception as e:
            print(f"   ❌ Error: {e}")

    print(f"\n🎯 API ENDPOINT DETAILS:")
    print(f"   URL: GET {base_url}")
    print(f"   Parameters: q (search query), limit (optional, default 10)")
    print(f"   Response: List of watches with separate wholesale/retail lines")
    print(f"   Features:")
    print(f"   • Two separate price lines (wholesale & retail)")
    print(f"   • Price ranges when available")
    print(f"   • Listing counts for each market")
    print(f"   • Margin calculation and arbitrage flagging")
    print(f"   • Dealer intelligence (naked, complete sets, condition)")

def show_api_response_format():
    """Show the expected JSON response format"""
    print(f"\n📋 API RESPONSE FORMAT:")
    print("-" * 30)
    
    sample_response = {
        "comparison_key": "116520-whitedial",
        "display_name": "Rolex Daytona 116520",
        "reference_number": "116520", 
        "model": "Daytona",
        "brand": "Rolex",
        "wholesale_line": {
            "price": 28000,
            "price_range": {"min": 26500, "max": 29500},
            "count": 5,
            "available": True,
            "market_type": "wholesale",
            "dealer_intel": {
                "naked_available": 2,
                "complete_sets": 1,
                "pristine_bracelets": 3
            }
        },
        "retail_line": {
            "price": 35000,
            "price_range": {"min": 33500, "max": 36500},
            "count": 12,
            "available": True,
            "market_type": "retail"
        },
        "margin_info": {
            "dollars": 7000,
            "percent": 25.0,
            "arbitrage_potential": True
        }
    }
    
    print(json.dumps(sample_response, indent=2))

if __name__ == "__main__":
    test_dual_price_search()
    show_api_response_format()