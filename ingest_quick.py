import asyncio
from core.database import SessionLocal
from models.medicine import Source, Ingredient, Medicine
from services.ingestion.rxnav_client import RxNavClient
from datetime import datetime
import re

def normalize_name(name):
    if not name:
        return ""
    name = name.lower().strip()
    name = re.sub(r'[^\w\s]', ' ', name)
    name = re.sub(r'\s+', ' ', name)
    return name

async def main():
    db = SessionLocal()
    client = RxNavClient()
    source = db.query(Source).filter(Source.name == "RxNav").first()

    drugs = ["acetaminophen", "ibuprofen", "amoxicillin"]
    for drug in drugs:
        print(f"Ingesting {drug}...")
        data = await client.get_drugs(drug)
        if not data.get("drugGroup"):
            continue
        for cg in data["drugGroup"].get("conceptGroup", []):
            tty = cg.get("tty")
            if tty == "IN":
                for c in cg.get("conceptProperties", []):
                    norm = normalize_name(c["name"])
                    if not db.query(Ingredient).filter(Ingredient.normalized_name == norm).first():
                        ing = Ingredient(canonical_name=c["name"], normalized_name=norm, rxcui=c["rxcui"], ingredient_type="active", verification_status="verified", last_verified_at=datetime.utcnow(), source_id=source.id)
                        db.add(ing)
                        print(f"  Added ingredient: {c['name']}")
            elif tty in ["SBD", "SCD"]:
                for c in cg.get("conceptProperties", [])[:2]:
                    if not db.query(Medicine).filter(Medicine.rxcui == c["rxcui"]).first():
                        med = Medicine(canonical_product_name=c["name"], brand_name=c["name"], rxcui=c["rxcui"], product_type=tty, verification_status="verified", last_verified_at=datetime.utcnow(), source_id=source.id, provenance={"source":"RxNav","rxcui":c["rxcui"]})
                        db.add(med)
                        print(f"  Added medicine: {c['name'][:60]}")
        await asyncio.sleep(0.3)
    db.commit()
    print(f"Done. Ingredients: {db.query(Ingredient).count()}, Medicines: {db.query(Medicine).count()}")
    db.close()

asyncio.run(main())
