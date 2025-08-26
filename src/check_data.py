"""Check what data we have in the database"""
from database.connection import SessionLocal
from database.models import WatchListing
from sqlalchemy import func

db = SessionLocal()

# Check reference numbers
refs = db.query(
    WatchListing.reference_number,
    func.count(WatchListing.id).label('count')
).group_by(WatchListing.reference_number).all()

print("Reference numbers and counts:")
for ref, count in refs:
    print(f"  {ref}: {count} watches")

# Check how many have multiple listings
multi_refs = db.query(
    WatchListing.reference_number,
    func.count(WatchListing.id).label('count')
).group_by(
    WatchListing.reference_number
).having(
    func.count(WatchListing.id) >= 2
).all()

print(f"\nReferences with 2+ listings: {len(multi_refs)}")

# Check for nulls
total = db.query(WatchListing).count()
with_ref = db.query(WatchListing).filter(WatchListing.reference_number != None).count()
print(f"\nTotal watches: {total}")
print(f"With reference numbers: {with_ref}")
print(f"Without reference numbers: {total - with_ref}")

db.close()