"""Service for FHIR resource database operations."""
from typing import List, Optional, Dict, Any
from src.config.database import get_db_session, FHIRResource, ImportLog
from src.services.extractor_service import get_nested_value


def save_fhir_resource(resource_type: str, subject_reference: Optional[str], 
                       raw_data: Dict[str, Any], extracted_fields: Dict[str, Any]) -> FHIRResource:
    """
    Save a FHIR resource to the database.
    
    Args:
        resource_type: Resource type (e.g., 'Observation', 'Condition')
        subject_reference: Subject reference string
        raw_data: Raw FHIR resource data
        extracted_fields: Extracted fields from the resource
        
    Returns:
        Saved FHIRResource instance
    """
    session = get_db_session()
    try:
        fhir_resource = FHIRResource(
            resource_type=resource_type,
            subject_reference=subject_reference,
            raw_data=raw_data,
            extracted_fields=extracted_fields
        )
        session.add(fhir_resource)
        session.commit()
        session.refresh(fhir_resource)
        return fhir_resource
    finally:
        session.close()


def get_fhir_resources(resource_type: Optional[str] = None, 
                       subject: Optional[str] = None) -> List[FHIRResource]:
    """
    Get FHIR resources with optional filtering.
    
    Args:
        resource_type: Filter by resource type (e.g., "Observation", "Condition")
        subject: Filter by subject reference (e.g., "Patient/PT-001" or "PT-001")
        
    Returns:
        List of FHIRResource instances
    """
    session = get_db_session()
    try:
        query = session.query(FHIRResource)
        
        # Filter by resourceType
        if resource_type:
            query = query.filter(FHIRResource.resource_type == resource_type)
        
        # Filter by subject
        if subject:
            # Support both full reference (Patient/PT-001) and just ID (PT-001)
            if '/' in subject:
                query = query.filter(FHIRResource.subject_reference == subject)
            else:
                # Match if subject_reference ends with the subject ID
                query = query.filter(FHIRResource.subject_reference.like(f'%/{subject}'))
        
        return query.all()
    finally:
        session.close()


def get_fhir_resource_by_id(record_id: int) -> Optional[FHIRResource]:
    """
    Get a single FHIR resource by database ID.
    
    Args:
        record_id: Database ID of the record
        
    Returns:
        FHIRResource instance or None if not found
    """
    session = get_db_session()
    try:
        return session.query(FHIRResource).filter(FHIRResource.id == record_id).first()
    finally:
        session.close()


def save_resources_batch(resources: List[Dict[str, Any]]) -> None:
    """
    Save multiple FHIR resources in a batch.
    
    Args:
        resources: List of resource dictionaries with keys:
            - resource_type: Resource type
            - subject_reference: Subject reference
            - raw_data: Raw FHIR data
            - extracted_fields: Extracted fields
    """
    session = get_db_session()
    try:
        for resource_data in resources:
            fhir_resource = FHIRResource(
                resource_type=resource_data['resource_type'],
                subject_reference=resource_data.get('subject_reference'),
                raw_data=resource_data['raw_data'],
                extracted_fields=resource_data['extracted_fields']
            )
            session.add(fhir_resource)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def create_import_log(total_lines: int, successful: int, failed: int,
                     errors: Optional[List[Dict[str, Any]]], 
                     statistics: Dict[str, Any]) -> ImportLog:
    """
    Create an import log entry.
    
    Args:
        total_lines: Total number of lines processed
        successful: Number of successful imports
        failed: Number of failed imports
        errors: List of error dictionaries
        statistics: Statistics dictionary
        
    Returns:
        Created ImportLog instance
    """
    session = get_db_session()
    try:
        import_log = ImportLog(
            total_lines=total_lines,
            successful=successful,
            failed=failed,
            errors=errors if errors else None,
            statistics=statistics
        )
        session.add(import_log)
        session.commit()
        session.refresh(import_log)
        return import_log
    finally:
        session.close()

