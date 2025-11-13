"""Database models and initialization for FHIR data."""
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, DateTime, JSON
)
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


class FHIRResource(Base):
    __tablename__ = "fhir_resources"
    id = Column(Integer, primary_key=True)
    resource_type = Column(String, nullable=False)
    subject_reference = Column(String)
    raw_data = Column(JSON, nullable=False)
    extracted_fields = Column(JSON)
    imported_at = Column(DateTime, default=datetime.utcnow)


class ImportLog(Base):
    __tablename__ = "import_logs"
    id = Column(Integer, primary_key=True)
    imported_at = Column(DateTime, default=datetime.utcnow)
    total_lines = Column(Integer, nullable=False)
    successful = Column(Integer, nullable=False)
    failed = Column(Integer, nullable=False)
    errors = Column(JSON)
    statistics = Column(JSON)


def init_db(db_url: str = "sqlite:///fhir_data.db"):
    """Create tables and return a session factory."""
    engine = create_engine(db_url, echo=False)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)
