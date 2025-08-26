"""Price history tracking service"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from database.models import WatchListing, PriceHistory
from loguru import logger

class PriceHistoryService:
    """Service for tracking and analyzing price history"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def record_price_change(self, listing: WatchListing, previous_price: Optional[float] = None):
        """Record a price change for a listing"""
        try:
            # Calculate price change if we have previous price
            price_change = None
            price_change_percent = None
            
            if previous_price is not None and previous_price != listing.price_usd:
                price_change = listing.price_usd - previous_price
                price_change_percent = (price_change / previous_price) * 100
            
            # Create price history record
            history_record = PriceHistory(
                listing_id=listing.id,
                source_id=listing.source_id,
                comparison_key=listing.comparison_key,
                brand=listing.brand,
                model=listing.model,
                reference_number=listing.reference_number,
                price_usd=listing.price_usd,
                previous_price=previous_price,
                price_change=price_change,
                price_change_percent=price_change_percent,
                source=listing.source,
                url=listing.url
            )
            
            self.db.add(history_record)
            
            if price_change is not None:
                logger.info(f"Price change recorded for {listing.comparison_key}: ${previous_price:,.0f} → ${listing.price_usd:,.0f} ({price_change_percent:+.1f}%)")
            else:
                logger.debug(f"Initial price recorded for {listing.comparison_key}: ${listing.price_usd:,.0f}")
                
        except Exception as e:
            logger.error(f"Error recording price change: {e}")
    
    def get_price_history_by_comparison_key(self, comparison_key: str, days: int = 30) -> List[Dict]:
        """Get price history for a comparison key over the last N days"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        history = self.db.query(PriceHistory).filter(
            PriceHistory.comparison_key == comparison_key,
            PriceHistory.timestamp >= cutoff_date
        ).order_by(PriceHistory.timestamp.desc()).all()
        
        return [
            {
                'timestamp': record.timestamp.isoformat(),
                'price_usd': record.price_usd,
                'previous_price': record.previous_price,
                'price_change': record.price_change,
                'price_change_percent': record.price_change_percent,
                'source': record.source,
                'url': record.url
            }
            for record in history
        ]
    
    def get_market_price_trends(self, comparison_key: str, days: int = 30) -> Dict:
        """Get aggregated price trends for a comparison key"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Get all price points
        prices = self.db.query(PriceHistory).filter(
            PriceHistory.comparison_key == comparison_key,
            PriceHistory.timestamp >= cutoff_date
        ).order_by(PriceHistory.timestamp.asc()).all()
        
        if not prices:
            return {
                'comparison_key': comparison_key,
                'days': days,
                'data_points': 0,
                'current_avg_price': None,
                'trend': None
            }
        
        # Calculate trends
        price_values = [p.price_usd for p in prices]
        timestamps = [p.timestamp for p in prices]
        
        current_avg = sum(price_values) / len(price_values)
        
        # Simple trend calculation (first half vs second half)
        if len(price_values) >= 4:
            mid_point = len(price_values) // 2
            early_avg = sum(price_values[:mid_point]) / mid_point
            late_avg = sum(price_values[mid_point:]) / (len(price_values) - mid_point)
            trend_percent = ((late_avg - early_avg) / early_avg) * 100
        else:
            trend_percent = 0
        
        return {
            'comparison_key': comparison_key,
            'days': days,
            'data_points': len(prices),
            'current_avg_price': round(current_avg),
            'min_price': round(min(price_values)),
            'max_price': round(max(price_values)),
            'trend_percent': round(trend_percent, 1),
            'trend_direction': 'up' if trend_percent > 2 else 'down' if trend_percent < -2 else 'stable',
            'first_recorded': timestamps[0].isoformat(),
            'last_updated': timestamps[-1].isoformat(),
            'price_history': [
                {
                    'timestamp': p.timestamp.isoformat(),
                    'price': p.price_usd,
                    'change': p.price_change,
                    'change_percent': p.price_change_percent
                }
                for p in prices
            ]
        }
    
    def get_all_comparison_keys_with_history(self, min_data_points: int = 2) -> List[Dict]:
        """Get all comparison keys that have price history data"""
        
        # Get comparison keys with count of price history records
        results = self.db.query(
            PriceHistory.comparison_key,
            PriceHistory.brand,
            PriceHistory.model,
            PriceHistory.reference_number,
            func.count(PriceHistory.id).label('data_points'),
            func.avg(PriceHistory.price_usd).label('avg_price'),
            func.min(PriceHistory.price_usd).label('min_price'),
            func.max(PriceHistory.price_usd).label('max_price'),
            func.max(PriceHistory.timestamp).label('last_updated')
        ).group_by(
            PriceHistory.comparison_key,
            PriceHistory.brand,
            PriceHistory.model,
            PriceHistory.reference_number
        ).having(
            func.count(PriceHistory.id) >= min_data_points
        ).order_by(
            desc(func.count(PriceHistory.id))
        ).all()
        
        return [
            {
                'comparison_key': r.comparison_key,
                'brand': r.brand,
                'model': r.model,
                'reference_number': r.reference_number,
                'data_points': r.data_points,
                'avg_price': round(r.avg_price),
                'min_price': round(r.min_price),
                'max_price': round(r.max_price),
                'price_range': round(r.max_price - r.min_price),
                'last_updated': r.last_updated.isoformat() if r.last_updated else None
            }
            for r in results
        ]
    
    def backfill_price_history(self):
        """Create initial price history records from current listings"""
        logger.info("Backfilling price history from current listings...")
        
        listings = self.db.query(WatchListing).filter(
            WatchListing.comparison_key != None
        ).all()
        
        created_count = 0
        for listing in listings:
            # Check if we already have a record for this listing
            existing = self.db.query(PriceHistory).filter(
                PriceHistory.source_id == listing.source_id
            ).first()
            
            if not existing:
                self.record_price_change(listing, previous_price=None)
                created_count += 1
        
        self.db.commit()
        logger.success(f"Created {created_count} initial price history records")
        return created_count