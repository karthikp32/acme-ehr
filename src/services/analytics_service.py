"""Analytics Service for FHIR Data Quality and Statistics"""

from typing import Dict, Any, List
from collections import Counter
from src.models.database import get_db_session, FHIRResource, ImportLog
import json
# Import sqlalchemy functions at module level
from sqlalchemy import func


def get_analytics() -> Dict[str, Any]:
    """
    Get comprehensive analytics about FHIR resources and data quality.
    
    Returns:
        dict: Analytics data including counts, statistics, and quality metrics
    """
    session = get_db_session()
    try:
        # Gather all analytics
        records_by_type = get_records_by_type(session)
        unique_subjects = get_unique_subjects_count(session)
        validation_summary = get_validation_error_summary(session)
        missing_fields = get_missing_fields_statistics(session)
        
        return {
            "total_records": sum(records_by_type.values()),
            "records_by_resource_type": records_by_type,
            "unique_subjects": unique_subjects,
            "validation_errors": validation_summary,
            "missing_fields_top5": missing_fields
        }
    finally:
        session.close()


def get_records_by_type(session) -> Dict[str, int]:
    """
    Get count of records grouped by resource type.
    
    Returns:
        dict: {"Observation": 100, "Procedure": 50, ...}
    """
    results = session.query(
        FHIRResource.resource_type,
        func.count(FHIRResource.id)
    ).group_by(FHIRResource.resource_type).all()
    
    return {resource_type: count for resource_type, count in results}


def get_unique_subjects_count(session) -> int:
    """
    Get count of unique patient references.
    
    Returns:
        int: Number of unique subjects/patients
    """
    result = session.query(
        func.count(func.distinct(FHIRResource.subject_reference))
    ).filter(FHIRResource.subject_reference.isnot(None)).scalar()
    
    return result or 0


def get_validation_error_summary(session) -> Dict[str, Any]:
    """
    Get summary of validation errors from import logs.
    
    Returns:
        dict: Summary of validation errors across all imports
    """
    # Get recent import logs
    logs = session.query(ImportLog).order_by(
        ImportLog.imported_at.desc()
    ).limit(10).all()
    
    if not logs:
        return {
            "total_validation_errors": 0,
            "errors_by_type": {},
            "recent_imports": 0
        }
    
    total_errors = 0
    error_types = Counter()
    
    for log in logs:
        if log.errors:
            # Parse validation errors if stored as JSON string
            if isinstance(log.errors, str):
                errors = json.loads(log.errors)
            else:
                errors = log.errors
            
            if isinstance(errors, list):
                total_errors += len(errors)
                for error in errors:
                    if isinstance(error, dict):
                        error_type = error.get('type') or error.get('error_type') or 'unknown'
                        error_types[error_type] += 1
    
    return {
        "total_validation_errors": total_errors,
        "errors_by_type": dict(error_types),
        "recent_imports": len(logs)
    }


def get_missing_fields_statistics(session) -> List[List]:
    """
    Get top 5 most commonly missing fields across all resources.
    Custom statistic: Helps identify data quality issues.
    
    Returns:
        list: [["fieldName", count], ...] top 5 missing fields
    """
    from src.config.extraction_config import get_extractable_fields
    
    # Get all resources
    resources = session.query(FHIRResource).all()
    
    missing_counter = Counter()
    
    for resource in resources:
        resource_type = resource.resource_type
        expected_fields = get_extractable_fields(resource_type)
        
        # Parse extracted_fields
        if isinstance(resource.extracted_fields, str):
            extracted = json.loads(resource.extracted_fields)
        else:
            extracted = resource.extracted_fields or {}
        
        # Check which expected fields are missing or null
        for field in expected_fields:
            if field not in extracted or extracted.get(field) is None:
                missing_counter[field] += 1
    
    # Return top 5
    return missing_counter.most_common(5)

