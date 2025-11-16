"""Service for importing FHIR data."""
from typing import Dict, List, Any
from collections import defaultdict
from src.services.parser_service import parse_jsonl_file
from src.services.validator_service import validate_resource
from src.services.extractor_service import process_resource
from src.services.resource_service import save_resources_batch, create_import_log


def project_fields(resource_data: Dict[str, Any], fields_list: List[str]) -> Dict[str, Any]:
    """
    Project specific fields from resource data.
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
        value = get_nested_value(resource_data, field)
        if value is None and field in resource_data:
            value = resource_data[field]
        if value is not None or field in resource_data:
            projected[field] = value if value is not None else resource_data.get(field)
    
    return projected


def import_fhir_data(jsonl_content: str) -> Dict[str, Any]:
    """
    Import FHIR data from JSONL content.
    """
    total_lines = 0
    successful = 0
    failed = 0
    validation_errors = []
    resource_type_counts = defaultdict(int)
    unique_patients = set()
    missing_optional_fields = defaultdict(list)
    resources_to_save = []
    
    for line_number, parsed_json, parse_error in parse_jsonl_file(jsonl_content):
        total_lines += 1
        
        if parse_error:
            failed += 1
            validation_errors.append({'line_number': line_number, 'errors': [parse_error], 'type': 'parse_error'})
            continue
        
        if parsed_json is None:
            continue
        
        validation_errors_list = validate_resource(parsed_json, line_number)
    
        if validation_errors_list:
            failed += 1
            validation_errors.append({'line_number': line_number, 'errors': validation_errors_list, 'type': 'validation_error'})
            continue
        
        try:
            processed = process_resource(parsed_json, line_number)
            
            resource_type = processed['resource_type']
            if resource_type:
                resource_type_counts[resource_type] += 1
            
            patient_id = processed['patient_id']
            if patient_id:
                unique_patients.add(patient_id)
            
            if processed['missing_field_warning']:
                missing_optional_fields[resource_type].append(processed['missing_field_warning'])
            
            resources_to_save.append({
                'resource_type': resource_type,
                'subject': processed.get('subject'),
                'subject_reference': processed.get('subject_reference'),
                'code': processed.get('code'),
                'raw_data': parsed_json,
                'extracted_fields': processed['extracted_fields']
            })
            
            successful += 1
            
        except Exception as e:
            failed += 1
            validation_errors.append({'line_number': line_number, 'error': f'Error processing resource: {str(e)}', 'type': 'processing_error'})
            continue
    
    if resources_to_save:
        save_resources_batch(resources_to_save)
    
    statistics = {
        'resource_types': dict(resource_type_counts),
        'unique_patients': len(unique_patients),
        'unique_patient_references': list(unique_patients)[:100]
    }
    
    # all_warnings = [warning for warnings_list in missing_optional_fields.values() for warning in warnings_list]
    all_warnings = [error_map['errors'][0] for error_map in validation_errors if error_map['errors']]

    
    import_log = create_import_log(
        total_lines=total_lines,
        successful=successful,
        failed=failed,
        errors=validation_errors if validation_errors else None,
        statistics=statistics
    )
    
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