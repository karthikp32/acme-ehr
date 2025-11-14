"""Flask application for FHIR data management."""
from flask import Flask, jsonify
from src.config.config import Config
from src.models.database import init_db
from src.routes.api_routes import api_bp


def create_app(config_class=Config):
    """
    Create and configure the Flask application.
    
    Args:
        config_class: Configuration class to use
        
    Returns:
        Flask application instance
    """
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize database
    init_db(app.config['SQLALCHEMY_DATABASE_URI'])
    
    # Register blueprints
    app.register_blueprint(api_bp, url_prefix='/api/v1')
    
    # Health check endpoint
    @app.route('/health', methods=['GET'])
    def health_check():
        """Health check endpoint."""
        return jsonify({'status': 'healthy'}), 200
    
    # Root endpoint
    @app.route('/', methods=['GET'])
    def root():
        """Root endpoint with API information."""
        return jsonify({
            'message': 'FHIR Data Management API',
            'version': '1.0.0',
            'endpoints': {
                'health': '/health',
                'api': '/api',
                'fhir': '/fhir'
            }
        }), 200
    
    print("--- Registered Routes ---")
    for rule in app.url_map.iter_rules():
        print(f"Endpoint: {rule.endpoint}, Methods: {','.join(rule.methods)}, URL: {rule.rule}")
    print("-------------------------")

    return app


def main():
    """Run the Flask application."""
    app = create_app()
    
    # Get host and port from environment or use defaults
    host = '0.0.0.0'
    port = 5000
    
    print(f"Starting Flask application on http://{host}:{port}")
    print(f"API endpoints available at http://{host}:{port}/api")
    print(f"FHIR endpoints available at http://{host}:{port}/fhir")
    
    app.run(host=host, port=port, debug=app.config.get('DEBUG', False))


if __name__ == "__main__":
    main()
