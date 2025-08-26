"""Add variation tracking columns to existing database"""
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

def add_variation_columns():
    """Add the new variation tracking columns to the database"""
    DATABASE_URL = os.getenv('DATABASE_URL')
    
    if not DATABASE_URL:
        logger.error("DATABASE_URL not found in environment variables")
        return
    
    engine = create_engine(DATABASE_URL)
    
    # SQL commands to add the new columns
    migration_commands = [
        "ALTER TABLE watch_listings ADD COLUMN IF NOT EXISTS dial_type VARCHAR(100);",
        "ALTER TABLE watch_listings ADD COLUMN IF NOT EXISTS special_edition VARCHAR(200);",
        "ALTER TABLE watch_listings ADD COLUMN IF NOT EXISTS comparison_key VARCHAR(200);",
        "CREATE INDEX IF NOT EXISTS idx_comparison_key_price ON watch_listings(comparison_key, price_usd);"
    ]
    
    try:
        with engine.connect() as connection:
            logger.info("Adding variation tracking columns to database...")
            
            for i, command in enumerate(migration_commands, 1):
                logger.info(f"Executing migration step {i}/{len(migration_commands)}...")
                logger.debug(f"SQL: {command}")
                
                connection.execute(text(command))
                connection.commit()
                
            logger.success("✅ All variation tracking columns added successfully!")
            
            # Verify columns were added
            logger.info("Verifying new columns...")
            result = connection.execute(text("""
                SELECT column_name, data_type, is_nullable 
                FROM information_schema.columns 
                WHERE table_name = 'watch_listings' 
                AND column_name IN ('dial_type', 'special_edition', 'comparison_key')
                ORDER BY column_name;
            """))
            
            columns = result.fetchall()
            if len(columns) == 3:
                logger.success("✅ Column verification successful:")
                for col in columns:
                    logger.info(f"  - {col[0]}: {col[1]} (nullable: {col[2]})")
            else:
                logger.error(f"❌ Expected 3 columns, found {len(columns)}")
                
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise

if __name__ == "__main__":
    add_variation_columns()