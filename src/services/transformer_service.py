"""Transformer Service for FHIR Resources"""

from typing import List, Dict, Any
from src.models.database import get_db_session, FHIRResource
import json


def transform_resources(resource_types: List[str], 
                       transformations: List[Dict], 
                       filters: Dict) -> Dict[str, Any]:
    """
    Fetch, filter, and transform resources.
    
    Args:
        resource_types: List of resource types to fetch
        transformations: List of transformation rules
        filters: Filter criteria
    
    Returns:
        dict: {"count": int, "data": list}
    """
    # Fetch matching records from database
    resources = fetch_resources(resource_types, filters)    
    # Apply transformations
    transformed = apply_transformations(resources, transformations)
    
    return transformed


def fetch_resources(resource_types: List[str], filters: Dict) -> List[Dict]:
    """
    Fetch resources from database with basic filtering.
    
    Args:
        resource_types: List of resource types to filter by
        filters: Filter criteria (subject, etc.)
    
    Returns:
        list: List of resource dictionaries
    """
    session = get_db_session()
    try:
        query = session.query(FHIRResource)
        
        # Filter by resource types
        if resource_types:
            query = query.filter(FHIRResource.resource_type.in_(resource_types))
        
        # Filter by subject at DB level for efficiency
        if "subject" in filters:
            query = query.filter(FHIRResource.subject_reference == filters["subject"])
        
        rows = query.all()
        
        # Convert to list of dicts
        resources = []
        for row in rows:
            resource = row.extracted_fields if row.extracted_fields else {}
            resource['id'] = row.id
            resource['resourceType'] = row.resource_type
            resources.append(resource)
        
        return resources
        
    finally:
        session.close()


def filter_resources(resources: List[Dict], filters: Dict) -> List[Dict]:
    """
    Filter resources by field values (in-memory filtering).
    
    Args:
        resources: List of resources
        filters: Filter criteria {"subject": "Patient/123", ...}
    
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
            elif resource.get(key) != value:
                match = False
                break
        
        if match:
            filtered.append(resource)
    
    return filtered


def flatten_field(obj: Dict, field_path: str) -> Dict:
    """
    Flatten nested object into top-level keys.
    
    Example:
    Input: {"code": {"coding": [{"system": "x", "code": "y"}]}}
    Field: "code.coding[0]"
    Output: {"code_system": "x", "code_code": "y"}
    """
    if not isinstance(obj, dict):
        return obj
    
    result = obj.copy()
    
    # Parse the path to get what we're flattening
    # e.g., "code.coding[0]" -> navigate to that object
    parts = field_path.split('.')
    current = obj
    parent_key = parts[0]  # The top-level key to remove (e.g., "code")
    
    # Navigate to the nested object
    for part in parts:
        if not current:
            return result
            
        if '[' in part:
            # Handle array indexing like "coding[0]"
            key = part.split('[')[0]
            idx = int(part.split('[')[1].rstrip(']'))
            current = current.get(key, [])[idx] if isinstance(current.get(key), list) and idx < len(current.get(key, [])) else None
        else:
            current = current.get(part) if isinstance(current, dict) else None
    
    # If we found a dict to flatten, add its fields with prefix
    if isinstance(current, dict):
        for k, v in current.items():
            result[f"{parent_key}_{k}"] = v
        
        # Remove the original nested structure
        if parent_key in result:
            del result[parent_key]
    
    return result


def extract_and_rename(obj: Dict, field_path: str, new_name: str) -> Dict:
    """
    Extract a nested field and rename it.
    Example: {"valueQuantity": {"value": 120}} 
    Extract "valueQuantity.value" as "value" -> {"value": 120}
    """
    from src.services.extractor_service import get_nested_value
    
    value = get_nested_value(obj, field_path)
    return {new_name: value}


def apply_transformations(resources: List[Dict], 
                         transformations: List[Dict]) -> List[Dict]:
    """
    Apply transformation rules to resources.
    Returns ONLY the transformed fields, not the entire resource.
    """
    result = []
    
    for resource in resources:
        # Start with minimal base fields
        transformed = {
            "id": resource.get("id"),
            "resourceType": resource.get("resourceType")
        }
        
        for rule in transformations:
            action = rule.get("action")
            field = rule.get("field")
            
            if action == "flatten" and field:
                # Get flattened fields from original resource
                flattened = flatten_field(resource, field)
                # Extract only the new flattened fields (those with prefix_)
                prefix = field.split('.')[0]
                for k, v in flattened.items():
                    if k.startswith(f"{prefix}_"):
                        transformed[k] = v
            
            elif action == "extract" and field:
                new_name = rule.get("as", field.split('.')[-1])
                extracted = extract_and_rename(resource, field, new_name)
                transformed.update(extracted)
        
        result.append(transformed)
    
    return result