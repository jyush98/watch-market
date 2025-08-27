# Epic #007: Interactive Price History & Search Dashboard

**Status**: ✅ COMPLETED  
**Priority**: P1 - High  
**Completed**: August 2025  
**Owner**: Full-Stack Development Team  

---

## Overview

Build an interactive price history and search dashboard that allows users to search for watches by comparison key, compare multiple watches simultaneously, and access source listing transparency - showcasing the full value of our market intelligence platform.

## Business Value

- **Primary**: Provide users with intuitive access to price history and market intelligence data
- **Secondary**: Demonstrate platform value through interactive data visualization and source transparency
- **Impact**: Transform raw data into actionable user insights, supporting premium subscription tiers

---

## Success Criteria

### User Experience
- [ ] Users can search and find watches in <3 seconds
- [ ] Price history charts load in <2 seconds
- [ ] Multi-watch comparison works smoothly with up to 5 watches
- [ ] Source listing access provides full transparency

### Technical Performance
- [ ] Search autocomplete responds within 200ms
- [ ] Chart rendering handles 365+ days of data smoothly
- [ ] Modal popups load source listings within 1 second
- [ ] Interface works on desktop screens 1024px+ width

### Data Quality
- [ ] All 352+ watch listings searchable by comparison key
- [ ] Price history accurately reflects source data
- [ ] Source attribution links to correct original listings
- [ ] Variation grouping properly consolidates reference numbers

---

## Feature Specifications

### 1. Search Interface

#### Search Bar Component
```
┌─────────────────────────────────────────┐
│ 🔍 Search watches (e.g., "Submariner")  │
│ ┌─────────────────────────────────────┐ │
│ │ 1680-tiffany - Submariner Tiffany  │ │ <- Dropdown Results
│ │ 116613-standard - Sub Date (Gold)  │ │
│ │ 126660-standard - Sea-Dweller      │ │
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

**Functionality:**
- **Simple Text Matching**: Search comparison keys and display names
- **Dropdown Results**: Show up to 10 matching results with count of listings
- **Keyboard Navigation**: Arrow keys + Enter to select
- **Empty State**: "No watches found" message when no results

#### Search Logic
```javascript
// Phase 1: Simple text search
function searchWatches(query) {
    return comparisonKeys.filter(watch => 
        watch.comparison_key.includes(query.toLowerCase()) ||
        watch.display_name.toLowerCase().includes(query.toLowerCase())
    );
}
```

### 2. Watch Selection Pills

#### Selected Watches Display
```
Selected Watches (3/5):
┌──────────────┐ ┌────────────────┐ ┌─────────────┐
│ 1680-tiffany │ │ 116613-standard│ │ + Add Watch │
│   $45,000    │ │    $28,000     │ └─────────────┘
│      ❌      │ │       ❌       │ 
└──────────────┘ └────────────────┘
    Blue Line      Red Line
```

**Functionality:**
- **Maximum 5 Watches**: Clear limit with visual indicator
- **Color Assignment**: Pre-defined palette (Blue, Red, Green, Orange, Purple)
- **Current Price Display**: Latest average price shown on pill
- **Remove Function**: X button to remove from comparison
- **Add More**: + button when under 5 watches

#### Pre-defined Color Palette
```javascript
const CHART_COLORS = [
    '#3B82F6', // Blue
    '#EF4444', // Red  
    '#10B981', // Green
    '#F59E0B', // Orange
    '#8B5CF6'  // Purple
];
```

### 3. Variation Control Toggle

#### Variation Grouping Control
```
┌─────────────────────────────────────────┐
│ ⚙️ Display Options                       │
│                                         │
│ ○ Group by Reference (1680, 116613...)  │
│ ● Show All Variations (include -tiffany)│
└─────────────────────────────────────────┘
```

**Functionality:**
- **Group by Reference**: Shows `1680-standard` representing all 1680 variations
- **Show All Variations**: Shows `1680-tiffany`, `1680-tropical`, `1680-standard` separately
- **Dynamic Search Results**: Toggle affects search dropdown results
- **State Preservation**: Remember user preference during session

### 4. Interactive Price History Chart

#### Chart Display
```
     Average Price (USD)
          ↑
   $50k   │    ╭─╮ ← 1680-tiffany (Blue)
          │   ╱   ╲
   $30k   │  ╱     ╲___  ← 116613-standard (Red)  
          │ ╱           ╲___
   $15k   │╱                ╲___
          └──────────────────────→ Time
         30d   90d   1yr   All
```

**Technical Implementation:**
- **Chart.js Library**: Multi-line time series chart
- **Time Range Selector**: 30 days, 90 days, 1 year, Since Inception
- **Interactive Points**: Hover to see exact price and date
- **Legend**: Watch names with color indicators
- **Responsive**: Adapts to container width (desktop focus)

#### Chart Configuration
```javascript
const chartConfig = {
    type: 'line',
    options: {
        responsive: true,
        interaction: {
            mode: 'index',
            intersect: false,
        },
        scales: {
            y: {
                beginAtZero: false,
                ticks: {
                    callback: function(value) {
                        return '$' + value.toLocaleString();
                    }
                }
            }
        },
        plugins: {
            tooltip: {
                callbacks: {
                    afterBody: function(context) {
                        return 'Click to see source listings';
                    }
                }
            }
        }
    }
};
```

### 5. Source Listing Modal

#### Modal Popup Design
```
┌─────────────────────────────────────────┐
│ Source Listings - 1680 Tiffany         │
│                               ✕        │
├─────────────────────────────────────────┤
│                                         │
│ Date: Jan 15, 2024                      │
│ Average Price: $45,000                  │
│                                         │
│ Individual Listings:                    │
│ ┌─────────────────────────────────────┐ │
│ │ Bob's Watches    $44,500    [View]  │ │
│ │ Watchfinder     $45,500    [View]   │ │
│ │ Crown & Caliber  $45,000    [View]  │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ ┌─────────────┐ ┌─────────────────────┐ │
│ │    Close    │ │  Download Data      │ │
│ └─────────────┘ └─────────────────────┘ │
└─────────────────────────────────────────┘
```

**Functionality:**
- **Triggered by**: Clicking chart points or watch pills
- **Content**: Date, average price, individual source listings
- **External Links**: "View" opens original dealer listing in new tab
- **Data Export**: Download price history as CSV (future enhancement)
- **ESC to Close**: Standard modal behavior

---

## Technical Architecture

### Frontend Components

#### 1. Search Component
```javascript
class WatchSearch {
    constructor(container) {
        this.container = container;
        this.results = [];
        this.selectedCallback = null;
    }
    
    async search(query) {
        const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
        this.results = await response.json();
        this.renderDropdown();
    }
    
    onWatchSelected(callback) {
        this.selectedCallback = callback;
    }
}
```

#### 2. Watch Pills Component
```javascript
class WatchPills {
    constructor(container, maxWatches = 5) {
        this.container = container;
        this.maxWatches = maxWatches;
        this.selectedWatches = [];
        this.colors = CHART_COLORS;
    }
    
    addWatch(comparisonKey, displayName) {
        if (this.selectedWatches.length >= this.maxWatches) return false;
        
        const watch = {
            comparisonKey,
            displayName,
            color: this.colors[this.selectedWatches.length],
            priceHistory: []
        };
        
        this.selectedWatches.push(watch);
        this.render();
        return true;
    }
    
    removeWatch(index) {
        this.selectedWatches.splice(index, 1);
        this.reassignColors();
        this.render();
    }
}
```

#### 3. Price Chart Component
```javascript
class PriceChart {
    constructor(canvasId) {
        this.chart = new Chart(canvasId, chartConfig);
        this.timeRange = '90d'; // Default
    }
    
    async updateChart(watches, timeRange) {
        this.timeRange = timeRange;
        const datasets = [];
        
        for (const watch of watches) {
            const priceHistory = await this.fetchPriceHistory(
                watch.comparisonKey, 
                timeRange
            );
            
            datasets.push({
                label: watch.displayName,
                data: priceHistory,
                borderColor: watch.color,
                backgroundColor: watch.color + '20', // 20% opacity
                tension: 0.1
            });
        }
        
        this.chart.data.datasets = datasets;
        this.chart.update();
    }
    
    async fetchPriceHistory(comparisonKey, timeRange) {
        const response = await fetch(
            `/api/price-history?comparison_key=${comparisonKey}&range=${timeRange}`
        );
        return await response.json();
    }
}
```

### Backend API Endpoints

#### 1. Search API
```python
@app.route('/api/search')
def search_watches():
    query = request.args.get('q', '').lower()
    group_variations = request.args.get('group_variations', 'false') == 'true'
    
    if group_variations:
        # Group by reference number (1680, 116613, etc.)
        results = search_grouped_references(query)
    else:
        # Show all variations (1680-tiffany, 1680-standard, etc.)
        results = search_all_variations(query)
    
    return jsonify(results[:10])  # Limit to 10 results

def search_all_variations(query):
    return session.query(Watch).filter(
        or_(
            Watch.comparison_key.ilike(f'%{query}%'),
            Watch.title.ilike(f'%{query}%'),
            Watch.model.ilike(f'%{query}%')
        )
    ).distinct(Watch.comparison_key).all()
```

#### 2. Price History API
```python
@app.route('/api/price-history')
def get_price_history():
    comparison_key = request.args.get('comparison_key')
    time_range = request.args.get('range', '90d')  # 30d, 90d, 1y, all
    
    # Calculate date range
    end_date = datetime.now()
    if time_range == '30d':
        start_date = end_date - timedelta(days=30)
    elif time_range == '90d':
        start_date = end_date - timedelta(days=90)
    elif time_range == '1y':
        start_date = end_date - timedelta(days=365)
    else:  # 'all'
        start_date = None
    
    # Query price history
    query = session.query(
        func.date(Watch.scraped_at).label('date'),
        func.avg(Watch.price_usd).label('avg_price'),
        func.count(Watch.id).label('listing_count')
    ).filter(
        Watch.comparison_key == comparison_key
    )
    
    if start_date:
        query = query.filter(Watch.scraped_at >= start_date)
    
    results = query.group_by(
        func.date(Watch.scraped_at)
    ).order_by('date').all()
    
    return jsonify([{
        'date': result.date.isoformat(),
        'avg_price': float(result.avg_price),
        'listing_count': result.listing_count
    } for result in results])
```

#### 3. Source Listings API
```python
@app.route('/api/source-listings')
def get_source_listings():
    comparison_key = request.args.get('comparison_key')
    date = request.args.get('date')  # YYYY-MM-DD
    
    # Get all listings for specific comparison key on specific date
    target_date = datetime.strptime(date, '%Y-%m-%d')
    start_of_day = target_date.replace(hour=0, minute=0, second=0)
    end_of_day = target_date.replace(hour=23, minute=59, second=59)
    
    listings = session.query(Watch).filter(
        Watch.comparison_key == comparison_key,
        Watch.scraped_at.between(start_of_day, end_of_day)
    ).all()
    
    return jsonify([{
        'source': listing.source,
        'title': listing.title,
        'price_usd': listing.price_usd,
        'url': listing.url,
        'scraped_at': listing.scraped_at.isoformat()
    } for listing in listings])
```

---

## Implementation Roadmap

### Phase 1: Core Search & Display (Weeks 1-2)
- [ ] Build search API endpoint with simple text matching
- [ ] Create search input component with dropdown
- [ ] Implement watch pills component with color assignment
- [ ] Add variation grouping toggle functionality
- [ ] Build price history API endpoint

### Phase 2: Chart Integration (Weeks 3-4)
- [ ] Integrate Chart.js with multi-line time series
- [ ] Implement time range selector (30d, 90d, 1y, all)
- [ ] Add interactive hover tooltips
- [ ] Connect watch pills to chart data updates
- [ ] Handle empty states and error cases

### Phase 3: Source Transparency (Weeks 5-6)
- [ ] Build source listings API endpoint
- [ ] Create modal popup component
- [ ] Implement click-to-view functionality on chart points
- [ ] Add source listing links with external navigation
- [ ] Comprehensive testing and polish

### Phase 4: Future Enhancements (Future Epics)
- [ ] Fuzzy search implementation
- [ ] React/Vue component migration
- [ ] Real-time price updates
- [ ] Mobile responsive design
- [ ] Advanced chart features (zoom, annotations)

---

## Success Metrics

### User Engagement
- [ ] **Search Usage**: 80%+ of dashboard visitors use search function
- [ ] **Multi-Watch Comparison**: 40%+ users compare 2+ watches
- [ ] **Source Link Clicks**: 20%+ users click through to source listings
- [ ] **Session Duration**: 50%+ increase in average dashboard time

### Technical Performance
- [ ] **Search Response**: <200ms average response time
- [ ] **Chart Load Time**: <2 seconds for 365 days of data
- [ ] **Modal Load**: <1 second for source listings popup
- [ ] **Zero JavaScript Errors**: Clean browser console logs

### Data Quality Verification
- [ ] **Search Coverage**: 100% of comparison keys discoverable
- [ ] **Price Accuracy**: Spot checks confirm chart matches source data
- [ ] **Link Integrity**: 100% of source links navigate correctly
- [ ] **Variation Logic**: Grouping toggle works correctly for all references

---

## Dependencies

### Prerequisites
- ✅ Epic #001: Core Platform Foundation (completed)
- ✅ Epic #002: Automated Market Monitoring (completed)
- ✅ Existing dashboard framework with TailwindCSS

### Technical Dependencies
- **Database**: Price history data with timestamps
- **API Framework**: FastAPI endpoints for search and price history
- **Frontend**: Chart.js library integration
- **CSS Framework**: TailwindCSS for consistent styling

### Data Requirements
- **Minimum Data**: 30+ days of price history for meaningful charts
- **Search Index**: All 352+ watch comparison keys indexed
- **Source Attribution**: Original listing URLs preserved
- **Time Series**: Daily price averages calculated and stored

---

## Risks & Mitigations

| Risk | Impact | Mitigation | Status |
|------|--------|------------|---------|
| Chart performance with large datasets | Medium | Implement data pagination, optimize Chart.js config | 📋 Planned |
| Search becoming slow with more data | Medium | Add database indexing, consider search service | 📋 Planned |
| User confusion with variation toggle | Low | Clear UI labels, tooltips, user testing | 📋 Planned |
| Modal popup browser compatibility | Low | Standard modal implementation, progressive enhancement | 📋 Planned |

---

## Future Enhancement Opportunities

### Advanced Search Features (Epic #008)
- **Fuzzy Search**: Handle typos and partial matches
- **Filters**: Brand, price range, year, condition filters
- **Saved Searches**: User accounts with search history
- **Smart Suggestions**: ML-powered search recommendations

### Real-Time Features (Epic #009)
- **Live Price Updates**: WebSocket connections for real-time data
- **Price Alerts**: Notify users of significant price changes
- **Market Events**: Annotate charts with market news/events
- **Trend Analysis**: Automatic trend detection and alerts

### Mobile & Advanced UI (Epic #010)
- **Responsive Design**: Mobile-first responsive implementation
- **Touch Interactions**: Swipe gestures, touch-friendly controls
- **Progressive Web App**: Offline capability, app-like experience
- **Advanced Charts**: Zoom, pan, multiple Y-axes, technical indicators

---

**Target Completion**: 6 weeks from start  
**Business Impact**: Transform raw data into actionable user insights  
**Technical Impact**: Establish foundation for advanced analytics features