# Blog #002: Building the Database Foundation

*Date: August 26, 2025*

## The Heart of Market Intelligence: Database Design

After establishing our project vision, the first critical step was designing a database schema that could handle the complexity of luxury watch variations while maintaining performance for real-time market analysis.

### Core Challenges

1. **Variation Complexity**: Watches with identical reference numbers can have vastly different values
2. **Price History**: Need to track price movements over time for trend analysis  
3. **Multi-Source Data**: Handling data from different dealers with varying formats
4. **Performance**: Fast queries for arbitrage detection and market analytics

### Database Schema Evolution

**WatchListing Model** - The core entity:
```python
class WatchListing(Base):
    # Basic Information
    brand = Column(String(100), nullable=False, index=True)
    model = Column(String(200), nullable=False, index=True)  
    reference_number = Column(String(100), index=True)
    
    # Variation Tracking - THE GAME CHANGER
    dial_type = Column(String(100))  # 'Tiffany', 'Tropical', 'Spider'
    special_edition = Column(String(200))  # 'Tiffany & Co', 'COMEX'
    comparison_key = Column(String(200), index=True)  # reference + variation
    
    # Pricing
    price_usd = Column(Float, nullable=False, index=True)
```

**PriceHistory Model** - For market intelligence:
```python
class PriceHistory(Base):
    comparison_key = Column(String(200), index=True)
    price_usd = Column(Float, nullable=False) 
    previous_price = Column(Float)
    price_change = Column(Float)  # Dollar amount
    price_change_percent = Column(Float)  # Percentage
    timestamp = Column(DateTime, index=True)
```

### The Comparison Key Innovation

The breakthrough was the **comparison_key** field that combines reference number with variation suffix:
- `1680-standard` (regular Submariner)
- `1680-tiffany` (Tiffany dial version)
- `1680-tropical` (rare tropical dial)
- `16613-blackbezel` vs `16613-bluebezel`

This allows accurate price comparisons within truly comparable watches while preserving the ability to identify real arbitrage opportunities.

### Performance Optimizations

Strategic indexing for common queries:
```python
__table_args__ = (
    Index('idx_brand_model', 'brand', 'model'),
    Index('idx_reference_price', 'reference_number', 'price_usd'),
    Index('idx_comparison_key_price', 'comparison_key', 'price_usd'),
    Index('idx_comparison_key_timestamp', 'comparison_key', 'timestamp'),
)
```

### Database Migration Strategy

Created `add_variation_columns.py` for seamless schema updates:
- Added variation tracking fields to existing listings
- Preserved all historical data
- Generated comparison keys for existing records
- Zero downtime deployment

### Results

The new schema immediately improved arbitrage detection accuracy:
- **Before**: 45 watches flagged with false 300%+ price differences
- **After**: 12 special variations properly separated, realistic arbitrage opportunities identified

Next challenge: Building the scraping engine that can populate this intelligent database structure.

---
*Next: Web scraping with sophisticated variation detection*