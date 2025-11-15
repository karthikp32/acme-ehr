"""Export Service for FHIR Resources"""

import csv
import io
from typing import List, Dict, Any
import json


def records_to_csv(records: List[Dict]) -> str:
    """
    Convert list of records to CSV format.
    
    Args:
        records: List of record dictionaries
    
    Returns:
        str: CSV formatted string
    """
    if not records:
        return ""
    
    # Get all unique field names from all records
    all_fields = set()
    for record in records:
        all_fields.update(record.keys())
    
    # Order fields: common ones first, then alphabetical
    priority_fields = ['id', 'resourceType', 'status', 'subject_reference', 
                       'subject_display', 'effectiveDateTime']
    
    ordered_fields = [f for f in priority_fields if f in all_fields]
    remaining_fields = sorted(all_fields - set(ordered_fields))
    ordered_fields.extend(remaining_fields)
    
    # Flatten records for CSV
    flattened = [flatten_for_csv(record, ordered_fields) for record in records]
    
    # Generate CSV
    return generate_csv_string(flattened, ordered_fields)


def flatten_for_csv(record: Dict, fields: List[str]) -> Dict[str, str]:
    """
    Flatten record values to strings for CSV export.
    Converts nested objects/arrays to JSON strings.
    """
    flattened = {}
    
    for field in fields:
        value = record.get(field)
        
        if value is None:
            flattened[field] = ''
        elif isinstance(value, (dict, list)):
            # Convert complex types to JSON string
            flattened[field] = json.dumps(value)
        else:
            flattened[field] = str(value)
    
    return flattened


def generate_csv_string(records: List[Dict], fields: List[str]) -> str:
    """Generate CSV string from flattened records."""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction='ignore')
    
    writer.writeheader()
    writer.writerows(records)
    
    csv_content = output.getvalue()
    output.close()
    
    return csv_content