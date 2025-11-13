def validate_resource(resource, line_number):
    """
    Validates a single resource based on a set of rules.

    Args:
        resource: A dictionary representing the resource to validate.
        line_number: The line number of the resource in the input file.

    Returns:
        A list of validation error messages.
    """
    errors = []
    
    # Basic validation for all resources
    for field in ["id", "resourceType", "subject"]:
        if field not in resource:
            errors.append(f"Line {line_number}: Missing required field '{field}'")

    resource_type = resource.get("resourceType")

    if resource_type == "Observation":
        if "code" not in resource:
            errors.append(f"Line {line_number}: Observation missing required field 'code'")
        
        status = resource.get("status")
        if not status:
            errors.append(f"Line {line_number}: Observation missing required field 'status'")
        elif status not in ["final", "preliminary", "amended", "corrected"]:
            errors.append(f"Line {line_number}: Invalid status '{status}' for Observation")

    elif resource_type == "MedicationRequest":
        if "medicationCodeableConcept" not in resource:
            errors.append(f"Line {line_number}: MedicationRequest missing required field 'medicationCodeableConcept'")

        status = resource.get("status")
        if not status:
            errors.append(f"Line {line_number}: MedicationRequest missing required field 'status'")
        elif status not in ["active", "completed", "cancelled", "draft"]:
            errors.append(f"Line {line_number}: Invalid status '{status}' for MedicationRequest")
            
    return errors
