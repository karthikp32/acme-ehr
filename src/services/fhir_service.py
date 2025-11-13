"""FHIR data processing service."""
import json
import jsonschema
from typing import Dict, List, Optional, Tuple
from src.config.database import get_db_connection
from src.models.fhir_resource import FHIRResource


class FHIRService:
    """Service for FHIR resource operations."""
    
    def __init__(self):
        pass
    
    def validate_fhir_resource(self, resource_data: Dict) -> Tuple[bool, Optional[str]]:
        """
        Validate FHIR resource against JSON schema.
        
        Args:
            resource_data: FHIR resource data dictionary
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Basic validation - can be expanded with actual FHIR schemas
            required_fields = ['resourceType']
            for field in required_fields:
                if field not in resource_data:
                    return False, f"Missing required field: {field}"
            
            # Add more comprehensive validation here using jsonschema
            # For now, just check basic structure
            return True, None
        except Exception as e:
            return False, str(e)
    
    def create_resource(self, resource_type: str, resource_id: str, 
                       resource_data: Dict) -> Optional[FHIRResource]:
        """
        Create a new FHIR resource.
        
        Args:
            resource_type: Type of FHIR resource
            resource_id: Unique identifier for the resource
            resource_data: Resource data dictionary
            
        Returns:
            Created FHIRResource or None if creation fails
        """
        try:
            # Validate resource
            is_valid, error = self.validate_fhir_resource(resource_data)
            if not is_valid:
                raise ValueError(f"Invalid FHIR resource: {error}")
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO fhir_resources (resource_type, resource_id, resource_data)
                VALUES (?, ?, ?)
            ''', (resource_type, resource_id, json.dumps(resource_data)))
            
            conn.commit()
            resource_id_db = cursor.lastrowid
            conn.close()
            
            return self.get_resource_by_id(resource_id_db)
        except Exception as e:
            print(f"Error creating resource: {e}")
            return None
    
    def get_resource_by_id(self, id: int) -> Optional[FHIRResource]:
        """Get resource by database ID."""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM fhir_resources WHERE id = ?', (id,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return FHIRResource(
                    id=row['id'],
                    resource_type=row['resource_type'],
                    resource_id=row['resource_id'],
                    resource_data=json.loads(row['resource_data']),
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                )
            return None
        except Exception as e:
            print(f"Error getting resource: {e}")
            return None
    
    def get_resource_by_type_and_id(self, resource_type: str, resource_id: str) -> Optional[FHIRResource]:
        """Get resource by type and resource ID."""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                'SELECT * FROM fhir_resources WHERE resource_type = ? AND resource_id = ?',
                (resource_type, resource_id)
            )
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return FHIRResource(
                    id=row['id'],
                    resource_type=row['resource_type'],
                    resource_id=row['resource_id'],
                    resource_data=json.loads(row['resource_data']),
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                )
            return None
        except Exception as e:
            print(f"Error getting resource: {e}")
            return None
    
    def get_all_resources(self, resource_type: Optional[str] = None) -> List[FHIRResource]:
        """Get all resources, optionally filtered by type."""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            if resource_type:
                cursor.execute('SELECT * FROM fhir_resources WHERE resource_type = ?', (resource_type,))
            else:
                cursor.execute('SELECT * FROM fhir_resources')
            
            rows = cursor.fetchall()
            conn.close()
            
            resources = []
            for row in rows:
                resources.append(FHIRResource(
                    id=row['id'],
                    resource_type=row['resource_type'],
                    resource_id=row['resource_id'],
                    resource_data=json.loads(row['resource_data']),
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                ))
            
            return resources
        except Exception as e:
            print(f"Error getting resources: {e}")
            return []
    
    def update_resource(self, resource_type: str, resource_id: str, 
                       resource_data: Dict) -> Optional[FHIRResource]:
        """Update an existing FHIR resource."""
        try:
            # Validate resource
            is_valid, error = self.validate_fhir_resource(resource_data)
            if not is_valid:
                raise ValueError(f"Invalid FHIR resource: {error}")
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE fhir_resources
                SET resource_data = ?, updated_at = CURRENT_TIMESTAMP
                WHERE resource_type = ? AND resource_id = ?
            ''', (json.dumps(resource_data), resource_type, resource_id))
            
            conn.commit()
            conn.close()
            
            return self.get_resource_by_type_and_id(resource_type, resource_id)
        except Exception as e:
            print(f"Error updating resource: {e}")
            return None
    
    def delete_resource(self, resource_type: str, resource_id: str) -> bool:
        """Delete a FHIR resource."""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                'DELETE FROM fhir_resources WHERE resource_type = ? AND resource_id = ?',
                (resource_type, resource_id)
            )
            conn.commit()
            deleted = cursor.rowcount > 0
            conn.close()
            return deleted
        except Exception as e:
            print(f"Error deleting resource: {e}")
            return False

