"""Test the enhanced variation detection on 16613 models"""
from scrapers.bobs_watches import BobsWatchesScraper
from loguru import logger

def test_16613_detection():
    """Test enhanced variation detection on 16613 models"""
    scraper = BobsWatchesScraper()
    
    # Test cases from actual 16613s
    test_cases = [
        {
            'url': 'https://www.bobswatches.com/rolex-submariner-16613-black-bezel.html',
            'reference': '16613',
            'expected': 'blackbezel',
            'price': 10795,
            'description': 'Black bezel two-tone'
        },
        {
            'url': 'https://www.bobswatches.com/rolex-submariner-16613-slate-serti.html',
            'reference': '16613',
            'expected': 'serti',
            'price': 14995,
            'description': 'Slate serti dial'
        }
    ]
    
    logger.info("Testing 16613 variation detection...")
    logger.info("=" * 60)
    
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
        logger.info(f"  Description: {test_case['description']}")
        logger.info(f"  Price: ${test_case['price']:,}")
        logger.info(f"  Expected: {test_case['expected']}")
        logger.info(f"  Detected: {detected_suffix}")
        logger.info(f"  Comparison Key: {comparison_key}")
        logger.info(f"  Special Edition: {listing.get('special_edition', 'None')}")
        logger.info("")
    
    logger.info("=" * 60)
    logger.info(f"16613 Detection Results: {passed}/{total} tests passed")
    
    if passed == total:
        logger.success("🎉 All 16613 variation tests passed!")
    else:
        logger.warning("Some 16613 variation tests failed.")
    
    return passed == total

if __name__ == "__main__":
    test_16613_detection()