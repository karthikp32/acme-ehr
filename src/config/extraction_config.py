"""Field Extraction Configuration for FHIR Resources"""

EXTRACTION_CONFIG = {
    "id": "all",
    "resourceType": "all",
    "subject": "all",
    "code": "all",
    "status": ["Observation", "Procedure", "Condition", "MedicationRequest"],
    "effectiveDateTime": ["Observation"],
    "valueQuantity": ["Observation"],
    "component": ["Observation"],
    "performedDateTime": ["Procedure"],
    "performedPeriod": ["Procedure"],
    "onsetDateTime": ["Condition"],
    "clinicalStatus": ["Condition"],
    "medicationCodeableConcept": ["MedicationRequest"],
    "dosageInstruction": ["MedicationRequest"],
    "authoredOn": ["MedicationRequest"],
}


def get_extractable_fields(resource_type):
    """Get fields to extract for a resource type"""
    return [f for f, types in EXTRACTION_CONFIG.items() 
            if types == "all" or resource_type in types]