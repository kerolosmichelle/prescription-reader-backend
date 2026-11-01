import asyncio
from core.database import SessionLocal
from models.medicine import Source, Ingredient, Medicine, ProductIngredient
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

async def map_ingredients():
    db = SessionLocal()
    client = RxNavClient()
    source = db.query(Source).filter(Source.name == "RxNav").first()

    medicines = db.query(Medicine).filter(Medicine.product_type.in_(["SCD", "SBD"])).all()
    print(f"Mapping ingredients for {len(medicines)} medicines...")

    for med in medicines:
        if not med.rxcui:
            continue
        try:
            print(f"Processing {med.canonical_product_name[:50]}...")
            data = await client.get_ingredients(med.rxcui)
            related = data.get("relatedGroup", {}).get("conceptGroup", [])
            for cg in related:
                if cg.get("tty") == "IN":
                    for c in cg.get("conceptProperties", []):
                        norm = normalize_name(c["name"])
                        ing = db.query(Ingredient).filter(Ingredient.normalized_name == norm).first()
                        if not ing:
                            ing = Ingredient(
                                canonical_name=c["name"],
                                normalized_name=norm,
                                rxcui=c["rxcui"],
                                ingredient_type="active",
                                verification_status="verified",
                                last_verified_at=datetime.utcnow(),
                                source_id=source.id
                            )
                            db.add(ing)
                            db.flush()

                        # Check if mapping exists
                        existing = db.query(ProductIngredient).filter_by(
                            medicine_id=med.id, ingredient_id=ing.id
                        ).first()
                        if not existing:
                            pi = ProductIngredient(
                                medicine_id=med.id,
                                ingredient_id=ing.id,
                                ingredient_role="active",
                                source_references={"source": "RxNav", "rxcui": med.rxcui}
                            )
                            db.add(pi)
                            print(f"  -> mapped {ing.canonical_name}")
            await asyncio.sleep(0.3)
        except Exception as e:
            print(f"  Error: {e}")
            continue

    db.commit()
    print(f"\nDone. Product-Ingredient mappings: {db.query(ProductIngredient).count()}")
    db.close()

asyncio.run(map_ingredients())
