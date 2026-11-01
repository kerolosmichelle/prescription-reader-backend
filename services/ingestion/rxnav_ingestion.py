import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from sqlalchemy.orm import Session
from core.database import SessionLocal
from models.medicine import Source, Ingredient, Medicine, ProductIngredient
from services.ingestion.rxnav_client import RxNavClient
from datetime import datetime
import re

class RxNavIngestionService:
    def __init__(self, db: Session):
        self.db = db
        self.client = RxNavClient()
        self.source = db.query(Source).filter(Source.name == "RxNav").first()

    def normalize_name(self, name: str) -> str:
        if not name:
            return ""
        name = name.lower().strip()
        name = re.sub(r'[^\w\s]', ' ', name)
        name = re.sub(r'\s+', ' ', name)
        return name

    async def ingest_ingredient(self, rxcui: str, name: str):
        normalized = self.normalize_name(name)
        existing = self.db.query(Ingredient).filter(Ingredient.normalized_name == normalized).first()
        if existing:
            return existing

        ingredient = Ingredient(
            canonical_name=name,
            normalized_name=normalized,
            rxcui=rxcui,
            ingredient_type="active",
            verification_status="verified",
            last_verified_at=datetime.utcnow(),
            source_id=self.source.id if self.source else None
        )
        self.db.add(ingredient)
        self.db.commit()
        self.db.refresh(ingredient)
        return ingredient

    async def ingest_common_drugs(self, drug_list: list):
        results = {"ingredients": 0, "medicines": 0, "mappings": 0}

        for drug_name in drug_list:
            try:
                print(f"Ingesting {drug_name}...")
                data = await self.client.get_drugs(drug_name)
                if not data.get("drugGroup"):
                    continue

                for concept_group in data["drugGroup"].get("conceptGroup", []):
                    tty = concept_group.get("tty")
                    if tty not in ["IN", "SCD", "SBD", "GPCK", "BPCK"]:
                        continue

                    for concept in concept_group.get("conceptProperties", []):
                        rxcui = concept.get("rxcui")
                        name = concept.get("name")

                        if tty == "IN":
                            await self.ingest_ingredient(rxcui, name)
                            results["ingredients"] += 1
                        elif tty in ["SCD", "SBD"]:
                            normalized = self.normalize_name(name)
                            existing = self.db.query(Medicine).filter(
                                Medicine.canonical_product_name == name
                            ).first()
                            if not existing:
                                medicine = Medicine(
                                    canonical_product_name=name,
                                    brand_name=name,
                                    rxcui=rxcui,
                                    product_type=tty,
                                    verification_status="verified",
                                    last_verified_at=datetime.utcnow(),
                                    source_id=self.source.id if self.source else None,
                                    provenance={"source": "RxNav", "rxcui": rxcui}
                                )
                                self.db.add(medicine)
                                results["medicines"] += 1

                await asyncio.sleep(0.2)  # Rate limiting
            except Exception as e:
                print(f"Error ingesting {drug_name}: {e}")
                continue

        self.db.commit()
        return results

async def main():
    db = SessionLocal()
    try:
        service = RxNavIngestionService(db)
        common_drugs = [
            "paracetamol", "acetaminophen", "ibuprofen", "amoxicillin",
            "metformin", "atorvastatin", "omeprazole", "amlodipine",
            "metoprolol", "losartan", "simvastatin", "levothyroxine"
        ]
        results = await service.ingest_common_drugs(common_drugs)
        print(f"\nIngestion complete: {results}")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())
