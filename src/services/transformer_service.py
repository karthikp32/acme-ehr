"""Transformer Service for FHIR Resources"""


def flatten_field(obj, field_path):
    """
    Flatten nested object into top-level keys.
    Example: {"code": {"coding": [{"system": "x", "code": "y"}]}}
    With field="code.coding[0]" becomes {"system": "x", "code": "y"}
    """
    if not isinstance(obj, dict):
        return obj
    
    # Navigate to the field
    parts = field_path.split('.')
    current = obj
    
    for part in parts:
        if '[' in part:
            key = part.split('[')[0]
            idx = int(part.split('[')[1].rstrip(']'))
            current = current.get(key, [])[idx] if isinstance(current.get(key), list) else {}
        else:
            current = current.get(part, {})
    
    # Flatten the found object into parent
    if isinstance(current, dict):
        result = obj.copy()
        for k, v in current.items():
            result[f"{parts[0]}_{k}"] = v
        return result
    
    return obj


def extract_and_rename(obj, field_path, new_name):
    """
    Extract a nested field and rename it.
    Example: {"valueQuantity": {"value": 120}} 
    Extract "valueQuantity.value" as "value" -> {"value": 120}
    """
    from src.services.extractor_service import get_nested_value
    
    value = get_nested_value(obj, field_path)
    return {new_name: value}


def apply_transformations(resources, transformations):
    """
    Apply transformation rules to resources.
    
    Args:
        resources (list): List of resource dicts
        transformations (list): List of transformation rules
            [{"action": "flatten", "field": "code.coding[0]"},
             {"action": "extract", "field": "valueQuantity.value", "as": "value"}]
    
    Returns:
        list: Transformed resources
    """
    result = []
    
    for resource in resources:
        transformed = resource.copy()
        
        for rule in transformations:
            action = rule.get("action")
            field = rule.get("field")
            
            if action == "flatten" and field:
                transformed = flatten_field(transformed, field)
            
            elif action == "extract" and field:
                new_name = rule.get("as", field.split('.')[-1])
                extracted = extract_and_rename(transformed, field, new_name)
                transformed.update(extracted)
        
        result.append(transformed)
    
    return result


def filter_resources(resources, filters):
    """
    Filter resources by field values.
    
    Args:
        resources (list): List of resources
        filters (dict): Filter criteria {"subject": "Patient/123", ...}
    
    Returns:
        list: Filtered resources
    """
    if not filters:
        return resources
    
    filtered = []
    for resource in resources:
        match = True
        for key, value in filters.items():
            # Handle subject_reference special case
            if key == "subject" and resource.get("subject_reference") != value:
                match = False
                break
            elif resource.get(key) != value
                match = False
                break
        
        if match:
            filtered.append(resource)
    
    return filtered