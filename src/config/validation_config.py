"""Validation Configuration for FHIR Resources"""

VALIDATION_RULES = {
    "all": {
        "required": ["id", "resourceType", "subject"]
    },
    "Observation": {
        "required": ["code", "status"],
        "valid_status": ["final", "preliminary", "amended", "corrected"]
    },
    "MedicationRequest": {
        "required": ["medicationCodeableConcept", "status"],
        "valid_status": ["completed", "active", "final"]
    },
    "Procedure": {
        "required": ["code", "status"],
        "valid_status": ["completed", "active", "final"]
    },
    "Condition": {
        "required": ["code"]
    }
}


def get_required_fields(resource_type):
    """Get all required fields including universal ones"""
    fields = VALIDATION_RULES["all"]["required"].copy()
    if resource_type in VALIDATION_RULES:
        fields.extend(VALIDATION_RULES[resource_type].get("required", []))
    return fields


def get_valid_status(resource_type):
    """Get valid status values for a resource type"""
    return VALIDATION_RULES.get(resource_type, {}).get("valid_status")