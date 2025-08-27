"""
Epic #008: WhatsApp Conversational Watch Parser
Extracts watch listings from informal WhatsApp dealer communications
"""

import re
from typing import Dict, List, Tuple, Optional
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class WatchInfo:
    brand: Optional[str] = None
    model: Optional[str] = None
    reference: Optional[str] = None
    special_edition: Optional[str] = None
    material: Optional[str] = None
    dial_color: Optional[str] = None
    confidence: float = 0.0

@dataclass
class ParsedListing:
    watch_info: WatchInfo
    price_usd: Optional[float]
    raw_message: str
    confidence: float
    source_type: str = 'wholesale'
    communication_type: str = 'whatsapp_group'

class WhatsAppWatchParser:
    def __init__(self):
        # Price patterns for different formats
        self.price_patterns = [
            r'\$([0-9,]+(?:\.[0-9]{2})?)',           # $15,000 or $15,000.00
            r'([0-9,]+(?:\.[0-9]{2})?)[\s]*USD',    # 15000 USD or 15,000 USD
            r'([0-9]+)K(?![0-9])',                  # 15K (not part of reference number)
            r'([0-9,]+)[\s]*dollars?',              # 15000 dollars
            r'USD[\s]*([0-9,]+)',                   # USD 15000
            r'asking[\s]+\$?([0-9,]+)K?',          # asking $42K or asking 42000
            r'budget[\s]+around[\s]+([0-9]+)K',     # budget around 25K
            r'\$([0-9]+)K',                         # $42K format
        ]
        
        # Watch identification patterns
        self.rolex_patterns = [
            # Submariner patterns
            (r'(?:Sub|Submariner)[\s]*(\d{4,6})', 'Rolex', 'Submariner'),
            (r'(\d{4,6})[\s]+Sub(?:mariner)?', 'Rolex', 'Submariner'),
            
            # GMT patterns  
            (r'GMT[\s-]*Master[\s]*(\d{4,5})', 'Rolex', 'GMT-Master'),
            (r'(\d{4,5})[\s]+GMT', 'Rolex', 'GMT-Master'),
            
            # Day-Date patterns
            (r'Day[\s-]*Date[\s]*(\d{4,6})', 'Rolex', 'Day-Date'),
            (r'DD[\s]*(\d{4,6})', 'Rolex', 'Day-Date'),
            (r'(\d{4,6})[\s]+DD', 'Rolex', 'Day-Date'),
            
            # Daytona patterns
            (r'Daytona[\s]*(\d{4,6})', 'Rolex', 'Daytona'),
            (r'(\d{4,6})[\s]+Daytona', 'Rolex', 'Daytona'),
            
            # Explorer patterns
            (r'Explorer[\s]*(\d{4,5})', 'Rolex', 'Explorer'),
            (r'(\d{4,5})[\s]+Explorer', 'Rolex', 'Explorer'),
            
            # Sea-Dweller patterns
            (r'Sea[\s-]*Dweller[\s]*(\d{4,5})', 'Rolex', 'Sea-Dweller'),
            (r'(\d{4,5})[\s]+Sea[\s-]*Dweller', 'Rolex', 'Sea-Dweller'),
            
            # Yacht-Master patterns
            (r'Yacht[\s-]*Master[\s]*(\d{4,6})', 'Rolex', 'Yacht-Master'),
            (r'YM[\s]*(\d{4,6})', 'Rolex', 'Yacht-Master'),
            (r'(\d{4,6})[\s]+YM', 'Rolex', 'Yacht-Master'),
            
            # Air-King patterns
            (r'Air[\s-]*King[\s]*(\d{4,5})', 'Rolex', 'Air-King'),
            (r'(\d{4,5})[\s]+Air[\s-]*King', 'Rolex', 'Air-King'),
            
            # Milgauss patterns
            (r'Milgauss[\s]*(\d{4,6})', 'Rolex', 'Milgauss'),
            (r'(\d{4,6})[\s]+Milgauss', 'Rolex', 'Milgauss'),
            
            # Domino's Pizza and special model patterns
            (r'Domino\'?s[\s]*Pizza[\s]*(\d{4,6})', 'Rolex', 'Oyster Perpetual'),
            (r'(\d{4,6})[\s]*(?:Domino\'?s|Pizza)', 'Rolex', 'Oyster Perpetual'),
            
            # Generic reference number patterns
            (r'Rolex[\s]+(\d{4,6})', 'Rolex', None),
            (r'(\d{4,6})[\s]+Rolex', 'Rolex', None),
        ]
        
        # Special edition patterns
        self.special_edition_patterns = [
            (r'Tiffany|T&Co|Tiffany & Co', 'Tiffany & Co'),
            (r'Tropical|Tropicalized', 'Tropical'),
            (r'Spider|Spider dial', 'Spider'),
            (r'COMEX|Comex', 'COMEX'),
            (r"Domino'?s|Pizza", "Domino's"),
            (r'Military|Mil-Sub', 'Military'),
            (r'Paul Newman|PN', 'Paul Newman'),
            (r'Hulk', 'Hulk'),
            (r'Pepsi', 'Pepsi'),
            (r'Coke|Coca Cola', 'Coke'),
            (r'Batman', 'Batman'),
            (r'Kermit', 'Kermit'),
            (r'Starbucks', 'Starbucks'),
            (r'Smurf', 'Smurf'),
        ]
        
        # Material patterns
        self.material_patterns = [
            (r'Yellow[\s]+Gold|YG|18K[\s]*Y', 'Yellow Gold'),
            (r'White[\s]+Gold|WG|18K[\s]*W', 'White Gold'), 
            (r'Rose[\s]+Gold|RG|18K[\s]*R', 'Rose Gold'),
            (r'Two[\s-]*Tone|TT|Bi[\s-]*metal', 'Two-Tone'),
            (r'Steel|SS|Stainless', 'Steel'),
            (r'Platinum|PT|950', 'Platinum'),
            (r'Titanium|Ti', 'Titanium'),
        ]
        
        # Dial color patterns
        self.dial_patterns = [
            (r'Black[\s]+dial|Black[\s]+face', 'Black'),
            (r'Blue[\s]+dial|Blue[\s]+face', 'Blue'),
            (r'White[\s]+dial|White[\s]+face', 'White'),
            (r'Green[\s]+dial|Green[\s]+face', 'Green'),
            (r'Champagne[\s]+dial', 'Champagne'),
            (r'Silver[\s]+dial', 'Silver'),
            (r'Salmon[\s]+dial', 'Salmon'),
            (r'Meteorite[\s]+dial', 'Meteorite'),
            (r'Mother[\s]+of[\s]+pearl|MOP', 'Mother of Pearl'),
        ]
    
    def extract_prices(self, text: str) -> List[float]:
        """Extract all prices from text"""
        prices = []
        
        for pattern in self.price_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    # Clean up the price string
                    price_str = match.replace(',', '').replace('K', '000')
                    price = float(price_str)
                    
                    # Reasonable price range for luxury watches
                    if 1000 <= price <= 2000000:
                        prices.append(price)
                except (ValueError, TypeError):
                    continue
        
        return list(set(prices))  # Remove duplicates
    
    def extract_watch_details(self, text: str) -> List[WatchInfo]:
        """Extract watch information from text"""
        watches = []
        
        # Try Rolex patterns first
        for pattern, brand, model in self.rolex_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                watch_info = WatchInfo(
                    brand=brand,
                    model=model,
                    reference=match.group(1),
                    confidence=0.7 if model else 0.5
                )
                
                # Look for special editions near this match
                context_start = max(0, match.start() - 50)
                context_end = min(len(text), match.end() + 50)
                context = text[context_start:context_end]
                
                # Check for special editions
                for pattern_se, edition in self.special_edition_patterns:
                    if re.search(pattern_se, context, re.IGNORECASE):
                        watch_info.special_edition = edition
                        watch_info.confidence += 0.2
                        break
                
                # Check for materials
                for pattern_mat, material in self.material_patterns:
                    if re.search(pattern_mat, context, re.IGNORECASE):
                        watch_info.material = material
                        watch_info.confidence += 0.1
                        break
                
                # Check for dial colors
                for pattern_dial, dial in self.dial_patterns:
                    if re.search(pattern_dial, context, re.IGNORECASE):
                        watch_info.dial_color = dial
                        watch_info.confidence += 0.1
                        break
                
                watches.append(watch_info)
        
        return watches
    
    def match_price_to_watch(self, watches: List[WatchInfo], prices: List[float]) -> List[Tuple[WatchInfo, float]]:
        """Match extracted prices to watch information"""
        matched_pairs = []
        
        if not watches or not prices:
            return matched_pairs
        
        # Simple matching - if single watch and single price, match them
        if len(watches) == 1 and len(prices) == 1:
            matched_pairs.append((watches[0], prices[0]))
        
        # If multiple watches and prices, try to match by proximity or context
        elif len(watches) == len(prices):
            for watch, price in zip(watches, prices):
                matched_pairs.append((watch, price))
        
        # If mismatch, take the highest confidence watch with first price
        elif watches and prices:
            best_watch = max(watches, key=lambda w: w.confidence)
            matched_pairs.append((best_watch, prices[0]))
        
        return matched_pairs
    
    def generate_comparison_key(self, watch_info: WatchInfo) -> str:
        """Generate comparison key for database storage"""
        if not watch_info.reference:
            return None
        
        key_parts = [watch_info.reference]
        
        # Add special edition suffix
        if watch_info.special_edition:
            if watch_info.special_edition.lower() == 'tiffany & co':
                key_parts.append('tiffany')
            elif watch_info.special_edition.lower() == 'tropical':
                key_parts.append('tropical')
            elif watch_info.special_edition.lower() == 'spider':
                key_parts.append('spider')
            elif watch_info.special_edition.lower() == 'comex':
                key_parts.append('comex')
            elif watch_info.special_edition.lower() == "domino's":
                key_parts.append('dominos')
            elif watch_info.special_edition.lower() == 'hulk':
                key_parts.append('hulk')
            elif watch_info.special_edition.lower() == 'pepsi':
                key_parts.append('pepsi')
            elif watch_info.special_edition.lower() == 'batman':
                key_parts.append('batman')
            elif watch_info.special_edition.lower() == 'kermit':
                key_parts.append('kermit')
        
        # Add material suffix for precious metals
        if watch_info.material:
            if 'gold' in watch_info.material.lower():
                key_parts.append('gold')
            elif watch_info.material.lower() == 'two-tone':
                key_parts.append('twotone')
            elif watch_info.material.lower() == 'platinum':
                key_parts.append('platinum')
        
        # Add dial color for distinctive dials
        if watch_info.dial_color:
            dial_lower = watch_info.dial_color.lower()
            if dial_lower in ['blue', 'green', 'black', 'white', 'champagne']:
                key_parts.append(dial_lower + 'dial')
        
        # If no variations detected, add 'standard'
        if len(key_parts) == 1:
            key_parts.append('standard')
        
        return '-'.join(key_parts).lower()
    
    def parse_message(self, message_text: str, dealer_group: Optional[str] = None) -> List[ParsedListing]:
        """Main parsing function to extract watch listings from WhatsApp messages"""
        if not message_text or len(message_text.strip()) < 10:
            return []
        
        logger.info(f"Parsing WhatsApp message: {message_text[:100]}...")
        
        listings = []
        
        try:
            # Extract prices and watch details
            prices = self.extract_prices(message_text)
            watches = self.extract_watch_details(message_text)
            
            logger.info(f"Found {len(prices)} prices and {len(watches)} watches")
            
            # Match prices to watches
            matched_pairs = self.match_price_to_watch(watches, prices)
            
            for watch_info, price in matched_pairs:
                # Calculate overall confidence
                confidence = watch_info.confidence
                if price and 5000 <= price <= 500000:  # Reasonable luxury watch price range
                    confidence += 0.1
                
                # Generate comparison key
                comparison_key = self.generate_comparison_key(watch_info)
                
                listing = ParsedListing(
                    watch_info=watch_info,
                    price_usd=price,
                    raw_message=message_text,
                    confidence=confidence,
                    source_type='wholesale',
                    communication_type='whatsapp_group'
                )
                
                listings.append(listing)
                logger.info(f"Created listing: {watch_info.brand} {watch_info.model} {watch_info.reference} - ${price}")
        
        except Exception as e:
            logger.error(f"Error parsing WhatsApp message: {e}")
        
        return listings

    def parse_whatsapp_export(self, chat_export_text: str, dealer_group: str) -> List[ParsedListing]:
        """Parse entire WhatsApp chat export"""
        # Split by message boundaries (WhatsApp export format: timestamp - sender: message)
        message_pattern = r'\d{1,2}/\d{1,2}/\d{2,4},\s\d{1,2}:\d{2}\s[AP]M\s-\s[^:]+:\s'
        messages = re.split(message_pattern, chat_export_text)
        
        all_listings = []
        
        for message in messages:
            if message.strip():
                listings = self.parse_message(message.strip(), dealer_group)
                all_listings.extend(listings)
        
        logger.info(f"Parsed {len(all_listings)} total listings from {dealer_group}")
        return all_listings


# Example usage and testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    parser = WhatsAppWatchParser()
    
    # Test messages
    test_messages = [
        "Got a nice Sub 1680 Tiffany dial, asking $42K",
        "Daytona 116520 white dial excellent condition $28,000 USD",
        "Looking for GMT 1675 Pepsi, budget around 25K",
        "Have Domino's Pizza 126000 for sale, $6500",
        "Tropical dial 1675 GMT, very rare piece - $35,000",
        "Day-Date 18239 presidential bracelet yellow gold $45K",
        "Blue dial Sub 116619 white gold asking 32000 dollars",
    ]
    
    for message in test_messages:
        print(f"\n--- Testing: {message} ---")
        listings = parser.parse_message(message)
        for listing in listings:
            print(f"Brand: {listing.watch_info.brand}")
            print(f"Model: {listing.watch_info.model}")
            print(f"Reference: {listing.watch_info.reference}")
            print(f"Special Edition: {listing.watch_info.special_edition}")
            print(f"Material: {listing.watch_info.material}")
            print(f"Dial: {listing.watch_info.dial_color}")
            print(f"Price: ${listing.price_usd:,.0f}")
            print(f"Confidence: {listing.confidence:.2f}")
            print(f"Comparison Key: {parser.generate_comparison_key(listing.watch_info)}")
            print()