"""Automated watch market pricing engine with scheduling and alerts"""
import schedule
import time
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List
try:
    import smtplib
    from email.mime.text import MimeText
    from email.mime.multipart import MimeMultipart
    EMAIL_AVAILABLE = True
except ImportError:
    EMAIL_AVAILABLE = False
    print("Email modules not available, alerts will be logged only")
from loguru import logger
from sqlalchemy import func

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scrape_and_store import PricingEngineUpdater
from database.connection import SessionLocal
from database.models import WatchListing, PriceHistory

class AutomatedWatchMarketEngine:
    """Automated watch market pricing engine with scheduling and alerting"""
    
    def __init__(self):
        self.db = SessionLocal()
        self.alert_thresholds = {
            'large_price_change': 0.15,  # 15% change triggers alert
            'new_arbitrage_opportunity': 1000,  # $1000+ profit triggers alert
            'rare_watch_detected': ['tiffany', 'tropical', 'spider', 'comex']  # Special editions
        }
        
        # Email settings (configure as needed)
        self.email_settings = {
            'smtp_server': 'smtp.gmail.com',
            'smtp_port': 587,
            'username': os.getenv('EMAIL_USERNAME'),
            'password': os.getenv('EMAIL_PASSWORD'),
            'to_email': os.getenv('ALERT_EMAIL', 'your-email@gmail.com')
        }
    
    def run_scheduled_update(self):
        """Run full pricing update and check for alerts"""
        logger.info("🚀 Starting scheduled pricing engine update...")
        
        try:
            with PricingEngineUpdater() as updater:
                # Run comprehensive update (all 12 model categories)
                results = updater.run_full_update(max_pages=12)
                
                # Check for significant events
                self.check_for_alerts(results)
                
                # Log daily summary
                self.log_daily_summary(results)
                
                logger.success("✅ Scheduled update completed successfully")
                
        except Exception as e:
            logger.error(f"❌ Scheduled update failed: {e}")
            self.send_error_alert(str(e))
    
    def check_for_alerts(self, update_results: Dict):
        """Check for significant market events and send alerts"""
        alerts = []
        
        # Check for large price changes
        large_changes = self.find_large_price_changes()
        if large_changes:
            alerts.extend([f"📈 Large price change: {change}" for change in large_changes[:5]])
        
        # Check for new arbitrage opportunities
        new_arbitrage = self.find_significant_arbitrage()
        if new_arbitrage:
            alerts.extend([f"💰 New arbitrage opportunity: {arb}" for arb in new_arbitrage[:3]])
        
        # Check for rare watches
        rare_watches = self.find_rare_watch_alerts()
        if rare_watches:
            alerts.extend([f"💎 Rare watch detected: {watch}" for watch in rare_watches[:3]])
        
        # Send alerts if any found
        if alerts:
            self.send_market_alerts(alerts, update_results)
    
    def find_large_price_changes(self) -> List[str]:
        """Find significant price changes in last 24 hours"""
        yesterday = datetime.now() - timedelta(days=1)
        
        # Get price changes above threshold
        recent_changes = self.db.query(PriceHistory).filter(
            PriceHistory.timestamp >= yesterday,
            PriceHistory.price_change_percent != None,
            func.abs(PriceHistory.price_change_percent) >= self.alert_thresholds['large_price_change'] * 100
        ).order_by(func.abs(PriceHistory.price_change_percent).desc()).limit(5).all()
        
        changes = []
        for change in recent_changes:
            changes.append(
                f"{change.brand} {change.model} ({change.comparison_key}): "
                f"${change.previous_price:,.0f} → ${change.price_usd:,.0f} "
                f"({change.price_change_percent:+.1f}%)"
            )
        
        return changes
    
    def find_significant_arbitrage(self) -> List[str]:
        """Find new high-value arbitrage opportunities"""
        from sqlalchemy import text
        
        # Query for comparison keys with large price spreads
        query = text("""
            SELECT 
                comparison_key,
                brand,
                model,
                COUNT(*) as listings_count,
                MIN(price_usd) as min_price,
                MAX(price_usd) as max_price,
                MAX(price_usd) - MIN(price_usd) as profit_potential
            FROM watch_listings 
            WHERE comparison_key IS NOT NULL 
            GROUP BY comparison_key, brand, model
            HAVING COUNT(*) >= 2 
            AND (MAX(price_usd) - MIN(price_usd)) >= :threshold
            ORDER BY profit_potential DESC
            LIMIT 5
        """)
        
        results = self.db.execute(query, {'threshold': self.alert_thresholds['new_arbitrage_opportunity']}).fetchall()
        
        arbitrage_opportunities = []
        for row in results:
            arbitrage_opportunities.append(
                f"{row.brand} {row.model} ({row.comparison_key}): "
                f"Buy ${row.min_price:,.0f}, Sell ${row.max_price:,.0f} "
                f"= ${row.profit_potential:,.0f} profit ({row.listings_count} listings)"
            )
        
        return arbitrage_opportunities
    
    def find_rare_watch_alerts(self) -> List[str]:
        """Find newly listed rare/special edition watches"""
        yesterday = datetime.now() - timedelta(days=1)
        
        rare_watches = []
        for rare_type in self.alert_thresholds['rare_watch_detected']:
            # Find recently added rare watches
            recent_rare = self.db.query(WatchListing).filter(
                WatchListing.comparison_key.like(f'%-{rare_type}%')
            ).order_by(WatchListing.id.desc()).limit(2).all()
            
            for watch in recent_rare:
                rare_watches.append(
                    f"{watch.brand} {watch.model} {watch.special_edition} "
                    f"(Ref: {watch.reference_number}) - ${watch.price_usd:,.0f}"
                )
        
        return rare_watches
    
    def log_daily_summary(self, results: Dict):
        """Log comprehensive daily market summary"""
        total_listings = self.db.query(func.count(WatchListing.id)).scalar()
        total_history = self.db.query(func.count(PriceHistory.id)).scalar()
        
        # Average prices by model
        avg_prices = self.db.query(
            WatchListing.model,
            func.avg(WatchListing.price_usd).label('avg_price'),
            func.count(WatchListing.id).label('count')
        ).group_by(WatchListing.model).order_by(func.count(WatchListing.id).desc()).limit(5).all()
        
        logger.info("📊 DAILY MARKET SUMMARY:")
        logger.info(f"   • Total listings: {total_listings}")
        logger.info(f"   • Price history records: {total_history}")
        logger.info(f"   • New listings today: {results.get('new_listings', 0)}")
        logger.info(f"   • Price changes detected: {results.get('price_changes', 0)}")
        logger.info("   • Top models by volume:")
        
        for model_data in avg_prices:
            logger.info(f"     - {model_data.model}: {model_data.count} listings, avg ${model_data.avg_price:,.0f}")
    
    def send_market_alerts(self, alerts: List[str], results: Dict):
        """Send email alerts for significant market events"""
        if not EMAIL_AVAILABLE or not all([self.email_settings['username'], self.email_settings['to_email']]):
            logger.info("Email not available or configured, alerts will be logged only")
            for alert in alerts:
                logger.warning(f"ALERT: {alert}")
            return
        
        try:
            subject = f"Watch Market Alert - {len(alerts)} significant events detected"
            
            body = f"""
Watch Market Intelligence Alert - {datetime.now().strftime('%Y-%m-%d %H:%M')}

{len(alerts)} significant market events detected:

"""
            for alert in alerts:
                body += f"• {alert}\n"
            
            body += f"""
            
Update Summary:
• Scraped listings: {results.get('scraped_listings', 0)}
• New listings: {results.get('new_listings', 0)}
• Price changes: {results.get('price_changes', 0)}

Dashboard: http://localhost:8000/dashboard.html
"""
            
            msg = MimeMultipart()
            msg['From'] = self.email_settings['username']
            msg['To'] = self.email_settings['to_email']
            msg['Subject'] = subject
            
            msg.attach(MimeText(body, 'plain'))
            
            server = smtplib.SMTP(self.email_settings['smtp_server'], self.email_settings['smtp_port'])
            server.starttls()
            server.login(self.email_settings['username'], self.email_settings['password'])
            
            text = msg.as_string()
            server.sendmail(self.email_settings['username'], self.email_settings['to_email'], text)
            server.quit()
            
            logger.info(f"📧 Market alerts sent to {self.email_settings['to_email']}")
            
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
            # Log alerts locally as backup
            for alert in alerts:
                logger.warning(f"ALERT: {alert}")
    
    def send_error_alert(self, error_message: str):
        """Send alert when scraping fails"""
        logger.error(f"SYSTEM ERROR: {error_message}")
        
        if EMAIL_AVAILABLE and self.email_settings['username'] and self.email_settings['to_email']:
            try:
                subject = "Watch Market Engine - System Error"
                body = f"""
Watch Market Pricing Engine Error - {datetime.now().strftime('%Y-%m-%d %H:%M')}

An error occurred during the scheduled update:

{error_message}

Please check the system logs and resolve the issue.
"""
                
                msg = MimeMultipart()
                msg['From'] = self.email_settings['username']
                msg['To'] = self.email_settings['to_email']
                msg['Subject'] = subject
                msg.attach(MimeText(body, 'plain'))
                
                server = smtplib.SMTP(self.email_settings['smtp_server'], self.email_settings['smtp_port'])
                server.starttls()
                server.login(self.email_settings['username'], self.email_settings['password'])
                server.sendmail(self.email_settings['username'], self.email_settings['to_email'], msg.as_string())
                server.quit()
                
            except Exception as email_error:
                logger.error(f"Failed to send error alert: {email_error}")
    
    def setup_schedule(self):
        """Setup automated scheduling"""
        # Full update every 12 hours (6 AM and 6 PM)
        schedule.every().day.at("06:00").do(self.run_scheduled_update)
        schedule.every().day.at("18:00").do(self.run_scheduled_update)
        
        # Weekly comprehensive analysis
        schedule.every().sunday.at("07:00").do(self.run_weekly_analysis)
        
        logger.info("📅 Automated schedule configured:")
        logger.info("   • Full updates: 6:00 AM and 6:00 PM daily")
        logger.info("   • Weekly analysis: Sunday 7:00 AM")
    
    def run_quick_update(self):
        """Quick update focusing on most active models"""
        logger.info("⚡ Running quick market update...")
        
        try:
            with PricingEngineUpdater() as updater:
                # Focus on top 3 most active models
                results = updater.run_full_update(max_pages=3)
                logger.info(f"Quick update completed: {results.get('price_changes', 0)} price changes")
        except Exception as e:
            logger.error(f"Quick update failed: {e}")
    
    def run_weekly_analysis(self):
        """Run comprehensive weekly market analysis"""
        logger.info("📊 Running weekly market analysis...")
        
        # This would include trend analysis, market reports, etc.
        # For now, just run a full update
        self.run_scheduled_update()
    
    def run_scheduler(self):
        """Start the automated scheduler"""
        logger.info("🤖 Starting automated watch market pricing engine...")
        
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Automated Watch Market Pricing Engine')
    parser.add_argument('--run-once', action='store_true', help='Run update once and exit')
    parser.add_argument('--setup-schedule', action='store_true', help='Setup and run continuous scheduling')
    
    args = parser.parse_args()
    
    engine = AutomatedWatchMarketEngine()
    
    if args.run_once:
        logger.info("Running one-time update...")
        engine.run_scheduled_update()
    elif args.setup_schedule:
        engine.setup_schedule()
        engine.run_scheduler()
    else:
        logger.info("Use --run-once for single update or --setup-schedule for continuous operation")

if __name__ == "__main__":
    main()