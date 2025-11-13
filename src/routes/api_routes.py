"""API routes for FHIR data import."""
from flask import Blueprint, request, jsonify
from datetime import datetime
from collections import defaultdict
from src.config.database import init_db, FHIRResource, ImportLog
from src.config.config import Config
from src.services.parser_service import parse_jsonl_file
from src.services.validator_service import validate_resource
from src.services.extractor_service import extract_fields_from_resource, get_nested_value, extract_custom_fields

api_bp = Blueprint('api', __name__)

# Initialize database session factory
Session = init_db(Config.SQLALCHEMY_DATABASE_URI)


def get_jsonl_content():
    """
    Get JSONL content from request.
    Supports both file upload and raw body.
    """
    # Check if file was uploaded
    if 'file' in request.files:
        file = request.files['file']
        if file.filename:
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
def import_fhir_data():
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
        
        # Initialize counters and tracking
        total_lines = 0
        successful = 0
        failed = 0
        validation_errors = []
        warnings = []
        resource_type_counts = defaultdict(int)
        unique_patients = set()
        missing_optional_fields = defaultdict(list)
        
        # Create database session
        session = Session()
        
        try:
            # Parse and process each line
            for line_number, parsed_json, parse_error in parse_jsonl_file(jsonl_content):
                total_lines += 1
                
                # Handle parse errors
                if parse_error:
                    failed += 1
                    validation_errors.append({
                        'line_number': line_number,
                        'error': parse_error,
                        'type': 'parse_error'
                    })
                    continue
                
                if parsed_json is None:
                    # Empty line, skip (parser already skips these, so this shouldn't happen)
                    continue
                
                # Validate resource
                validation_errors_list = validate_resource(parsed_json, line_number)
                
                if validation_errors_list:
                    failed += 1
                    validation_errors.append({
                        'line_number': line_number,
                        'errors': validation_errors_list,
                        'type': 'validation_error'
                    })
                    continue
                
                # Extract fields
                try:
                    extracted_fields = extract_fields_from_resource(parsed_json)
                    
                    # Get resource type and ID
                    resource_type = parsed_json.get('resourceType')
                    resource_id = parsed_json.get('id', f'unknown-{line_number}')
                    
                    # Track resource type
                    resource_type_counts[resource_type] += 1
                    
                    # Track unique patients
                    subject_ref = extracted_fields.get('subject_reference')
                    if subject_ref:
                        # Extract patient ID from reference (e.g., "Patient/PT-001" -> "PT-001")
                        if '/' in subject_ref:
                            patient_id = subject_ref.split('/')[-1]
                            unique_patients.add(patient_id)
                    
                    # Check for missing optional fields and create warnings
                    resource_type_lower = resource_type.lower() if resource_type else ''
                    if resource_type_lower == 'observation':
                        if 'effectiveDateTime' not in extracted_fields:
                            missing_optional_fields[resource_type].append({
                                'line_number': line_number,
                                'field': 'effectiveDateTime',
                                'message': 'Observation missing optional field effectiveDateTime'
                            })
                    elif resource_type_lower == 'medicationrequest':
                        if 'authoredOn' not in extracted_fields:
                            missing_optional_fields[resource_type].append({
                                'line_number': line_number,
                                'field': 'authoredOn',
                                'message': 'MedicationRequest missing optional field authoredOn'
                            })
                    
                    # Save to database
                    fhir_resource = FHIRResource(
                        resource_type=resource_type,
                        subject_reference=subject_ref,
                        raw_data=parsed_json,
                        extracted_fields=extracted_fields
                    )
                    
                    session.add(fhir_resource)
                    successful += 1
                    
                except Exception as e:
                    failed += 1
                    validation_errors.append({
                        'line_number': line_number,
                        'error': f'Error processing resource: {str(e)}',
                        'type': 'processing_error'
                    })
                    continue
            
            # Commit all successful resources
            session.commit()
            
            # Prepare statistics
            statistics = {
                'resource_types': dict(resource_type_counts),
                'unique_patients': len(unique_patients),
                'unique_patient_references': list(unique_patients)[:100]  # Limit to first 100 for response size
            }
            
            # Collect all warnings
            all_warnings = []
            for resource_type, warnings_list in missing_optional_fields.items():
                all_warnings.extend(warnings_list)
            
            # Create import log
            import_log = ImportLog(
                total_lines=total_lines,
                successful=successful,
                failed=failed,
                errors=validation_errors if validation_errors else None,
                statistics=statistics
            )
            session.add(import_log)
            session.commit()
            
            # Prepare response
            response = {
                'total_lines': total_lines,
                'successful': successful,
                'failed': failed,
                'validation_errors': validation_errors,
                'statistics': statistics,
                'warnings': all_warnings,
                'import_log_id': import_log.id,
                'imported_at': import_log.imported_at.isoformat() if import_log.imported_at else None
            }
            
            status_code = 200 if failed == 0 else 207  # 207 Multi-Status if partial success
            
            return jsonify(response), status_code
            
        except Exception as e:
            session.rollback()
            return jsonify({
                'error': f'Error during import: {str(e)}',
                'total_lines': total_lines,
                'successful': successful,
                'failed': failed
            }), 500
            
        finally:
            session.close()
            
    except Exception as e:
        return jsonify({
            'error': f'Error processing request: {str(e)}'
        }), 500


def project_fields(resource_data, fields_list):
    """
    Project specific fields from resource data.
    
    Args:
        resource_data: Dictionary containing resource data (raw_data from DB)
        fields_list: List of field names to project (supports dot notation)
        
    Returns:
        Dictionary with projected fields
    """
    if not fields_list or not resource_data:
        return resource_data if not fields_list else {}
    
    if not isinstance(resource_data, dict):
        return {}
    
    projected = {}
    for field in fields_list:
        field = field.strip()
        if not field:
            continue
            
        # Try to get value using nested path (supports dot notation like "code.text")
        # get_nested_value handles both nested paths and will return None if not found
        value = get_nested_value(resource_data, field)
        
        # If nested path didn't find it, try direct access
        if value is None and field in resource_data:
            value = resource_data[field]
        
        # Include field if we found a value (even if it's None/null)
        # Check if field exists in the data structure
        if value is not None or field in resource_data:
            projected[field] = value if value is not None else resource_data.get(field)
    
    return projected


@api_bp.route('/records', methods=['GET'])
def get_records():
    """
    Get FHIR records with filtering and field projection.
    
    Query parameters:
    - resourceType: Filter by resource type (e.g., "Observation", "Condition")
    - subject: Filter by subject reference (e.g., "Patient/PT-001" or "PT-001")
    - fields: Comma-separated list of fields to project (e.g., "id,code,status,subject")
    
    Returns:
    - JSON array of records
    """
    try:
        session = Session()
        
        try:
            # Build query
            query = session.query(FHIRResource)
            
            # Filter by resourceType
            resource_type = request.args.get('resourceType')
            if resource_type:
                query = query.filter(FHIRResource.resource_type == resource_type)
            
            # Filter by subject
            subject = request.args.get('subject')
            if subject:
                # Support both full reference (Patient/PT-001) and just ID (PT-001)
                if '/' in subject:
                    query = query.filter(FHIRResource.subject_reference == subject)
                else:
                    # Match if subject_reference ends with the subject ID
                    query = query.filter(FHIRResource.subject_reference.like(f'%/{subject}'))
            
            # Execute query
            resources = query.all()
            
            # Get fields to project
            fields_param = request.args.get('fields')
            fields_list = None
            if fields_param:
                fields_list = [f.strip() for f in fields_param.split(',') if f.strip()]
            
            # Project fields and build response
            results = []
            for resource in resources:
                resource_data = resource.raw_data if resource.raw_data else {}
                
                # Project fields if specified
                if fields_list:
                    projected_data = project_fields(resource_data, fields_list)
                else:
                    # Return full resource data if no field projection
                    projected_data = resource_data.copy() if isinstance(resource_data, dict) else {}
                
                # Build result starting with projected data
                result = projected_data.copy()
                
                # Always include database ID as db_id
                result['db_id'] = resource.id
                
                # Ensure 'id' field exists - use from raw_data if available, otherwise use db_id
                if 'id' not in result:
                    # Check if id exists in original raw_data (might not be in projected_data)
                    if isinstance(resource_data, dict) and 'id' in resource_data:
                        result['id'] = resource_data['id']
                    else:
                        result['id'] = resource.id
                
                results.append(result)
            
            return jsonify(results), 200
            
        except Exception as e:
            return jsonify({
                'error': f'Error querying records: {str(e)}'
            }), 500
            
        finally:
            session.close()
            
    except Exception as e:
        return jsonify({
            'error': f'Error processing request: {str(e)}'
        }), 500


@api_bp.route('/records/<int:record_id>', methods=['GET'])
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
        session = Session()
        
        try:
            # Query for the record
            resource = session.query(FHIRResource).filter(FHIRResource.id == record_id).first()
            
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
            
            # Always include database ID as db_id
            result['db_id'] = resource.id
            
            # If no field projection, include additional metadata
            if not fields_list:
                result['resource_type'] = resource.resource_type
                if resource.subject_reference:
                    result['subject_reference'] = resource.subject_reference
                if resource.imported_at:
                    result['imported_at'] = resource.imported_at.isoformat()
            
            # Ensure 'id' field exists - use from raw_data if available, otherwise use db_id
            if 'id' not in result:
                if isinstance(resource_data, dict) and 'id' in resource_data:
                    result['id'] = resource_data['id']
                else:
                    result['id'] = resource.id
            
            return jsonify(result), 200
            
        except Exception as e:
            return jsonify({
                'error': f'Error querying record: {str(e)}'
            }), 500
            
        finally:
            session.close()
            
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