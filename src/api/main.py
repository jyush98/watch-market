"""FastAPI backend for watch platform"""
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Dict, Optional
from pydantic import BaseModel
import sys
import os

# Add parent directory to path so we can import from database module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import get_db
from database.models import WatchListing
from services.price_history import PriceHistoryService

app = FastAPI(title="Watch Market Intelligence API")

# Allow CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class WatchResponse(BaseModel):
    id: int
    brand: str
    model: str
    reference_number: Optional[str] = None
    price_usd: float
    url: str
    source: str
    # Variation tracking fields
    dial_type: Optional[str] = None
    special_edition: Optional[str] = None
    comparison_key: Optional[str] = None
    
    class Config:
        from_attributes = True

@app.get("/")
def root():
    return {"message": "Watch Market Intelligence API", "version": "1.0.0"}

@app.get("/api/watches", response_model=List[WatchResponse])
def get_watches(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all watches with pagination"""
    watches = db.query(WatchListing).offset(skip).limit(limit).all()
    return watches

@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    """Get market statistics"""
    total = db.query(WatchListing).count()
    avg_price = db.query(func.avg(WatchListing.price_usd)).scalar()
    min_price = db.query(func.min(WatchListing.price_usd)).scalar()
    max_price = db.query(func.max(WatchListing.price_usd)).scalar()
    
    by_model = db.query(
        WatchListing.model,
        func.count(WatchListing.id).label('count'),
        func.avg(WatchListing.price_usd).label('avg_price')
    ).group_by(WatchListing.model).all()
    
    return {
        "total_watches": total,
        "avg_price": round(avg_price) if avg_price else 0,
        "min_price": round(min_price) if min_price else 0,
        "max_price": round(max_price) if max_price else 0,
        "by_model": [
            {"model": m[0], "count": m[1], "avg_price": round(m[2])} 
            for m in by_model
        ]
    }

@app.get("/api/reference-analysis")
def get_reference_analysis(db: Session = Depends(get_db)):
    """Analyze prices by comparison key (reference + variations)"""
    
    # Get stats grouped by comparison_key instead of reference_number
    ref_stats = db.query(
        WatchListing.comparison_key,
        WatchListing.reference_number,
        WatchListing.model,
        WatchListing.special_edition,
        func.count(WatchListing.id).label('count'),
        func.avg(WatchListing.price_usd).label('avg_price'),
        func.min(WatchListing.price_usd).label('min_price'),
        func.max(WatchListing.price_usd).label('max_price')
    ).filter(
        WatchListing.comparison_key != None
    ).group_by(
        WatchListing.comparison_key,
        WatchListing.reference_number,
        WatchListing.model,
        WatchListing.special_edition
    ).having(
        func.count(WatchListing.id) > 1  # Only comparison keys with multiple listings
    ).all()
    
    results = []
    for ref in ref_stats:
        spread_percentage = ((ref.max_price - ref.min_price) / ref.avg_price) * 100
        
        # Get individual listings for this comparison key
        listings = db.query(WatchListing).filter(
            WatchListing.comparison_key == ref.comparison_key
        ).all()
        
        results.append({
            "comparison_key": ref.comparison_key,
            "reference": ref.reference_number,
            "model": ref.model,
            "special_edition": ref.special_edition,
            "count": ref.count,
            "avg_price": round(ref.avg_price),
            "min_price": round(ref.min_price),
            "max_price": round(ref.max_price),
            "price_spread": round(spread_percentage),
            "listings": [
                {
                    "id": l.id,
                    "price": l.price_usd,
                    "deviation_from_avg": round((l.price_usd - ref.avg_price) / ref.avg_price * 100),
                    "url": l.url,
                    "dial_type": l.dial_type,
                    "special_edition": l.special_edition
                }
                for l in listings
            ]
        })
    
    # Sort by price spread to find biggest arbitrage opportunities
    results.sort(key=lambda x: x['price_spread'], reverse=True)
    return results

@app.get("/api/arbitrage-opportunities")
def get_arbitrage_opportunities(db: Session = Depends(get_db)):
    """Find the best arbitrage opportunities based on comparison keys (prevents false arbitrage from variations)"""
    
    # Get comparison keys with significant price spreads
    ref_stats = db.query(
        WatchListing.comparison_key,
        WatchListing.reference_number,
        WatchListing.model,
        WatchListing.special_edition,
        func.count(WatchListing.id).label('count'),
        func.avg(WatchListing.price_usd).label('avg_price'),
        func.min(WatchListing.price_usd).label('min_price'),
        func.max(WatchListing.price_usd).label('max_price')
    ).filter(
        WatchListing.comparison_key != None
    ).group_by(
        WatchListing.comparison_key,
        WatchListing.reference_number,
        WatchListing.model,
        WatchListing.special_edition
    ).having(
        and_(
            func.count(WatchListing.id) >= 2,
            # At least $1000 spread
            (func.max(WatchListing.price_usd) - func.min(WatchListing.price_usd)) > 1000
        )
    ).all()
    
    opportunities = []
    for ref in ref_stats:
        profit_potential = ref.max_price - ref.min_price
        profit_percentage = (profit_potential / ref.min_price) * 100
        
        # Get the cheapest and most expensive listings for this comparison key
        cheapest = db.query(WatchListing).filter(
            WatchListing.comparison_key == ref.comparison_key,
            WatchListing.price_usd == ref.min_price
        ).first()
        
        most_expensive = db.query(WatchListing).filter(
            WatchListing.comparison_key == ref.comparison_key,
            WatchListing.price_usd == ref.max_price
        ).first()
        
        opportunities.append({
            "comparison_key": ref.comparison_key,
            "reference": ref.reference_number,
            "model": ref.model,
            "special_edition": ref.special_edition,
            "buy_price": round(ref.min_price),
            "sell_price": round(ref.max_price),
            "profit_potential": round(profit_potential),
            "profit_percentage": round(profit_percentage, 1),
            "buy_url": cheapest.url if cheapest else None,
            "sell_comp_url": most_expensive.url if most_expensive else None,
            "listings_count": ref.count
        })
    
    # Sort by profit potential
    opportunities.sort(key=lambda x: x['profit_potential'], reverse=True)
    return opportunities[:20]  # Top 20 opportunities

@app.get("/api/reference/{reference_number}")
def get_reference_details(reference_number: str, db: Session = Depends(get_db)):
    """Get detailed analysis for a specific reference number"""
    
    listings = db.query(WatchListing).filter(
        WatchListing.reference_number == reference_number
    ).order_by(WatchListing.price_usd).all()
    
    if not listings:
        return {"error": "Reference not found"}
    
    prices = [l.price_usd for l in listings]
    avg_price = sum(prices) / len(prices)
    
    # Calculate median
    sorted_prices = sorted(prices)
    n = len(sorted_prices)
    median_price = sorted_prices[n//2] if n % 2 else (sorted_prices[n//2-1] + sorted_prices[n//2]) / 2
    
    return {
        "reference": reference_number,
        "model": listings[0].model,
        "brand": listings[0].brand,
        "count": len(listings),
        "avg_price": round(avg_price),
        "median_price": round(median_price),
        "min_price": round(min(prices)),
        "max_price": round(max(prices)),
        "price_range": round(max(prices) - min(prices)),
        "listings": [
            {
                "id": l.id,
                "price": l.price_usd,
                "source": l.source,
                "url": l.url,
                "condition": l.condition,
                "material": l.material,
                "deviation_from_median": round((l.price_usd - median_price) / median_price * 100, 1)
            }
            for l in listings
        ]
    }

@app.get("/api/best-deals")
def get_best_deals(db: Session = Depends(get_db)):
    """Find watches priced below market average for their comparison key"""
    deals = []
    
    # Get average price per comparison key, only for keys with multiple listings
    ref_avgs = db.query(
        WatchListing.comparison_key,
        WatchListing.reference_number,
        WatchListing.model,
        WatchListing.special_edition,
        func.avg(WatchListing.price_usd).label('avg_price'),
        func.count(WatchListing.id).label('count'),
        func.min(WatchListing.price_usd).label('min_price'),
        func.max(WatchListing.price_usd).label('max_price')
    ).filter(
        WatchListing.comparison_key != None
    ).group_by(
        WatchListing.comparison_key,
        WatchListing.reference_number,
        WatchListing.model,
        WatchListing.special_edition
    ).having(
        func.count(WatchListing.id) >= 3  # Need at least 3 for meaningful comparison
    ).all()
    
    for comp_key, ref, model, special_edition, avg_price, count, min_price, max_price in ref_avgs:
        # Only consider it a deal if there's meaningful price variation
        if max_price - min_price < 500:  # Skip if prices are too similar
            continue
            
        # Find the cheapest watches for this comparison key
        cheapest_watches = db.query(WatchListing).filter(
            WatchListing.comparison_key == comp_key,
            WatchListing.price_usd < avg_price * 0.9  # At least 10% below average
        ).order_by(WatchListing.price_usd).limit(2).all()
        
        for watch in cheapest_watches:
            discount_percentage = round((1 - watch.price_usd/avg_price) * 100)
            discount_dollars = round(avg_price - watch.price_usd)
            
            deals.append({
                "id": watch.id,
                "model": watch.model,
                "reference": watch.reference_number,
                "comparison_key": watch.comparison_key,
                "special_edition": watch.special_edition,
                "price": watch.price_usd,
                "avg_price": round(avg_price),
                "min_price": round(min_price),
                "max_price": round(max_price),
                "discount_percentage": discount_percentage,
                "discount_dollars": discount_dollars,
                "url": watch.url,
                "source": watch.source,
                "comparable_count": count,
                "price_range": round(max_price - min_price)
            })
    
    # Sort by discount dollars (biggest savings first)
    deals.sort(key=lambda x: x['discount_dollars'], reverse=True)
    return deals[:20]  # Top 20 deals

@app.get("/api/price-history/{comparison_key}")
def get_price_history(comparison_key: str, days: int = 30, db: Session = Depends(get_db)):
    """Get price history for a specific comparison key"""
    service = PriceHistoryService(db)
    
    history_data = service.get_price_history_by_comparison_key(comparison_key, days)
    trends = service.get_market_price_trends(comparison_key, days)
    
    return {
        "comparison_key": comparison_key,
        "days": days,
        "history": history_data,
        "trends": trends
    }

@app.get("/api/price-trends")
def get_all_price_trends(min_data_points: int = 2, db: Session = Depends(get_db)):
    """Get all comparison keys with price history trends"""
    service = PriceHistoryService(db)
    return service.get_all_comparison_keys_with_history(min_data_points)

@app.get("/api/market-trends/{comparison_key}")
def get_market_trends(comparison_key: str, days: int = 30, db: Session = Depends(get_db)):
    """Get detailed market trends for a specific comparison key"""
    service = PriceHistoryService(db)
    return service.get_market_price_trends(comparison_key, days)

@app.post("/api/backfill-price-history")
def backfill_price_history(db: Session = Depends(get_db)):
    """Initialize price history from current listings (admin endpoint)"""
    service = PriceHistoryService(db)
    records_created = service.backfill_price_history()
    return {"message": f"Created {records_created} initial price history records"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)