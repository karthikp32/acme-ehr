"""FHIR resource model."""
from datetime import datetime
from src.config.database import get_db_connection


class FHIRResource:
    """Model for FHIR resources."""
    
    def __init__(self, resource_type, resource_id, resource_data, id=None, 
                 created_at=None, updated_at=None):
        self.id = id
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.resource_data = resource_data
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            'id': self.id,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'resource_data': self.resource_data,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            'updated_at': self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at
        }
    
    @staticmethod
    def from_dict(data):
        """Create model from dictionary."""
        return FHIRResource(
            id=data.get('id'),
            resource_type=data.get('resource_type'),
            resource_id=data.get('resource_id'),
            resource_data=data.get('resource_data'),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at')
        )

