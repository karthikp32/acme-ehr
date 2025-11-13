"""FHIR resource routes."""
from flask import Blueprint, request, jsonify
from src.services.fhir_service import FHIRService

fhir_bp = Blueprint('fhir', __name__)
fhir_service = FHIRService()


@fhir_bp.route('/<resource_type>', methods=['POST'])
def create_resource(resource_type):
    """Create a new FHIR resource."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        resource_id = data.get('id') or data.get('resourceType', resource_type)
        
        resource = fhir_service.create_resource(resource_type, resource_id, data)
        
        if resource:
            return jsonify(resource.to_dict()), 201
        else:
            return jsonify({'error': 'Failed to create resource'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@fhir_bp.route('/<resource_type>/<resource_id>', methods=['GET'])
def get_resource(resource_type, resource_id):
    """Get a specific FHIR resource."""
    try:
        resource = fhir_service.get_resource_by_type_and_id(resource_type, resource_id)
        
        if resource:
            return jsonify(resource.to_dict()), 200
        else:
            return jsonify({'error': 'Resource not found'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@fhir_bp.route('/<resource_type>/<resource_id>', methods=['PUT'])
def update_resource(resource_type, resource_id):
    """Update a FHIR resource."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        resource = fhir_service.update_resource(resource_type, resource_id, data)
        
        if resource:
            return jsonify(resource.to_dict()), 200
        else:
            return jsonify({'error': 'Resource not found or update failed'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@fhir_bp.route('/<resource_type>/<resource_id>', methods=['DELETE'])
def delete_resource(resource_type, resource_id):
    """Delete a FHIR resource."""
    try:
        deleted = fhir_service.delete_resource(resource_type, resource_id)
        
        if deleted:
            return jsonify({'message': 'Resource deleted successfully'}), 200
        else:
            return jsonify({'error': 'Resource not found'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@fhir_bp.route('/<resource_type>', methods=['GET'])
def list_resources(resource_type):
    """List all resources of a specific type."""
    try:
        resources = fhir_service.get_all_resources(resource_type)
        return jsonify([resource.to_dict() for resource in resources]), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

