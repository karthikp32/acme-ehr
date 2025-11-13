"""Service for importing FHIR data."""
from typing import Dict, List, Any, Tuple
from collections import defaultdict
from src.services.parser_service import parse_jsonl_file
from src.services.validator_service import validate_resource
from src.services.extractor_service import process_resource
from src.services.resource_service import save_resources_batch, create_import_log


def project_fields(resource_data: Dict[str, Any], fields_list: List[str]) -> Dict[str, Any]:
    """
    Project specific fields from resource data.
    
    Args:
        resource_data: Dictionary containing resource data (raw_data from DB)
        fields_list: List of field names to project (supports dot notation)
        
    Returns:
        Dictionary with projected fields
    """
    from src.services.extractor_service import get_nested_value
    
    if not fields_list or not resource_data:
        return resource_data if not fields_list else {}
    
    if not isinstance(resource_data, dict):
        return {}
    
    projected = {}
    for field in fields_list:
        field = field.strip()
        if not field:
            continue
            
        # Try to get value using nested path (supports dot notation like "code.text")
        value = get_nested_value(resource_data, field)
        
        # If nested path didn't find it, try direct access
        if value is None and field in resource_data:
            value = resource_data[field]
        
        # Include field if we found a value (even if it's None/null)
        if value is not None or field in resource_data:
            projected[field] = value if value is not None else resource_data.get(field)
    
    return projected


def import_fhir_data(jsonl_content: str) -> Dict[str, Any]:
    """
    Import FHIR data from JSONL content.
    
    Args:
        jsonl_content: JSONL formatted string content
        
    Returns:
        Dictionary with import results including:
            - total_lines: Total lines processed
            - successful: Number of successful imports
            - failed: Number of failed imports
            - validation_errors: List of validation errors
            - statistics: Import statistics
            - warnings: List of warnings
            - import_log_id: ID of the import log entry
            - imported_at: Timestamp of import
    """
    # Initialize counters and tracking
    total_lines = 0
    successful = 0
    failed = 0
    validation_errors = []
    resource_type_counts = defaultdict(int)
    unique_patients = set()
    missing_optional_fields = defaultdict(list)
    resources_to_save = []
    
    # Parse and process each line
    for line_number, parsed_json, parse_error in parse_jsonl_file(jsonl_content):
        total_lines += 1
        
        # Handle parse errors
        if parse_error:
            failed += 1
            validation_errors.append({
                'line_number': line_number,
                'error': parse_error,
                'type': 'parse_error'
            })
            continue
        
        if parsed_json is None:
            # Empty line, skip
            continue
        
        # Validate resource
        validation_errors_list = validate_resource(parsed_json, line_number)
        
        if validation_errors_list:
            failed += 1
            validation_errors.append({
                'line_number': line_number,
                'errors': validation_errors_list,
                'type': 'validation_error'
            })
            continue
        
        # Process resource
        try:
            processed = process_resource(parsed_json, line_number)
            extracted_fields = processed['extracted_fields']
            resource_type = processed['resource_type']
            subject_ref = processed['subject_reference']
            
            # Track resource type
            resource_type_counts[resource_type] += 1
            
            # Track unique patients
            patient_id = processed['patient_id']
            if patient_id:
                unique_patients.add(patient_id)
            
            # Track missing optional fields
            if processed['missing_field_warning']:
                missing_optional_fields[resource_type].append(processed['missing_field_warning'])
            
            # Prepare resource for batch save
            resources_to_save.append({
                'resource_type': resource_type,
                'subject_reference': subject_ref,
                'raw_data': parsed_json,
                'extracted_fields': extracted_fields
            })
            
            successful += 1
            
        except Exception as e:
            failed += 1
            validation_errors.append({
                'line_number': line_number,
                'error': f'Error processing resource: {str(e)}',
                'type': 'processing_error'
            })
            continue
    
    # Save all successful resources in batch
    if resources_to_save:
        save_resources_batch(resources_to_save)
    
    # Prepare statistics
    statistics = {
        'resource_types': dict(resource_type_counts),
        'unique_patients': len(unique_patients),
        'unique_patient_references': list(unique_patients)[:100]  # Limit to first 100
    }
    
    # Collect all warnings
    all_warnings = []
    for resource_type, warnings_list in missing_optional_fields.items():
        all_warnings.extend(warnings_list)
    
    # Create import log
    import_log = create_import_log(
        total_lines=total_lines,
        successful=successful,
        failed=failed,
        errors=validation_errors if validation_errors else None,
        statistics=statistics
    )
    
    # Prepare response
    return {
        'total_lines': total_lines,
        'successful_imports': successful,
        'failed_imports': failed,
        'validation_errors': validation_errors,
        'statistics': statistics,
        'warnings': all_warnings,
        'import_log_id': import_log.id,
        'imported_at': import_log.imported_at.isoformat() if import_log.imported_at else None
    }

