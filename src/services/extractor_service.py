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
    """Extract all configured fields from a FHIR resource"""
    if not isinstance(resource, dict):
        return {}
    
    resource_type = resource.get("resourceType")
    if not resource_type:
        return {}
    
    extracted = {}
    fields_to_extract = get_extractable_fields(resource_type)
    
    for field in fields_to_extract:
        value = resource.get(field) or get_nested_value(resource, field)
        
        # Special handling for subject
        if field == "subject" and isinstance(value, dict):
            extracted["subject_reference"] = value.get("reference")
            extracted["subject_display"] = value.get("display")
        
        extracted[field] = value
    
    return extracted


def extract_custom_fields(resource, field_list):
    """Extract specific fields for query projection"""
    return {field: get_nested_value(resource, field) or resource.get(field) 
            for field in field_list}