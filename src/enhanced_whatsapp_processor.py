#!/usr/bin/env python3
"""
Enhanced WhatsApp Processor with Image Correlation
Processes real dealer WhatsApp exports with professional watch terminology
"""

import os
import re
import json
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class DealerMessage:
    timestamp: datetime
    dealer_name: str
    phone_number: Optional[str]
    message_text: str
    has_image: bool
    image_files: List[str]
    
@dataclass  
class EnhancedWatchListing:
    # Basic info
    brand: Optional[str] = None
    model: Optional[str] = None
    reference_number: Optional[str] = None
    
    # Dealer-specific details
    serial_number: Optional[str] = None
    condition: Optional[str] = None  # "naked", "full links", "mint", etc.
    year: Optional[str] = None
    
    # Pricing
    price_usd: Optional[float] = None
    includes_label: bool = False  # "+ label" shipping cost
    
    # Watch specifics
    dial_color: Optional[str] = None
    material: Optional[str] = None
    special_edition: Optional[str] = None
    bracelet_condition: Optional[str] = None  # "no stretch", "full links"
    case_condition: Optional[str] = None  # "razor sharp", "unpolished"
    
    # Accessories
    has_box: Optional[bool] = None
    has_papers: Optional[bool] = None
    has_warranty_card: Optional[bool] = None
    complete_set: bool = False
    
    # Metadata
    dealer_name: str = ""
    timestamp: Optional[datetime] = None
    raw_message: str = ""
    confidence: float = 0.0
    image_files: List[str] = None
    comparison_key: Optional[str] = None

class EnhancedWhatsAppProcessor:
    def __init__(self):
        # Enhanced patterns for professional dealer terminology
        self.enhanced_rolex_patterns = [
            # Standard patterns with better reference capture
            (r'(\d{6}[A-Z]*)\s*(?:,|\s|$)', 'Rolex', None, 0.8),  # 6-digit refs like 116610LN
            (r'(\d{5}[A-Z]*)\s*(?:,|\s|$)', 'Rolex', None, 0.7),  # 5-digit refs like 16613
            (r'(\d{4}[A-Z]*)\s*(?:,|\s|$)', 'Rolex', None, 0.6),  # 4-digit vintage like 1675
            
            # Model-specific with references
            (r'(?:Sub|Submariner).*?(\d{4,6}[A-Z]*)', 'Rolex', 'Submariner', 0.9),
            (r'(?:GMT|GMT-Master).*?(\d{4,6}[A-Z]*)', 'Rolex', 'GMT-Master', 0.9),
            (r'(?:Daytona).*?(\d{4,6}[A-Z]*)', 'Rolex', 'Daytona', 0.9),
            (r'(?:Explorer).*?(\d{4,6}[A-Z]*)', 'Rolex', 'Explorer', 0.9),
            (r'(?:Day-Date|DD).*?(\d{4,6}[A-Z]*)', 'Rolex', 'Day-Date', 0.9),
            (r'(?:Yacht-Master|YM).*?(\d{4,6}[A-Z]*)', 'Rolex', 'Yacht-Master', 0.9),
            (r'(?:Milgauss).*?(\d{4,6}[A-Z]*)', 'Rolex', 'Milgauss', 0.9),
            (r'(?:Sea-Dweller).*?(\d{4,6}[A-Z]*)', 'Rolex', 'Sea-Dweller', 0.9),
            (r'(?:Air-King).*?(\d{4,6}[A-Z]*)', 'Rolex', 'Air-King', 0.9),
            
            # Vintage model patterns
            (r'(\d{4}),\s*([A-Z])\s*ser', 'Rolex', None, 0.9),  # "16220, L ser."
        ]
        
        # Other luxury brands
        self.other_brand_patterns = [
            (r'Omega.*?(\d{3}\.\d{2}\.\d{2}\.\d{2}\.\d{2}\.\d{3})', 'Omega', None, 0.9),
            (r'Cartier.*?(\d{4})', 'Cartier', None, 0.8),
            (r'(RM\d{2}[-\d]*)', 'Richard Mille', None, 0.9),  # Richard Mille
            (r'Patek.*?(\d{4})', 'Patek Philippe', None, 0.9),
        ]
        
        # Professional dealer terminology
        self.condition_patterns = [
            (r'\bnaked\b', 'naked'),  # watch only, no box/papers
            (r'\bmint\b', 'mint'),
            (r'\bexcellent\b', 'excellent'), 
            (r'\bunpolished\b', 'unpolished'),
            (r'\brazor sharp\b', 'razor sharp'),
            (r'\bno holes\b', 'no holes'),
            (r'\bbrand new\b', 'brand new'),
            (r'\bNTQ\b', 'new to quality'),  # Dealer term
            (r'\bcomplete\b', 'complete'),
            (r'\bfull set\b', 'full set'),
        ]
        
        self.bracelet_patterns = [
            (r'\bfull links\b', 'full links'),
            (r'\bno stretch\b', 'no stretch'),
            (r'\bsolid oyster\b', 'solid oyster'),
            (r'\bfully linked\b', 'fully linked'),
            (r'\b(\d+)\s*links\b', lambda m: f'{m.group(1)} links'),
        ]
        
        # Enhanced price patterns for dealer format
        self.price_patterns = [
            r'\$([0-9,]+(?:\.[0-9]{2})?)',           # $15,000 
            r'([0-9,]+(?:\.[0-9]{2})?)[\s]*USD',    # 15000 USD
            r'\$([0-9]+)K',                         # $42K
            r'([0-9]+)K[\s]*\+',                    # 42K + (before "label")
            r'\$([0-9,]+)[\s]*\+',                  # $15,000 + (before "label")
        ]
        
        # Serial number patterns
        self.serial_patterns = [
            (r'([A-Z])\s*ser\.?', 'serial_letter'),  # "L ser."
            (r'ser\.?\s*([A-Z]\d+)', 'serial_full'),  # "ser. L123456"
        ]

    def parse_chat_export(self, chat_file_path: str, image_dir_path: str) -> List[DealerMessage]:
        """Parse WhatsApp chat export and correlate with images"""
        logger.info(f"Processing chat file: {chat_file_path}")
        
        with open(chat_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse message format: [7/31/25, 5:20:16 AM] ~ Dealer Name: message
        message_pattern = r'(?:^|\n)\[(\d{1,2}/\d{1,2}/\d{2,4}),\s*(\d{1,2}:\d{2}:\d{2}\s*[AP]M)\]\s*(?:~\s*(.+?)|([+\s\d()-]+)):\s*(.+?)(?=\n\[|\Z)'
        
        messages = []
        image_files = self._get_image_files_by_timestamp(image_dir_path)
        
        for match in re.finditer(message_pattern, content, re.DOTALL | re.MULTILINE):
            date_str, time_str, dealer_name, phone_number, message_text = match.groups()
            
            # Parse timestamp
            try:
                # Handle different year formats
                if len(date_str.split('/')[-1]) == 2:
                    year = f"20{date_str.split('/')[-1]}"
                    date_str = '/'.join(date_str.split('/')[:-1] + [year])
                
                timestamp = datetime.strptime(f"{date_str} {time_str}", "%m/%d/%Y %I:%M:%S %p")
            except ValueError as e:
                logger.warning(f"Could not parse timestamp: {date_str} {time_str} - {e}")
                continue
            
            # Clean up message text
            message_text = message_text.strip()
            has_image = '‎image omitted' in message_text
            
            # Find correlated images within 30 minutes
            correlated_images = []
            if has_image:
                for img_file, img_time in image_files:
                    time_diff = abs((timestamp - img_time).total_seconds())
                    if time_diff <= 1800:  # 30 minutes
                        correlated_images.append(img_file)
            
            # Skip empty messages or pure image messages without text content
            if not message_text or message_text == '‎image omitted':
                continue
                
            message = DealerMessage(
                timestamp=timestamp,
                dealer_name=dealer_name or phone_number or "Unknown",
                phone_number=phone_number,
                message_text=message_text,
                has_image=has_image,
                image_files=correlated_images
            )
            messages.append(message)
        
        logger.info(f"Parsed {len(messages)} messages with text content")
        return messages

    def _get_image_files_by_timestamp(self, image_dir_path: str) -> List[Tuple[str, datetime]]:
        """Get image files with their timestamps from filename"""
        image_files = []
        image_dir = Path(image_dir_path)
        
        # Pattern: 00000010-PHOTO-2025-08-29-15-49-47.jpg
        filename_pattern = r'.*PHOTO-(\d{4})-(\d{2})-(\d{2})-(\d{2})-(\d{2})-(\d{2})\.jpg'
        
        for img_file in image_dir.glob('*.jpg'):
            match = re.match(filename_pattern, img_file.name)
            if match:
                year, month, day, hour, minute, second = map(int, match.groups())
                try:
                    timestamp = datetime(year, month, day, hour, minute, second)
                    image_files.append((img_file.name, timestamp))
                except ValueError:
                    logger.warning(f"Invalid timestamp in filename: {img_file.name}")
        
        return sorted(image_files, key=lambda x: x[1])

    def extract_watch_listing(self, message: DealerMessage) -> Optional[EnhancedWatchListing]:
        """Extract enhanced watch listing from dealer message"""
        text = message.message_text.lower()
        
        listing = EnhancedWatchListing(
            dealer_name=message.dealer_name,
            timestamp=message.timestamp,
            raw_message=message.message_text,
            image_files=message.image_files
        )
        
        # Try to extract watch information
        watch_found = False
        
        # Check Rolex patterns first
        for pattern, brand, model, confidence in self.enhanced_rolex_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                listing.brand = brand
                listing.model = model
                listing.reference_number = match.group(1).upper()
                listing.confidence = confidence
                watch_found = True
                break
            if watch_found:
                break
        
        # Try other brands if no Rolex found
        if not watch_found:
            for pattern, brand, model, confidence in self.other_brand_patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    listing.brand = brand
                    listing.model = model
                    listing.reference_number = match.group(1)
                    listing.confidence = confidence
                    watch_found = True
                    break
                if watch_found:
                    break
        
        if not watch_found:
            return None
        
        # Extract pricing
        listing.price_usd = self._extract_price(message.message_text)
        listing.includes_label = '+ label' in text.lower()
        
        # Extract condition details
        listing.condition = self._extract_condition(text)
        listing.bracelet_condition = self._extract_bracelet_condition(text)
        
        # Extract serial information
        listing.serial_number = self._extract_serial(text)
        
        # Extract accessories
        listing.complete_set = any(phrase in text for phrase in ['complete set', 'full set', 'complete'])
        listing.has_box = 'box' in text and 'no box' not in text
        listing.has_papers = any(phrase in text for phrase in ['papers', 'card', 'warranty'])
        
        # Generate comparison key
        listing.comparison_key = self._generate_comparison_key(listing)
        
        return listing

    def _extract_price(self, text: str) -> Optional[float]:
        """Extract price from dealer message"""
        for pattern in self.price_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    price_str = match.replace(',', '').replace('K', '000')
                    price = float(price_str)
                    if 1000 <= price <= 2000000:  # Reasonable range
                        return price
                except (ValueError, TypeError):
                    continue
        return None

    def _extract_condition(self, text: str) -> Optional[str]:
        """Extract watch condition from dealer terminology"""
        for pattern, condition in self.condition_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return condition
        return None

    def _extract_bracelet_condition(self, text: str) -> Optional[str]:
        """Extract bracelet/strap condition"""
        for pattern, condition in self.bracelet_patterns:
            if callable(condition):
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    return condition(match)
            elif re.search(pattern, text, re.IGNORECASE):
                return condition
        return None

    def _extract_serial(self, text: str) -> Optional[str]:
        """Extract serial number information"""
        for pattern, serial_type in self.serial_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def _generate_comparison_key(self, listing: EnhancedWatchListing) -> str:
        """Generate comparison key for database matching"""
        if not listing.reference_number:
            return None
        
        key_parts = [listing.reference_number.lower()]
        
        # Add condition modifiers that affect pricing
        if listing.condition in ['tropical', 'spider']:
            key_parts.append(listing.condition)
        if listing.complete_set:
            key_parts.append('fullset')
        
        return '-'.join(key_parts)

    def process_chat_export(self, chat_file_path: str, image_dir_path: str) -> Dict:
        """Process entire WhatsApp chat export"""
        logger.info("Starting enhanced WhatsApp processing...")
        
        # Parse messages
        messages = self.parse_chat_export(chat_file_path, image_dir_path)
        
        # Extract watch listings
        listings = []
        for message in messages:
            listing = self.extract_watch_listing(message)
            if listing:
                listings.append(listing)
        
        # Generate summary
        summary = {
            'total_messages': len(messages),
            'total_listings': len(listings),
            'dealers': list(set(msg.dealer_name for msg in messages)),
            'date_range': {
                'start': min(msg.timestamp for msg in messages).isoformat() if messages else None,
                'end': max(msg.timestamp for msg in messages).isoformat() if messages else None
            },
            'listings': [asdict(listing) for listing in listings]
        }
        
        logger.info(f"✅ Processed {len(messages)} messages, extracted {len(listings)} watch listings")
        return summary


def demo_enhanced_processor():
    """Demo the enhanced processor with real data"""
    chat_file = "/Users/jonathan/Desktop/Projects/watch-market/whatsapp/WhatsApp Chat - USA WATCH DEALERS/_chat.txt"
    image_dir = "/Users/jonathan/Desktop/Projects/watch-market/whatsapp/WhatsApp Chat - USA WATCH DEALERS/"
    
    processor = EnhancedWhatsAppProcessor()
    results = processor.process_chat_export(chat_file, image_dir)
    
    print("🚀 ENHANCED WHATSAPP PROCESSOR RESULTS")
    print("=" * 50)
    print(f"📊 Total Messages: {results['total_messages']}")
    print(f"⌚ Watch Listings: {results['total_listings']}")
    print(f"👥 Active Dealers: {len(results['dealers'])}")
    print(f"📅 Date Range: {results['date_range']['start']} to {results['date_range']['end']}")
    
    print("\n🔥 TOP WATCH LISTINGS:")
    for i, listing in enumerate(results['listings'][:10], 1):
        price_str = f"${listing['price_usd']:,.0f}" if listing['price_usd'] else "No price"
        print(f"{i:2d}. {listing['brand']} {listing['model'] or 'Unknown'} {listing['reference_number']}")
        print(f"    💰 {price_str} | 🏪 {listing['dealer_name'][:20]}")
        print(f"    📋 {listing['condition'] or 'N/A'} | 🔗 {listing['bracelet_condition'] or 'N/A'}")
        if listing['image_files']:
            print(f"    📸 {len(listing['image_files'])} images")
        print()

if __name__ == "__main__":
    demo_enhanced_processor()