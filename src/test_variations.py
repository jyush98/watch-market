"""Test script to verify watch variation detection"""
from scrapers.bobs_watches import BobsWatchesScraper
from loguru import logger

def test_variation_detection():
    """Test the variation detection with sample titles"""
    scraper = BobsWatchesScraper()
    
    # Test cases with different watch variations
    test_cases = [
        {
            'title': 'Rolex Submariner 1680 Tiffany & Co. Dial',
            'reference_number': '1680',
            'expected_variation': 'tiffany'
        },
        {
            'title': 'Rolex Submariner 1680 Standard Black Dial',
            'reference_number': '1680', 
            'expected_variation': 'standard'
        },
        {
            'title': 'Rolex GMT-Master 1675 Pepsi COMEX Dial',
            'reference_number': '1675',
            'expected_variation': 'comex'
        },
        {
            'title': 'Rolex Daytona 6265 Tropical Brown Dial',
            'reference_number': '6265',
            'expected_variation': 'tropical'
        },
        {
            'title': 'Rolex Submariner 16610LV Kermit Green Bezel',
            'reference_number': '16610LV',
            'expected_variation': 'kermit'
        },
        {
            'title': 'Rolex GMT-Master II 116710BLNR Batman',
            'reference_number': '116710BLNR',
            'expected_variation': 'standard'
        },
        {
            'title': 'Rolex Submariner 5513 Military MilSub',
            'reference_number': '5513',
            'expected_variation': 'military'
        },
        {
            'title': 'Rolex Daytona 116500LN Domino\'s Pizza Dial',
            'reference_number': '116500LN',
            'expected_variation': 'dominos'
        }
    ]
    
    logger.info("Testing watch variation detection...")
    logger.info("=" * 60)
    
    passed = 0
    total = len(test_cases)
    
    for i, test_case in enumerate(test_cases, 1):
        # Create test listing
        listing = {
            'title': test_case['title'],
            'reference_number': test_case['reference_number']
        }
        
        # Apply variation detection
        scraper.detect_watch_variations(listing)
        
        # Extract detected variation from comparison_key
        comparison_key = listing.get('comparison_key', '')
        detected_variation = comparison_key.split('-')[-1] if '-' in comparison_key else 'unknown'
        
        # Check if detection was correct
        is_correct = detected_variation == test_case['expected_variation']
        status = "✅ PASS" if is_correct else "❌ FAIL"
        
        if is_correct:
            passed += 1
        
        logger.info(f"Test {i}: {status}")
        logger.info(f"  Title: {test_case['title']}")
        logger.info(f"  Expected: {test_case['expected_variation']}")
        logger.info(f"  Detected: {detected_variation}")
        logger.info(f"  Comparison Key: {comparison_key}")
        logger.info(f"  Special Edition: {listing.get('special_edition', 'None')}")
        logger.info(f"  Dial Type: {listing.get('dial_type', 'None')}")
        logger.info("")
    
    logger.info("=" * 60)
    logger.info(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        logger.success("All variation detection tests passed! 🎉")
    else:
        logger.warning(f"Some tests failed. Please review the variation detection logic.")
    
    return passed == total

def test_comparison_key_uniqueness():
    """Test that different variations get different comparison keys"""
    scraper = BobsWatchesScraper()
    
    # Test same reference with different variations
    variations = [
        {'title': 'Rolex Submariner 1680 Standard', 'reference_number': '1680'},
        {'title': 'Rolex Submariner 1680 Tiffany Dial', 'reference_number': '1680'},
        {'title': 'Rolex Submariner 1680 Military COMEX', 'reference_number': '1680'},
    ]
    
    comparison_keys = []
    logger.info("\nTesting comparison key uniqueness...")
    logger.info("=" * 40)
    
    for variation in variations:
        listing = variation.copy()
        scraper.detect_watch_variations(listing)
        comparison_key = listing.get('comparison_key')
        comparison_keys.append(comparison_key)
        
        logger.info(f"Title: {variation['title']}")
        logger.info(f"Comparison Key: {comparison_key}")
        logger.info("")
    
    # Check uniqueness
    unique_keys = set(comparison_keys)
    if len(unique_keys) == len(comparison_keys):
        logger.success("✅ All comparison keys are unique!")
        return True
    else:
        logger.error("❌ Some comparison keys are duplicated!")
        logger.error(f"Keys: {comparison_keys}")
        return False

if __name__ == "__main__":
    logger.info("Starting watch variation detection tests...\n")
    
    test1_passed = test_variation_detection()
    test2_passed = test_comparison_key_uniqueness()
    
    if test1_passed and test2_passed:
        logger.success("\n🎉 All tests passed! Variation tracking is working correctly.")
    else:
        logger.error("\n❌ Some tests failed. Please review the implementation.")