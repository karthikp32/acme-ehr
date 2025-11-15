"""Service for FHIR resource database operations."""
from typing import List, Optional, Dict, Any
from src.models.database import get_db_session, FHIRResource, ImportLog


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
        
        # Filter by resourceType (indexed)
        if resource_type:
            query = query.filter(FHIRResource.resource_type == resource_type)
        
        # Filter by subject_reference (indexed)
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


def get_all_resources_unfiltered() -> List[FHIRResource]:
    """Return all resources without any filtering for debugging."""
    session = get_db_session()
    try:
        return session.query(FHIRResource).all()
    finally:
        session.close()


def save_resources_batch(resources: List[Dict[str, Any]]) -> None:
    """
    Save multiple FHIR resources in a batch.
    Skips resources with IDs that already exist in the database.
    
    Args:
        resources: List of resource dictionaries with keys:
            - resource_type, subject, subject_reference, code, raw_data, extracted_fields
    """
    session = get_db_session()
    
    try:
        # Get all IDs being imported
        incoming_ids = [r['raw_data']['id'] for r in resources]
        
        # Bulk check which IDs already exist
        existing_ids = set(
            session.query(FHIRResource.id)
            .filter(FHIRResource.id.in_(incoming_ids))
            .all()
        )
        existing_ids = {id_tuple[0] for id_tuple in existing_ids}
        
        # Only insert new resources
        for resource_data in resources:
            resource_id = resource_data['raw_data']['id']
            
            if resource_id in existing_ids:
                continue  # Skip duplicates
            
            fhir_resource = FHIRResource(
                id=resource_id,
                resource_type=resource_data['resource_type'],
                subject=resource_data.get('subject'),
                subject_reference=resource_data.get('subject_reference'),
                code=resource_data.get('code'),
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
