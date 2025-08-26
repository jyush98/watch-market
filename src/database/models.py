"""Database models for watch platform"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, JSON, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()

class WatchListing(Base):
    """Represents a watch listing from any source"""
    __tablename__ = 'watch_listings'
    
    id = Column(Integer, primary_key=True)
    
    # Source Information
    source = Column(String(50), nullable=False)  # 'chrono24', 'bobs_watches', etc.
    source_id = Column(String(100), unique=True, nullable=False)  # ID from source
    url = Column(String(500), nullable=False)
    
    # Watch Information
    brand = Column(String(100), nullable=False, index=True)
    model = Column(String(200), nullable=False, index=True)
    reference_number = Column(String(100), index=True)
    year = Column(Integer)
    
    # Condition & Accessories
    condition = Column(String(50))  # 'new', 'unworn', 'excellent', 'good', 'fair'
    has_box = Column(Boolean)
    has_papers = Column(Boolean)
    
    # Pricing
    price_usd = Column(Float, nullable=False, index=True)
    original_currency = Column(String(3))
    original_price = Column(Float)
    
    # Additional Details
    case_size_mm = Column(Integer)
    material = Column(String(100))  # 'steel', 'gold', 'two-tone'
    movement = Column(String(100))  # 'automatic', 'manual', 'quartz'
    
    # Variation Tracking for Accurate Price Comparisons
    dial_type = Column(String(100))  # 'Tiffany', 'Tropical', 'Spider', etc.
    special_edition = Column(String(200))  # 'Tiffany & Co', 'COMEX', 'Domino\'s', etc.
    comparison_key = Column(String(200), index=True)  # reference_number + variations for grouping
    
    # Seller Information
    seller_name = Column(String(200))
    seller_location = Column(String(200))
    seller_rating = Column(Float)
    
    # Metadata
    raw_data = Column(JSON)  # Store full scraped data
    first_seen = Column(DateTime, server_default=func.now())
    last_updated = Column(DateTime, server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    
    # Create composite indexes for common queries
    __table_args__ = (
        Index('idx_brand_model', 'brand', 'model'),
        Index('idx_reference_price', 'reference_number', 'price_usd'),
        Index('idx_active_updated', 'is_active', 'last_updated'),
        Index('idx_comparison_key_price', 'comparison_key', 'price_usd'),
    )
    
    def __repr__(self):
        return f"<WatchListing({self.brand} {self.model} - ${self.price_usd:,.0f})>"

class PriceHistory(Base):
    """Track price changes over time"""
    __tablename__ = 'price_history'
    
    id = Column(Integer, primary_key=True)
    listing_id = Column(Integer, index=True)
    source_id = Column(String(100), index=True)
    
    # Watch identification for aggregation
    comparison_key = Column(String(200), index=True)
    brand = Column(String(100), index=True)
    model = Column(String(200))
    reference_number = Column(String(100))
    
    # Price tracking
    price_usd = Column(Float, nullable=False, index=True)
    previous_price = Column(Float)
    timestamp = Column(DateTime, server_default=func.now(), index=True)
    
    # Track what changed
    price_change = Column(Float)  # Dollar amount change
    price_change_percent = Column(Float)  # Percentage change
    
    # Additional context
    source = Column(String(50))
    url = Column(String(500))
    
    __table_args__ = (
        Index('idx_comparison_key_timestamp', 'comparison_key', 'timestamp'),
        Index('idx_brand_model_timestamp', 'brand', 'model', 'timestamp'),
    )
    
class MarketAnalytics(Base):
    """Store computed market analytics"""
    __tablename__ = 'market_analytics'
    
    id = Column(Integer, primary_key=True)
    
    brand = Column(String(100), index=True)
    model = Column(String(200), index=True)
    reference_number = Column(String(100), index=True)
    
    # Computed metrics
    avg_price = Column(Float)
    min_price = Column(Float)
    max_price = Column(Float)
    median_price = Column(Float)
    total_listings = Column(Integer)
    
    # Trends
    price_trend_7d = Column(Float)  # Percentage change
    price_trend_30d = Column(Float)
    
    computed_at = Column(DateTime, server_default=func.now())