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
    Handles nested fields like code.text, valueQuantity.value, component[0].code
    """
    if not isinstance(resource, dict):
        return {}
    
    resource_type = resource.get("resourceType")
    if not resource_type:
        return {}
    
    extracted = {}
    fields_to_extract = get_extractable_fields(resource_type)
    
    for field in fields_to_extract:
        # Check if field exists at top level first
        if field in resource:
            # Extract the full nested structure of the field
            # This will get the entire object including nested properties
            value = resource[field]
            extracted[field] = value
        else:
            # If field doesn't exist at top level, try nested extraction
            # (for cases where field might be nested)
            value = get_nested_value(resource, field)
            if value is not None:
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
        dict containing:
            - extracted_fields: Extracted fields from the resource
            - resource_type: Resource type (e.g., 'Observation', 'MedicationRequest')
            - resource_id: Resource ID
            - patient_id: Patient ID extracted from subject reference (if available)
            - missing_field_warning: Warning dict if optional field is missing (None otherwise)
    """
    # Extract fields
    extracted_fields = extract_fields_from_resource(parsed_json)
    
    # Get resource type and ID
    resource_type = parsed_json.get('resourceType')
    resource_id = parsed_json.get('id', f'unknown-{line_number}')
    
    # Extract patient ID from subject reference
    # Get subject.reference from the nested subject structure
    patient_id = None
    subject_ref = None
    
    # Get subject reference from nested subject field
    subject = extracted_fields.get('subject')
    if isinstance(subject, dict):
        subject_ref = subject.get('reference')
    else:
        # Fallback: try to get it directly using nested path from parsed_json
        subject_ref = get_nested_value(parsed_json, 'subject.reference')
    
    # Extract patient ID from reference (e.g., "Patient/PT-001" -> "PT-001")
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
        'resource_id': resource_id,
        'patient_id': patient_id,
        'subject_reference': subject_ref,
        'missing_field_warning': missing_field_warning
    }