from flask import Blueprint, request, jsonify
from sqlalchemy import or_
from core.database import SessionLocal
from models.medicine import Medicine, Ingredient
from services.safety.duplicate_detector import DuplicateDetector

safety_bp = Blueprint('safety', __name__, url_prefix='/api/v1/safety')

class DuplicateDetector:
    def __init__(self, db):
        self.db = db

    def check_prescription(self, medicine_ids):
        findings = []
        # Get all ingredients across medicines
        ingredient_map = {}
        for med_id in medicine_ids:
            med = self.db.query(Medicine).filter(Medicine.id == med_id).first()
            if not med:
                continue
            for pi in med.product_ingredients:
                if pi.ingredient:
                    ing_id = pi.ingredient.id
                    if ing_id not in ingredient_map:
                        ingredient_map[ing_id] = {
                            "ingredient": pi.ingredient,
                            "medicines": []
                        }
                    ingredient_map[ing_id]["medicines"].append(med)

        # Check for duplicates
        for ing_id, data in ingredient_map.items():
            if len(data["medicines"]) > 1:
                findings.append({
                    "type": "duplicate_ingredient",
                    "severity": "high",
                    "title": "Potential duplicate active ingredient detected",
                    "ingredient": data["ingredient"].canonical_name,
                    "ingredient_rxcui": data["ingredient"].rxcui,
                    "medicines": [{"id": m.id, "name": m.canonical_product_name} for m in data["medicines"]],
                    "description": f"Both products contain the same active ingredient ({data['ingredient'].canonical_name}). Confirm intended regimen and total exposure.",
                    "requires_professional_review": True,
                    "evidence": [{"source": "RxNav", "type": "ingredient_mapping"}]
                })

        return findings

@safety_bp.route('/check-prescription', methods=['POST'])
def check_prescription():
    data = request.get_json()
    medicine_ids = data.get('medicine_ids', [])

    if not medicine_ids:
        return jsonify({"error": "medicine_ids required"}), 400

    db = SessionLocal()
    try:
        detector = DuplicateDetector(db)
        findings = detector.check_prescription(medicine_ids)
        return jsonify({
            "findings": findings,
            "count": len(findings),
            "checked_medicines": len(medicine_ids)
        })
    finally:
        db.close()
