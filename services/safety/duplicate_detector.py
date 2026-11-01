import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.database import SessionLocal
from models.medicine import Medicine, Ingredient, ProductIngredient

class DuplicateDetector:
    def __init__(self, db):
        self.db = db

    def check_prescription(self, medicine_ids):
        findings = []
        ingredient_map = {}
        for med_id in medicine_ids:
            med = self.db.query(Medicine).filter(Medicine.id == med_id).first()
            if not med:
                continue
            for pi in med.product_ingredients:
                if pi.ingredient:
                    ing_id = pi.ingredient.id
                    if ing_id not in ingredient_map:
                        ingredient_map[ing_id] = {"ingredient": pi.ingredient, "medicines": []}
                    ingredient_map[ing_id]["medicines"].append(med)

        for ing_id, data in ingredient_map.items():
            if len(data["medicines"]) > 1:
                findings.append({
                    "finding_id": f"dup-{ing_id[:8]}",
                    "type": "duplicate_ingredient",
                    "severity": "high",
                    "title": "Potential duplicate active ingredient detected",
                    "ingredient": data["ingredient"].canonical_name,
                    "ingredient_rxcui": data["ingredient"].rxcui,
                    "medicines": [{"id": m.id, "name": m.canonical_product_name, "rxcui": m.rxcui} for m in data["medicines"]],
                    "description": f"Both products contain the same active ingredient ({data['ingredient'].canonical_name}). Confirm intended regimen and total exposure with a qualified healthcare professional.",
                    "requires_professional_review": True,
                    "evidence": [{"source": "RxNav", "type": "ingredient_mapping", "verified": True}]
                })
        return findings

    def find_duplicates_across_brands(self):
        results = []
        for ing in self.db.query(Ingredient).all():
            meds = []
            for pi in ing.product_ingredients:
                if pi.medicine:
                    meds.append(pi.medicine)
            if len(meds) >= 2:
                results.append({
                    "ingredient": ing.canonical_name,
                    "ingredient_id": ing.id,
                    "rxcui": ing.rxcui,
                    "medicine_count": len(meds),
                    "medicines": [{"id": m.id, "name": m.canonical_product_name} for m in meds]
                })
        return results

def find_duplicates():
    db = SessionLocal()
    try:
        detector = DuplicateDetector(db)
        dups = detector.find_duplicates_across_brands()
        print(f"Found {len(dups)} ingredients used in multiple products")
        for d in dups[:5]:
            print(f"  {d['ingredient']}: {d['medicine_count']} products")
    finally:
        db.close()

if __name__ == "__main__":
    find_duplicates()
