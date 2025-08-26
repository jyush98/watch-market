"""Migrate price history table to include comparison key and additional fields"""
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

def migrate_price_history_table():
    """Add new columns to price_history table"""
    DATABASE_URL = os.getenv('DATABASE_URL')
    
    if not DATABASE_URL:
        logger.error("DATABASE_URL not found in environment variables")
        return
    
    engine = create_engine(DATABASE_URL)
    
    # SQL commands to add new columns to price_history table
    migration_commands = [
        # Add new columns
        "ALTER TABLE price_history ADD COLUMN IF NOT EXISTS comparison_key VARCHAR(200);",
        "ALTER TABLE price_history ADD COLUMN IF NOT EXISTS brand VARCHAR(100);",
        "ALTER TABLE price_history ADD COLUMN IF NOT EXISTS model VARCHAR(200);",
        "ALTER TABLE price_history ADD COLUMN IF NOT EXISTS reference_number VARCHAR(100);",
        "ALTER TABLE price_history ADD COLUMN IF NOT EXISTS previous_price FLOAT;",
        "ALTER TABLE price_history ADD COLUMN IF NOT EXISTS source VARCHAR(50);",
        "ALTER TABLE price_history ADD COLUMN IF NOT EXISTS url VARCHAR(500);",
        
        # Add indexes
        "CREATE INDEX IF NOT EXISTS idx_price_history_comparison_key ON price_history(comparison_key);",
        "CREATE INDEX IF NOT EXISTS idx_price_history_brand ON price_history(brand);",
        "CREATE INDEX IF NOT EXISTS idx_price_history_comparison_key_timestamp ON price_history(comparison_key, timestamp);",
        "CREATE INDEX IF NOT EXISTS idx_price_history_brand_model_timestamp ON price_history(brand, model, timestamp);",
        "CREATE INDEX IF NOT EXISTS idx_price_history_price_usd ON price_history(price_usd);",
    ]
    
    try:
        with engine.connect() as connection:
            logger.info("Migrating price_history table...")
            
            for i, command in enumerate(migration_commands, 1):
                logger.info(f"Executing migration step {i}/{len(migration_commands)}...")
                logger.debug(f"SQL: {command}")
                
                connection.execute(text(command))
                connection.commit()
                
            logger.success("✅ Price history table migrated successfully!")
            
            # Verify columns were added
            logger.info("Verifying new columns...")
            result = connection.execute(text("""
                SELECT column_name, data_type, is_nullable 
                FROM information_schema.columns 
                WHERE table_name = 'price_history' 
                AND column_name IN ('comparison_key', 'brand', 'model', 'reference_number', 'previous_price', 'source', 'url')
                ORDER BY column_name;
            """))
            
            columns = result.fetchall()
            if len(columns) >= 7:
                logger.success("✅ Column verification successful:")
                for col in columns:
                    logger.info(f"  - {col[0]}: {col[1]} (nullable: {col[2]})")
            else:
                logger.error(f"❌ Expected at least 7 columns, found {len(columns)}")
                
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise

if __name__ == "__main__":
    migrate_price_history_table()