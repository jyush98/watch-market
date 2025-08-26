"""Test the enhanced variation detection on actual URLs"""
from scrapers.bobs_watches import BobsWatchesScraper
from loguru import logger

def test_enhanced_detection():
    """Test enhanced variation detection on real URLs from the 1680 group"""
    scraper = BobsWatchesScraper()
    
    # Test cases from actual problematic 1680s
    test_cases = [
        {
            'url': 'https://www.bobswatches.com/vintage-rolex-submariner-ref-1680-yellow-gold.html',
            'reference': '1680',
            'expected': 'gold',
            'price': 26995
        },
        {
            'url': 'https://www.bobswatches.com/vintage-rolex-submariner-ref-1680-blue-dial.html',
            'reference': '1680',
            'expected': 'blue',
            'price': 29995
        },
        {
            'url': 'https://www.bobswatches.com/vintage-rolex-white-submariner-1680-stainless-steel.html',
            'reference': '1680',
            'expected': 'white',
            'price': 12495
        },
        {
            'url': 'https://www.bobswatches.com/vintage-rolex-submariner-ref-1680-red-writing.html',
            'reference': '1680',
            'expected': 'red',
            'price': 20995
        },
        {
            'url': 'https://www.bobswatches.com/vintage-rolex-submariner-ref-1680-steel-oyster.html',
            'reference': '1680',
            'expected': 'standard',
            'price': 9995
        },
        {
            'url': 'https://www.bobswatches.com/vintage-rolex-submariner-ref-1680.html',
            'reference': '1680',
            'expected': 'standard',
            'price': 12995
        }
    ]
    
    logger.info("Testing enhanced variation detection on real URLs...")
    logger.info("=" * 80)
    
    passed = 0
    total = len(test_cases)
    
    for i, test_case in enumerate(test_cases, 1):
        listing = {
            'title': '',  # Empty since we're using URL
            'url': test_case['url'],
            'reference_number': test_case['reference']
        }
        
        scraper.detect_watch_variations(listing)
        
        comparison_key = listing.get('comparison_key', '')
        detected_suffix = comparison_key.split('-')[-1] if '-' in comparison_key else 'unknown'
        
        is_correct = detected_suffix == test_case['expected']
        status = "✅ PASS" if is_correct else "❌ FAIL"
        
        if is_correct:
            passed += 1
        
        logger.info(f"Test {i}: {status}")
        logger.info(f"  URL: ...{test_case['url'][-50:]}")
        logger.info(f"  Price: ${test_case['price']:,}")
        logger.info(f"  Expected: {test_case['expected']}")
        logger.info(f"  Detected: {detected_suffix}")
        logger.info(f"  Comparison Key: {comparison_key}")
        logger.info(f"  Special Edition: {listing.get('special_edition', 'None')}")
        logger.info("")
    
    logger.info("=" * 80)
    logger.info(f"Enhanced Detection Results: {passed}/{total} tests passed")
    
    if passed == total:
        logger.success("🎉 All enhanced variation tests passed!")
    else:
        logger.warning("Some enhanced variation tests failed.")
    
    return passed == total

if __name__ == "__main__":
    test_enhanced_detection()