"""Debug scraper to see what we're getting"""
import requests
from bs4 import BeautifulSoup
import json

url = "https://www.bobswatches.com/rolex-submariner-1.html"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

response = requests.get(url, headers=headers)
print(f"Status: {response.status_code}")

if response.status_code == 200:
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Look for any JSON-LD structured data
    scripts = soup.find_all('script', type='application/ld+json')
    print(f"\nFound {len(scripts)} JSON-LD scripts")
    
    # Parse each JSON-LD script to find product data
    products = []
    for i, script in enumerate(scripts):
        try:
            data = json.loads(script.string)
            
            # Check if it's a product
            if isinstance(data, dict):
                if data.get('@type') == 'Product':
                    products.append(data)
                    print(f"\nScript {i}: Found Product!")
                    print(f"  Name: {data.get('name', 'N/A')}")
                    if 'offers' in data:
                        print(f"  Price: ${data['offers'].get('price', 'N/A')}")
                elif '@graph' in data:
                    # Check items in graph
                    for item in data['@graph']:
                        if isinstance(item, dict) and item.get('@type') == 'Product':
                            products.append(item)
                            print(f"\nScript {i}: Found Product in @graph!")
                            print(f"  Name: {item.get('name', 'N/A')}")
                            if 'offers' in item:
                                print(f"  Price: ${item['offers'].get('price', 'N/A')}")
        except json.JSONDecodeError:
            pass
    
    print(f"\nTotal products found: {len(products)}")
    
    # Show first product details
    if products:
        print(f"\nFirst product full data:")
        print(json.dumps(products[0], indent=2)[:500])  # First 500 chars