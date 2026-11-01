import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import SessionLocal
from models.medicine import Source

db = SessionLocal()
try:
    # Add RxNav as primary source
    rxnav = db.query(Source).filter(Source.name == "RxNav").first()
    if not rxnav:
        rxnav = Source(
            name="RxNav",
            organization="National Library of Medicine",
            source_type="api",
            base_url="https://rxnav.nlm.nih.gov/REST",
            jurisdiction="US",
            license_info="Public domain/NIH",
            update_frequency="daily",
            is_active=True
        )
        db.add(rxnav)

    openfda = db.query(Source).filter(Source.name == "openFDA").first()
    if not openfda:
        openfda = Source(
            name="openFDA",
            organization="FDA",
            source_type="api",
            base_url="https://api.fda.gov",
            jurisdiction="US",
            license_info="Public",
            update_frequency="daily",
            is_active=True
        )
        db.add(openfda)

    db.commit()
    print("Sources added successfully!")
    for s in db.query(Source).all():
        print(f"  - {s.name} ({s.jurisdiction})")
except Exception as e:
    print(f"Error: {e}")
    db.rollback()
finally:
    db.close()
