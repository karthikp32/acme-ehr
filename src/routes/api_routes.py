"""API routes for FHIR data import."""
from flask import Blueprint, request, jsonify
from src.services.import_service import import_fhir_data, project_fields
from src.services.resource_service import get_fhir_resources, get_fhir_resource_by_id

api_bp = Blueprint('api', __name__)


def get_jsonl_content():
    """
    Get JSONL content from request.
    Supports both file upload and raw body.
    """

    if "file" not in request.files:
        print("No file part in request")
        return None

    file = request.files["file"]

    if file.filename == "":
        return None

    # Check if file was uploaded
    if 'file' in request.files:
        file = request.files['file']
        if file.filename != '':
            return file.read().decode('utf-8')
    
    # Check if raw JSONL in body
    if request.is_json:
        # If it's a single JSON object, convert to JSONL format
        data = request.get_json()
        if isinstance(data, dict):
            import json
            return json.dumps(data)
        elif isinstance(data, list):
            import json
            return '\n'.join(json.dumps(item) for item in data)
    
    # Try to get raw text from body
    if request.data:
        try:
            return request.data.decode('utf-8')
        except UnicodeDecodeError:
            return None
    
    return None


@api_bp.route('/import', methods=['POST'])
def import_fhir_data_route():
    """
    Import FHIR data from JSONL file or raw JSONL content.
    
    Accepts:
    - Multipart file upload: file field
    - Raw JSONL in request body
    - JSON array in request body (converted to JSONL)
    
    Returns:
    - Detailed summary with statistics and errors
    """
    try:
        # Get JSONL content
        jsonl_content = get_jsonl_content()
        if not jsonl_content:
            return jsonify({
                'error': 'No file or content provided. Please upload a file or provide JSONL content in the request body.'
            }), 400
        
        # Import data using service
        result = import_fhir_data(jsonl_content)
        
        status_code = 200 if result['failed_imports'] == 0 else 207  # 207 Multi-Status if partial success
        return jsonify(result), status_code
            
    except Exception as e:
        return jsonify({
            'error': f'Error processing request: {str(e)}'
        }), 500


@api_bp.route('/records', methods=['GET'])
def get_records():
    """
    Get FHIR records with filtering and field projection.
    
    Query parameters:
    - resourceType: Filter by resource type
    - subject: Filter by subject reference
    - fields: Comma-separated list of fields to project
    
    Returns:
    - JSON array of records
    """
    try:
        # Get filter parameters
        resource_type = request.args.get('resourceType')
        subject = request.args.get('subject')
        
        # Get resources using service
        print("Resource type: ", resource_type)
        print("Subject: ", subject)
        resources = get_fhir_resources(resource_type=resource_type, subject=subject)
        
        # Get fields to project
        fields_param = request.args.get('fields')
        fields_list = None
        if fields_param:
            fields_list = [f.strip() for f in fields_param.split(',') if f.strip()]
        
        # Project fields and build response
        results = []
        for resource in resources:
            # USE EXTRACTED_FIELDS, NOT RAW_DATA
            resource_data = resource.extracted_fields if resource.extracted_fields else {}
            
            # Project fields if specified
            if fields_list:
                projected_data = project_fields(resource_data, fields_list)
            else:
                # Return extracted fields if no field projection
                projected_data = resource_data.copy() if isinstance(resource_data, dict) else {}
            
            results.append(projected_data)
        
        return jsonify(results), 200
            
    except Exception as e:
        return jsonify({
            'error': f'Error processing request: {str(e)}'
        }), 500


@api_bp.route('/records/<string:record_id>', methods=['GET'])
def get_record(record_id):
    """
    Get a single FHIR record by ID.
    
    Path parameters:
    - record_id: Database ID of the record
    
    Query parameters:
    - fields: Comma-separated list of fields to project (optional)
    
    Returns:
    - JSON object representing the record
    - 404 if record not found
    """
    try:
        # Get resource using service
        resource = get_fhir_resource_by_id(record_id)
        
        if not resource:
            return jsonify({
                'error': f'Record with id {record_id} not found'
            }), 404
        
        # Get fields to project
        fields_param = request.args.get('fields')
        fields_list = None
        if fields_param:
            fields_list = [f.strip() for f in fields_param.split(',') if f.strip()]
        
        # Project fields if specified
        resource_data = resource.raw_data if resource.raw_data else {}
        if fields_list:
            projected_data = project_fields(resource_data, fields_list)
        else:
            # Return full resource data if no field projection
            projected_data = resource_data.copy() if isinstance(resource_data, dict) else {}
        
        # Build response starting with projected data
        result = projected_data.copy()
                
        # Ensure 'id' field exists - use from raw_data if available, otherwise use db_id
        if 'id' not in result:
            if isinstance(resource_data, dict) and 'id' in resource_data:
                result['id'] = resource_data['id']
            else:
                result['id'] = resource.id
        
        return jsonify(result), 200
            
    except Exception as e:
        return jsonify({
            'error': f'Error processing request: {str(e)}'
        }), 500

# Add these new routes from transform_analytics_routes.py
@api_bp.route('/transform', methods=['POST'])
def transform_data():
    pass

@api_bp.route('/analytics', methods=['GET'])
def get_analytics():
    pass

@api_bp.route('/debug/all_resources', methods=['GET'])
def get_all_resources_debug():
    """Return all resources in a plain-text table."""
    from src.services.resource_service import get_all_resources_unfiltered
    from flask import Response
    import json
    resources = get_all_resources_unfiltered()

    # Prepare headers
    headers = [
        "id",
        "resource_type",
        "code",
        "subject",
        "imported_at",
        "raw_data",
        "extracted_fields"
    ]

    # Convert ORM rows to table rows
    rows = []
    for r in resources:
        rows.append([
            str(r.id),
            r.resource_type,
            json.dumps(r.code, indent=2) if r.code else "",
            json.dumps(r.subject, indent=2) if r.subject else "",
            r.imported_at.isoformat() if r.imported_at else "",
            json.dumps(r.raw_data, indent=2),
            json.dumps(r.extracted_fields, indent=2) if r.extracted_fields else "",
        ])

    # Compute column widths
    col_widths = [max(len(headers[i]), max(len(row[i]) for row in rows)) for i in range(len(headers))]

    # Helper to format rows
    def fmt_row(row):
        return "| " + " | ".join(row[i].ljust(col_widths[i]) for i in range(len(row))) + " |"

    # Build table
    separator = "+-" + "-+-".join("-" * w for w in col_widths) + "-+"
    lines = [separator, fmt_row(headers), separator]
    for row in rows:
        lines.append(fmt_row(row))
    lines.append(separator)

    table_text = "\n".join(lines)
    return Response(table_text, mimetype="text/plain")