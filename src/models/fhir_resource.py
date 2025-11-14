from datetime import datetime
from sqlalchemy import Column, String, JSON, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class FHIRResource(Base):
    """SQLAlchemy model for FHIR resources."""
    
    __tablename__ = "fhir_resources"

    id = Column(String, primary_key=True)  # FHIR resource ID
    resource_type = Column(String, nullable=False, index=True)
    subject_reference = Column(String, index=True)
    code = Column(JSON)
    subject = Column(JSON)
    raw_data = Column(JSON, nullable=False)
    extracted_fields = Column(JSON)
    imported_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "resource_type": self.resource_type,
            "subject_reference": self.subject_reference,
            "code": self.code,
            "subject": self.subject,
            "raw_data": self.raw_data,
            "extracted_fields": self.extracted_fields,
            "imported_at": self.imported_at.isoformat() if isinstance(self.imported_at, datetime) else self.imported_at
        }

    @staticmethod
    def from_dict(data):
        """Create model instance from dictionary."""
        return FHIRResource(
            id=data.get("id"),
            resource_type=data.get("resource_type"),
            subject_reference=data.get("subject_reference"),
            code=data.get("code"),
            subject=data.get("subject"),
            raw_data=data.get("raw_data"),
            extracted_fields=data.get("extracted_fields"),
            imported_at=data.get("imported_at") or datetime.utcnow()
        )
