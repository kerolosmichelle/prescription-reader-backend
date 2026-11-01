import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Boolean, Integer, Float, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from core.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class TimestampMixin:
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

class Source(Base, TimestampMixin):
    __tablename__ = "sources"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False, unique=True)
    organization = Column(String(255))
    source_type = Column(String(50))  # api, download, manual
    base_url = Column(Text)
    jurisdiction = Column(String(10))
    license_info = Column(Text)
    update_frequency = Column(String(50))
    is_active = Column(Boolean, default=True)
    last_sync_at = Column(DateTime)
    sync_status = Column(String(50))
    metadata_json = Column(JSON)

    medicines = relationship("Medicine", back_populates="source")

class Manufacturer(Base, TimestampMixin):
    __tablename__ = "manufacturers"

    id = Column(String, primary_key=True, default=generate_uuid)
    canonical_name = Column(String(500), nullable=False)
    normalized_name = Column(String(500), index=True)
    country = Column(String(100))
    source_id = Column(String, ForeignKey("sources.id"))
    verification_status = Column(String(50), default="pending")
    last_verified_at = Column(DateTime)

    medicines = relationship("Medicine", back_populates="manufacturer")

class DosageForm(Base, TimestampMixin):
    __tablename__ = "dosage_forms"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(100), unique=True, nullable=False)
    category = Column(String(50))
    description = Column(Text)

    medicines = relationship("Medicine", back_populates="dosage_form")

class Ingredient(Base, TimestampMixin):
    __tablename__ = "ingredients"

    id = Column(String, primary_key=True, default=generate_uuid)
    canonical_name = Column(String(500), nullable=False)
    normalized_name = Column(String(500), unique=True, index=True)
    synonyms = Column(JSON)
    rxcui = Column(String(50), index=True)
    unii = Column(String(50))
    ingredient_type = Column(String(50))
    verification_status = Column(String(50), default="pending")
    last_verified_at = Column(DateTime)
    source_id = Column(String, ForeignKey("sources.id"))
    source_references = Column(JSON)

    product_ingredients = relationship("ProductIngredient", back_populates="ingredient")
    interactions_as1 = relationship("Interaction", foreign_keys="Interaction.ingredient_id_1", back_populates="ingredient1")
    interactions_as2 = relationship("Interaction", foreign_keys="Interaction.ingredient_id_2", back_populates="ingredient2")

class Medicine(Base, TimestampMixin):
    __tablename__ = "medicines"

    id = Column(String, primary_key=True, default=generate_uuid)
    canonical_product_name = Column(String(1000), nullable=False)
    brand_name = Column(String(500), index=True)
    generic_display_name = Column(String(500))
    rxcui = Column(String(50), index=True)
    ndc = Column(String(50))
    prescription_status = Column(String(50))
    product_type = Column(String(50))
    strength_display = Column(String(255))
    package_description = Column(Text)
    route = Column(String(100))
    release_mechanism = Column(String(100))
    market_country = Column(String(10))
    marketing_authorization_number = Column(String(100))
    approval_status = Column(String(50))
    discontinuation_status = Column(String(50), default="active")
    official_product_information_url = Column(Text)

    manufacturer_id = Column(String, ForeignKey("manufacturers.id"))
    dosage_form_id = Column(String, ForeignKey("dosage_forms.id"))
    source_id = Column(String, ForeignKey("sources.id"))

    verification_status = Column(String(50), default="pending")
    last_verified_at = Column(DateTime)
    provenance = Column(JSON)

    manufacturer = relationship("Manufacturer", back_populates="medicines")
    dosage_form = relationship("DosageForm", back_populates="medicines")
    source = relationship("Source", back_populates="medicines")
    product_ingredients = relationship("ProductIngredient", back_populates="medicine")
    classifications = relationship("MedicineClassification", back_populates="medicine")

class ProductIngredient(Base, TimestampMixin):
    __tablename__ = "product_ingredients"

    id = Column(String, primary_key=True, default=generate_uuid)
    medicine_id = Column(String, ForeignKey("medicines.id"), nullable=False)
    ingredient_id = Column(String, ForeignKey("ingredients.id"), nullable=False)
    ingredient_role = Column(String(50))
    amount = Column(Float)
    amount_unit = Column(String(50))
    denominator_quantity = Column(Float)
    denominator_unit = Column(String(50))
    concentration = Column(String(255))
    normalized_strength = Column(String(255))
    source_references = Column(JSON)

    medicine = relationship("Medicine", back_populates="product_ingredients")
    ingredient = relationship("Ingredient", back_populates="product_ingredients")

class Classification(Base, TimestampMixin):
    __tablename__ = "classifications"

    id = Column(String, primary_key=True, default=generate_uuid)
    system = Column(String(50))  # ATC, therapeutic, pharmacological
    code = Column(String(50), index=True)
    name = Column(String(500), nullable=False)
    parent_code = Column(String(50))
    level = Column(Integer)
    definition = Column(Text)
    source_id = Column(String, ForeignKey("sources.id"))

    medicines = relationship("MedicineClassification", back_populates="classification")

class MedicineClassification(Base, TimestampMixin):
    __tablename__ = "medicine_classifications"

    id = Column(String, primary_key=True, default=generate_uuid)
    medicine_id = Column(String, ForeignKey("medicines.id"), nullable=False)
    classification_id = Column(String, ForeignKey("classifications.id"), nullable=False)
    source_references = Column(JSON)
    verification_status = Column(String(50), default="pending")

    medicine = relationship("Medicine", back_populates="classifications")
    classification = relationship("Classification", back_populates="medicines")

class Interaction(Base, TimestampMixin):
    __tablename__ = "interactions"

    id = Column(String, primary_key=True, default=generate_uuid)
    ingredient_id_1 = Column(String, ForeignKey("ingredients.id"), nullable=False)
    ingredient_id_2 = Column(String, ForeignKey("ingredients.id"), nullable=False)
    interaction_type = Column(String(100))
    severity = Column(String(50))
    evidence_level = Column(String(50))
    clinical_effect = Column(Text)
    management_guidance = Column(Text)
    source_id = Column(String, ForeignKey("sources.id"))
    source_reference = Column(Text)
    jurisdiction = Column(String(10))
    last_verified_at = Column(DateTime)
    verification_status = Column(String(50), default="pending")

    ingredient1 = relationship("Ingredient", foreign_keys=[ingredient_id_1], back_populates="interactions_as1")
    ingredient2 = relationship("Ingredient", foreign_keys=[ingredient_id_2], back_populates="interactions_as2")
    source = relationship("Source")

class Prescription(Base, TimestampMixin):
    __tablename__ = "prescriptions"

    id = Column(String, primary_key=True, default=generate_uuid)
    patient_reference = Column(String(255))
    prescriber_info = Column(JSON)
    status = Column(String(50), default="draft")
    notes = Column(Text)

    items = relationship("PrescriptionItem", back_populates="prescription")
    findings = relationship("SafetyFinding", back_populates="prescription")

class PrescriptionItem(Base, TimestampMixin):
    __tablename__ = "prescription_items"

    id = Column(String, primary_key=True, default=generate_uuid)
    prescription_id = Column(String, ForeignKey("prescriptions.id"), nullable=False)
    medicine_id = Column(String, ForeignKey("medicines.id"))
    medicine_name_raw = Column(String(500))
    prescribed_dose = Column(String(100))
    dose_unit = Column(String(50))
    route = Column(String(100))
    frequency_code = Column(String(50))
    frequency_description = Column(String(255))
    duration = Column(String(100))
    quantity = Column(String(100))
    instructions = Column(Text)

    prescription = relationship("Prescription", back_populates="items")
    medicine = relationship("Medicine")

class SafetyFinding(Base, TimestampMixin):
    __tablename__ = "safety_findings"

    id = Column(String, primary_key=True, default=generate_uuid)
    prescription_id = Column(String, ForeignKey("prescriptions.id"), nullable=False)
    finding_type = Column(String(100))
    severity = Column(String(50))
    title = Column(String(500))
    description = Column(Text)
    clinical_rationale = Column(Text)
    evidence = Column(JSON)
    supporting_evidence = Column(JSON)
    source_references = Column(JSON)
    rule_id = Column(String(100))
    rule_version = Column(String(50))
    review_status = Column(String(50), default="pending")
    requires_professional_review = Column(Boolean, default=True)

    prescription = relationship("Prescription", back_populates="findings")

class IngestionJob(Base, TimestampMixin):
    __tablename__ = "ingestion_jobs"

    id = Column(String, primary_key=True, default=generate_uuid)
    source_id = Column(String, ForeignKey("sources.id"))
    job_type = Column(String(50))
    status = Column(String(50), default="pending")
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    records_processed = Column(Integer, default=0)
    records_created = Column(Integer, default=0)
    records_updated = Column(Integer, default=0)
    errors = Column(JSON)
    report = Column(JSON)

    source = relationship("Source")
