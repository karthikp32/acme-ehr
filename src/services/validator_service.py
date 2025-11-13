"""Validation service for FHIR resources."""
from src.config.validation_config import get_required_fields, get_valid_status

def validate_resource(resource, line_number):
    """
    Validates a single resource based on rules from validation_config.py.

    Args:
        resource: A dictionary representing the resource to validate.
        line_number: The line number of the resource in the input file.

    Returns:
        A list of validation error messages.
    """
    errors = []
    resource_type = resource.get("resourceType")

    if not resource_type:
        errors.append(f"Line {line_number}: Missing required field 'resourceType'")
        return errors

    # Check for required fields
    required_fields = get_required_fields(resource_type)
    for field in required_fields:
        if field not in resource:
            errors.append(f"Line {line_number}: {resource_type} missing required field '{field}'")

    # Check for valid status if applicable
    valid_statuses = get_valid_status(resource_type)
    if valid_statuses and "status" in resource:
        status = resource.get("status")
        if status not in valid_statuses:
            errors.append(f"Line {line_number}: Invalid status '{status}' for {resource_type}")

    return errors