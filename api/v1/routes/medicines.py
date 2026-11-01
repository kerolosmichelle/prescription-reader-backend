from flask import Blueprint, request, jsonify
from sqlalchemy import or_
from core.database import SessionLocal
from models.medicine import Medicine, Ingredient

api_v1 = Blueprint('api_v1', __name__, url_prefix='/api/v1')

@api_v1.route('/health', methods=['GET'])
def health():
    db = SessionLocal()
    try:
        med_count = db.query(Medicine).count()
        ing_count = db.query(Ingredient).count()
        return jsonify({
            "status": "ok",
            "version": "1.0.0",
            "database": {"medicines": med_count, "ingredients": ing_count}
        })
    finally:
        db.close()

@api_v1.route('/medicines', methods=['GET'])
def list_medicines():
    db = SessionLocal()
    try:
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 20)), 100)
        search = request.args.get('search', '').strip()
        query = db.query(Medicine)
        if search:
            query = query.filter(or_(Medicine.canonical_product_name.ilike(f'%{search}%'), Medicine.brand_name.ilike(f'%{search}%')))
        total = query.count()
        medicines = query.offset((page-1)*per_page).limit(per_page).all()
        results = [{"id": m.id, "canonical_product_name": m.canonical_product_name, "brand_name": m.brand_name, "rxcui": m.rxcui, "product_type": m.product_type, "verification_status": m.verification_status} for m in medicines]
        return jsonify({"data": results, "pagination": {"page": page, "per_page": per_page, "total": total, "pages": (total+per_page-1)//per_page}})
    finally:
        db.close()

@api_v1.route('/medicines/<medicine_id>', methods=['GET'])
def get_medicine(medicine_id):
    db = SessionLocal()
    try:
        med = db.query(Medicine).filter(Medicine.id == medicine_id).first()
        if not med:
            return jsonify({"error": "Medicine not found"}), 404
        ingredients = []
        for pi in med.product_ingredients:
            ingredients.append({"ingredient": pi.ingredient.canonical_name if pi.ingredient else None, "rxcui": pi.ingredient.rxcui if pi.ingredient else None})
        return jsonify({"id": med.id, "canonical_product_name": med.canonical_product_name, "brand_name": med.brand_name, "rxcui": med.rxcui, "product_type": med.product_type, "verification_status": med.verification_status, "provenance": med.provenance, "ingredients": ingredients})
    finally:
        db.close()

@api_v1.route('/ingredients', methods=['GET'])
def list_ingredients():
    db = SessionLocal()
    try:
        search = request.args.get('search', '').strip()
        query = db.query(Ingredient)
        if search:
            query = query.filter(Ingredient.canonical_name.ilike(f'%{search}%'))
        ingredients = query.limit(50).all()
        return jsonify({"data": [{"id": i.id, "canonical_name": i.canonical_name, "rxcui": i.rxcui, "verification_status": i.verification_status} for i in ingredients]})
    finally:
        db.close()
