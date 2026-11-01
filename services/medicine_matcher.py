import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from difflib import get_close_matches
from sqlalchemy import or_

try:
    from core.database import SessionLocal
    from models.medicine import Medicine, Ingredient
except Exception:
    SessionLocal = None
    Medicine = None
    Ingredient = None


class MedicineMatcher:
    def __init__(self, db=None):
        self.db = db or (SessionLocal() if SessionLocal else None)
        self._cache = {}

    def close(self):
        if self.db and SessionLocal:
            try:
                self.db.close()
            except Exception:
                pass

    def normalize_name(self, name):
        if not name:
            return ""
        name = name.lower()
        # Remove common suffixes
        for suffix in [' tablet', ' tablets', ' tab', ' capsule', ' cap', ' syrup', ' injection']:
            if name.endswith(suffix):
                name = name[: -len(suffix)].strip()
        return name.strip()

    def find_matches(self, name, limit=5):
        if not self.db or not Medicine or not name:
            return []
        norm = self.normalize_name(name)
        if norm in self._cache:
            return self._cache[norm]

        # Try exact/ilike matches
        query = self.db.query(Medicine)
        # Try brand name first
        results = query.filter(or_(
            Medicine.brand_name.ilike(f'%{norm}%'),
            Medicine.canonical_product_name.ilike(f'%{norm}%'),
            Medicine.generic_display_name.ilike(f'%{norm}%')
        )).limit(limit * 2).all()

        matches = []
        for med in results:
            ingredients = []
            try:
                for pi in med.product_ingredients:
                    if pi.ingredient:
                        ingredients.append(pi.ingredient.canonical_name)
            except Exception:
                pass
            matches.append({
                "id": med.id,
                "brand_name": med.brand_name,
                "canonical_product_name": med.canonical_product_name,
                "generic_display_name": med.generic_display_name,
                "rxcui": med.rxcui,
                "strength_display": med.strength_display,
                "dosage_form": med.dosage_form.name if med.dosage_form else None,
                "ingredients": ingredients,
                "verification_status": med.verification_status
            })

        # Fuzzy match if few results
        if len(matches) < limit:
            all_meds = self.db.query(Medicine).all()
            names = []
            med_map = {}
            for med in all_meds:
                for n in [med.brand_name, med.canonical_product_name, med.generic_display_name]:
                    if n:
                        key = n.lower()
                        names.append(key)
                        med_map[key] = med
            close = get_close_matches(norm, names, n=limit, cutoff=0.6)
            for c in close:
                if c in med_map:
                    med = med_map[c]
                    # avoid duplicates
                    if any(m['id'] == med.id for m in matches):
                        continue
                    ingredients = []
                    try:
                        for pi in med.product_ingredients:
                            if pi.ingredient:
                                ingredients.append(pi.ingredient.canonical_name)
                    except Exception:
                        pass
                    matches.append({
                        "id": med.id,
                        "brand_name": med.brand_name,
                        "canonical_product_name": med.canonical_product_name,
                        "generic_display_name": med.generic_display_name,
                        "rxcui": med.rxcui,
                        "strength_display": med.strength_display,
                        "dosage_form": med.dosage_form.name if med.dosage_form else None,
                        "ingredients": ingredients,
                        "verification_status": med.verification_status
                    })

        self._cache[norm] = matches[:limit]
        return matches[:limit]

    def enrich_medicines(self, medicines):
        enriched = []
        for med in medicines:
            m = dict(med)
            matches = self.find_matches(m.get('name', ''))
            m['matches'] = matches
            if matches:
                m['matched'] = True
                m['match_confidence'] = 'high' if matches else 'low'
            else:
                m['matched'] = False
                m['match_confidence'] = 'none'
            enriched.append(m)
        return enriched
