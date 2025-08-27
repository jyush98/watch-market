"""FastAPI backend for watch platform"""
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import List, Dict, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path so we can import from database module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import get_db
from database.models import WatchListing, PriceHistory
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


# ============================================================================
# Epic #007: Interactive Price Search Dashboard - API Endpoints
# ============================================================================

class SearchResult(BaseModel):
    """Response model for search results"""
    comparison_key: str
    display_name: str
    reference_number: Optional[str] = None
    model: Optional[str] = None
    brand: str
    listing_count: int
    avg_price: Optional[float] = None
    latest_price: Optional[float] = None

class PricePoint(BaseModel):
    """Individual price point in time series"""
    date: str  # ISO format date
    avg_price: float
    listing_count: int
    min_price: float
    max_price: float

class SourceListing(BaseModel):
    """Individual source listing"""
    source: str
    title: str
    price_usd: float
    url: str
    scraped_at: str

@app.get("/api/search", response_model=List[SearchResult])
def search_watches(
    q: str, 
    group_variations: bool = False, 
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    Search watches by comparison key, model, or title
    
    Args:
        q: Search query (e.g., "submariner", "1680", "tiffany")
        group_variations: If True, group by reference number (1680) 
                         If False, show all variations (1680-tiffany, 1680-standard)
        limit: Maximum number of results to return
    """
    if not q or len(q.strip()) < 1:
        return []
    
    query = q.lower().strip()
    
    if group_variations:
        # Group by reference number, show one representative per reference
        results = db.query(
            WatchListing.reference_number,
            WatchListing.brand,
            WatchListing.model,
            func.count(WatchListing.id).label('listing_count'),
            func.avg(WatchListing.price_usd).label('avg_price'),
            func.max(WatchListing.last_updated).label('latest_update')
        ).filter(
            WatchListing.is_active == True,
            WatchListing.reference_number.isnot(None),
            or_(
                WatchListing.reference_number.ilike(f'%{query}%'),
                WatchListing.model.ilike(f'%{query}%'),
                WatchListing.brand.ilike(f'%{query}%')
            )
        ).group_by(
            WatchListing.reference_number,
            WatchListing.brand,
            WatchListing.model
        ).order_by(
            func.count(WatchListing.id).desc()  # Most listings first
        ).limit(limit).all()
        
        search_results = []
        for result in results:
            # Get a representative comparison key for this reference
            sample_listing = db.query(WatchListing.comparison_key).filter(
                WatchListing.reference_number == result.reference_number,
                WatchListing.brand == result.brand,
                WatchListing.is_active == True
            ).first()
            
            display_name = f"{result.brand} {result.model} {result.reference_number}"
            
            search_results.append(SearchResult(
                comparison_key=sample_listing.comparison_key if sample_listing else f"{result.reference_number}-standard",
                display_name=display_name,
                reference_number=result.reference_number,
                model=result.model,
                brand=result.brand,
                listing_count=result.listing_count,
                avg_price=result.avg_price,
                latest_price=result.avg_price
            ))
            
    else:
        # Show all individual variations
        results = db.query(
            WatchListing.comparison_key,
            WatchListing.reference_number,
            WatchListing.brand,
            WatchListing.model,
            WatchListing.special_edition,
            func.count(WatchListing.id).label('listing_count'),
            func.avg(WatchListing.price_usd).label('avg_price'),
            func.max(WatchListing.price_usd).label('latest_price')
        ).filter(
            WatchListing.is_active == True,
            WatchListing.comparison_key.isnot(None),
            or_(
                WatchListing.comparison_key.ilike(f'%{query}%'),
                WatchListing.model.ilike(f'%{query}%'),
                WatchListing.brand.ilike(f'%{query}%'),
                WatchListing.reference_number.ilike(f'%{query}%'),
                WatchListing.special_edition.ilike(f'%{query}%')
            )
        ).group_by(
            WatchListing.comparison_key,
            WatchListing.reference_number,
            WatchListing.brand,
            WatchListing.model,
            WatchListing.special_edition
        ).order_by(
            func.count(WatchListing.id).desc()
        ).limit(limit).all()
        
        search_results = []
        for result in results:
            # Build display name with special edition info
            display_name = f"{result.brand} {result.model}"
            if result.reference_number:
                display_name += f" {result.reference_number}"
            if result.special_edition:
                display_name += f" ({result.special_edition})"
                
            search_results.append(SearchResult(
                comparison_key=result.comparison_key,
                display_name=display_name,
                reference_number=result.reference_number,
                model=result.model,
                brand=result.brand,
                listing_count=result.listing_count,
                avg_price=result.avg_price,
                latest_price=result.latest_price
            ))
    
    return search_results

@app.get("/api/price-history-enhanced")
def get_enhanced_price_history(
    comparison_key: str,
    range: str = "90d",  # 30d, 90d, 1y, all
    db: Session = Depends(get_db)
):
    """
    Enhanced price history endpoint for Epic #007 dashboard
    
    Args:
        comparison_key: The watch comparison key (e.g., "1680-tiffany")
        range: Time range - "30d", "90d", "1y", "all"
    """
    # Calculate date range
    end_date = datetime.now()
    start_date = None
    
    if range == "30d":
        start_date = end_date - timedelta(days=30)
    elif range == "90d":
        start_date = end_date - timedelta(days=90)
    elif range == "1y":
        start_date = end_date - timedelta(days=365)
    # range == "all" leaves start_date as None
    
    # Query price history aggregated by date
    query = db.query(
        func.date(WatchListing.last_updated).label('date'),
        func.avg(WatchListing.price_usd).label('avg_price'),
        func.count(WatchListing.id).label('listing_count'),
        func.min(WatchListing.price_usd).label('min_price'),
        func.max(WatchListing.price_usd).label('max_price')
    ).filter(
        WatchListing.comparison_key == comparison_key,
        WatchListing.is_active == True
    )
    
    if start_date:
        query = query.filter(WatchListing.last_updated >= start_date)
    
    results = query.group_by(
        func.date(WatchListing.last_updated)
    ).order_by('date').all()
    
    # If no direct history, try to get from price_history table
    if not results:
        history_query = db.query(
            func.date(PriceHistory.timestamp).label('date'),
            func.avg(PriceHistory.price_usd).label('avg_price'),
            func.count(PriceHistory.id).label('listing_count'),
            func.min(PriceHistory.price_usd).label('min_price'),
            func.max(PriceHistory.price_usd).label('max_price')
        ).filter(PriceHistory.comparison_key == comparison_key)
        
        if start_date:
            history_query = history_query.filter(PriceHistory.timestamp >= start_date)
            
        results = history_query.group_by(
            func.date(PriceHistory.timestamp)
        ).order_by('date').all()
    
    # Convert to response format
    price_points = []
    for result in results:
        price_points.append(PricePoint(
            date=result.date.isoformat(),
            avg_price=float(result.avg_price),
            listing_count=result.listing_count,
            min_price=float(result.min_price),
            max_price=float(result.max_price)
        ))
    
    # Get watch info for metadata
    watch_info = db.query(WatchListing).filter(
        WatchListing.comparison_key == comparison_key,
        WatchListing.is_active == True
    ).first()
    
    return {
        "comparison_key": comparison_key,
        "range": range,
        "watch_info": {
            "brand": watch_info.brand if watch_info else "Unknown",
            "model": watch_info.model if watch_info else "Unknown", 
            "reference": watch_info.reference_number if watch_info else None,
            "special_edition": watch_info.special_edition if watch_info else None
        } if watch_info else None,
        "price_history": price_points,
        "summary": {
            "total_data_points": len(price_points),
            "date_range": {
                "start": price_points[0].date if price_points else None,
                "end": price_points[-1].date if price_points else None
            },
            "price_range": {
                "min": min(p.avg_price for p in price_points) if price_points else 0,
                "max": max(p.avg_price for p in price_points) if price_points else 0,
                "current": price_points[-1].avg_price if price_points else 0
            }
        }
    }

@app.get("/api/source-listings")
def get_source_listings(
    comparison_key: str,
    date: str,  # YYYY-MM-DD format
    db: Session = Depends(get_db)
):
    """
    Get individual source listings for a specific comparison key on a specific date
    Used for modal popup showing source transparency
    
    Args:
        comparison_key: Watch comparison key
        date: Date in YYYY-MM-DD format
    """
    try:
        target_date = datetime.strptime(date, '%Y-%m-%d')
    except ValueError:
        return {"error": "Invalid date format. Use YYYY-MM-DD"}
    
    # Get listings for that specific date (with some tolerance)
    start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    # First try current listings
    listings = db.query(WatchListing).filter(
        WatchListing.comparison_key == comparison_key,
        WatchListing.last_updated.between(start_of_day, end_of_day),
        WatchListing.is_active == True
    ).order_by(WatchListing.price_usd).all()
    
    # If no current listings, try price history
    if not listings:
        price_history_records = db.query(PriceHistory).filter(
            PriceHistory.comparison_key == comparison_key,
            PriceHistory.timestamp.between(start_of_day, end_of_day)
        ).order_by(PriceHistory.price_usd).all()
        
        # Convert price history to listing format
        source_listings = []
        for record in price_history_records:
            source_listings.append(SourceListing(
                source=record.source,
                title=f"{record.brand} {record.model} {record.reference_number or ''}",
                price_usd=record.price_usd,
                url=record.url,
                scraped_at=record.timestamp.isoformat()
            ))
    else:
        # Convert current listings to response format
        source_listings = []
        for listing in listings:
            source_listings.append(SourceListing(
                source=listing.source,
                title=listing.model + (f" {listing.reference_number}" if listing.reference_number else ""),
                price_usd=listing.price_usd,
                url=listing.url,
                scraped_at=listing.last_updated.isoformat()
            ))
    
    # Calculate summary stats for this date
    if source_listings:
        prices = [listing.price_usd for listing in source_listings]
        avg_price = sum(prices) / len(prices)
        
        summary = {
            "date": date,
            "comparison_key": comparison_key,
            "listing_count": len(source_listings),
            "avg_price": round(avg_price, 2),
            "min_price": min(prices),
            "max_price": max(prices),
            "price_spread": max(prices) - min(prices)
        }
    else:
        summary = {
            "date": date,
            "comparison_key": comparison_key,
            "listing_count": 0,
            "avg_price": 0,
            "min_price": 0,
            "max_price": 0,
            "price_spread": 0
        }
    
    return {
        "summary": summary,
        "listings": source_listings
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)