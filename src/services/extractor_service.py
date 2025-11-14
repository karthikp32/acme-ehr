"""Field Extractor Service for FHIR Resources"""

import re
from src.config.extraction_config import get_extractable_fields


def get_nested_value(data, path):
    """
    Extract value using dot notation and array indexing.
    Examples: "code.text", "component[0].valueQuantity.value"
    """
    if not data or not path:
        return None
    
    # Parse path: split by dots but handle brackets
    parts = re.split(r'\.|\[', path)
    current = data
    
    for part in parts:
        if not part or current is None:
            continue
            
        # Handle array index: "0]"
        if part.endswith(']'):
            try:
                idx = int(part[:-1])
                current = current[idx] if isinstance(current, list) and idx < len(current) else None
            except (ValueError, TypeError, IndexError):
                return None
        # Handle dict key
        elif isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    
    return current


def extract_fields_from_resource(resource):
    """
    Extract all configured fields from a FHIR resource.
    Extracts full nested structures for fields like 'code', 'subject', etc.
    """
    if not isinstance(resource, dict):
        return {}
    
    resource_type = resource.get("resourceType")
    if not resource_type:
        return {}
    
    extracted = {}
    fields_to_extract = get_extractable_fields(resource_type)
    
    for field in fields_to_extract:
        if field in resource:
            value = resource[field]
            extracted[field] = value
    
    return extracted


def extract_custom_fields(resource, field_list):
    """Extract specific fields for query projection"""
    return {field: get_nested_value(resource, field) or resource.get(field) 
            for field in field_list}


def process_resource(parsed_json, line_number):
    """
    Process a FHIR resource and extract fields, metadata, and warnings.
    
    Args:
        parsed_json: The parsed FHIR resource JSON
        line_number: Line number for tracking purposes
        
    Returns:
        dict containing extracted data.
    """
    # Extract fields based on config
    extracted_fields = extract_fields_from_resource(parsed_json)
    
    resource_type = parsed_json.get('resourceType')
    
    # Get the full subject and code objects
    subject_obj = extracted_fields.get('subject')
    code_obj = extracted_fields.get('code')
    
    # Extract patient ID and subject reference for statistics and indexing
    patient_id = None
    subject_ref = None
    if isinstance(subject_obj, dict):
        subject_ref = subject_obj.get('reference')
        if subject_ref and '/' in subject_ref:
            patient_id = subject_ref.split('/')[-1]
    
    # Check for missing optional fields and create warnings
    missing_field_warning = None
    resource_type_lower = resource_type.lower() if resource_type else ''
    if resource_type_lower == 'observation':
        if 'effectiveDateTime' not in extracted_fields:
            missing_field_warning = {
                'line_number': line_number,
                'field': 'effectiveDateTime',
                'message': 'Observation missing optional field effectiveDateTime'
            }
    elif resource_type_lower == 'medicationrequest':
        if 'authoredOn' not in extracted_fields:
            missing_field_warning = {
                'line_number': line_number,
                'field': 'authoredOn',
                'message': 'MedicationRequest missing optional field authoredOn'
            }
    
    return {
        'extracted_fields': extracted_fields,
        'resource_type': resource_type,
        'subject': subject_obj,
        'subject_reference': subject_ref,
        'code': code_obj,
        'patient_id': patient_id,
        'missing_field_warning': missing_field_warning
    }