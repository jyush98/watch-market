"""Initialize price history from current listings"""
from database.connection import SessionLocal, init_database
from services.price_history import PriceHistoryService
from loguru import logger

def initialize_price_history():
    """Initialize price history from current listings"""
    # Make sure database is initialized
    init_database()
    
    db = SessionLocal()
    try:
        service = PriceHistoryService(db)
        records_created = service.backfill_price_history()
        logger.success(f"Successfully initialized {records_created} price history records")
        return records_created
    finally:
        db.close()

if __name__ == "__main__":
    initialize_price_history()