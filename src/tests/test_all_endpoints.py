#!/usr/bin/env python3
"""
Comprehensive test script for Acme EHR API.
Tests all endpoints with multiple JSONL files.
"""

import requests
import json
import os
from pathlib import Path
from typing import Dict, List, Any

BASE_URL = "http://localhost:5000/api/v1"

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DATA_DIR = PROJECT_ROOT / "data"

# ANSI color codes for pretty output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def print_section(title: str):
    """Print a section header"""
    print(f"\n{'='*80}")
    print(f"{BLUE}{title}{RESET}")
    print('='*80)


def print_success(message: str):
    """Print success message"""
    print(f"{GREEN}✓ {message}{RESET}")


def print_error(message: str):
    """Print error message"""
    print(f"{RED}✗ {message}{RESET}")


def print_info(message: str):
    """Print info message"""
    print(f"{YELLOW}ℹ {message}{RESET}")


def test_import(filename: str) -> Dict[str, Any]:
    """Test POST /import endpoint"""
    filepath = DATA_DIR / filename
    
    if not filepath.exists():
        print_error(f"File not found: {filepath}")
        return None
    
    print_section(f"Testing Import: {filename}")
    
    try:
        with open(filepath, 'rb') as f:
            files = {'file': (filename, f, 'application/x-ndjson')}
            response = requests.post(f"{BASE_URL}/import", files=files)
        
        print_info(f"Status Code: {response.status_code}")
        
        if response.status_code in [200,207]:
            data = response.json()
            print_success(f"Import completed")
            print(f"  Total processed: {data.get('total_processed', 0)}")
            print(f"  Successful: {data.get('successful_imports', 0)}")
            print(f"  Failed: {data.get('failed_imports', 0)}")
            
            if data.get('validation_errors'):
                print_info(f"  Validation errors: {len(data['validation_errors'])}")
                # Show first 3 errors
                for error in data['validation_errors'][:3]:
                    print(f"    Line {error.get('line')}: {error.get('error')}")
            
            return data
        else:
            print_error(f"Import failed: {response.text}")
            return None
            
    except Exception as e:
        print_error(f"Exception during import: {str(e)}")
        return None


def test_get_records(params: Dict[str, str] = None):
    """Test GET /records endpoint"""
    print_section("Testing GET /records")
    
    try:
        response = requests.get(f"{BASE_URL}/records", params=params)
        print_info(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print_success(f"Retrieved {len(data)} records")
            
            if data and len(data) > 0:
                print_info(f"Sample record ID: {data[0].get('id')}")
                print_info(f"Sample resource type: {data[0].get('resourceType')}")
            
            return data
        else:
            print_error(f"GET /records failed: {response.text}")
            return None
            
    except Exception as e:
        print_error(f"Exception: {str(e)}")
        return None


def test_get_record_by_id(record_id: str, fields: str = None):
    """Test GET /records/:id endpoint"""
    print_section(f"Testing GET /records/{record_id}")
    
    params = {'fields': fields} if fields else None
    
    try:
        response = requests.get(f"{BASE_URL}/records/{record_id}", params=params)
        print_info(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print_success(f"Retrieved record: {data.get('id')}")
            print_info(f"Fields returned: {list(data.keys())}")
            return data
        elif response.status_code == 404:
            print_info("Record not found (expected for test)")
            return None
        else:
            print_error(f"GET /records/:id failed: {response.text}")
            return None
            
    except Exception as e:
        print_error(f"Exception: {str(e)}")
        return None


def test_transform(resource_types: List[str], subject: str = None):
    """Test POST /transform endpoint"""
    print_section("Testing POST /transform")
    
    payload = {
        "resourceTypes": resource_types,
        "transformations": [
            {"action": "flatten", "field": "code.coding[0]"},
            {"action": "extract", "field": "valueQuantity.value", "as": "value"},
            {"action": "extract", "field": "valueQuantity.unit", "as": "unit"}
        ],
        "filters": {}
    }
    
    if subject:
        payload["filters"]["subject"] = subject
    
    try:
        response = requests.post(
            f"{BASE_URL}/transform",
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        
        print_info(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            count = len(data)
            
            print_success(f"Transformed {count} records")
            
            if data and len(data) > 0:
                sample = data[0]
                print_info(f"Sample transformed fields: {list(sample.keys())}")
                if 'code_system' in sample:
                    print_success("Flatten worked: 'code_system' present")
                if 'value' in sample:
                    print_success("Extract worked: 'value' present")
            
            return data
        else:
            print_error(f"Transform failed: {response.text}")
            return None
            
    except Exception as e:
        print_error(f"Exception: {str(e)}")
        return None


def test_analytics():
    """Test GET /analytics endpoint"""
    print_section("Testing GET /analytics")
    
    try:
        response = requests.get(f"{BASE_URL}/analytics")
        print_info(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print_success("Analytics retrieved")
            print(f"  Total records: {data.get('total_records', 0)}")
            print(f"  Unique subjects: {data.get('unique_subjects', 0)}")
            
            records_by_type = data.get('records_by_type', {})
            if records_by_type:
                print_info("Records by type:")
                for rtype, count in records_by_type.items():
                    print(f"    {rtype}: {count}")
            
            missing_fields = data.get('missing_fields_top5', [])
            if missing_fields:
                print_info("Top missing fields:")
                for field, count in missing_fields[:3]:
                    print(f"    {field}: {count}")
            
            return data
        else:
            print_error(f"Analytics failed: {response.text}")
            return None
            
    except Exception as e:
        print_error(f"Exception: {str(e)}")
        return None


def test_export_csv(resource_type: str = None):
    """Test CSV export"""
    print_section("Testing CSV Export")
    
    params = {'format': 'csv'}
    if resource_type:
        params['resourceType'] = resource_type
    
    try:
        response = requests.get(f"{BASE_URL}/records", params=params)
        print_info(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', '')
            
            if 'text/csv' in content_type:
                print_success("CSV export successful")
                lines = response.text.split('\n')
                print_info(f"CSV has {len(lines)} lines")
                print_info(f"Header: {lines[0][:100]}...")
                return True
            else:
                print_error(f"Expected CSV, got: {content_type}")
                return False
        else:
            print_error(f"CSV export failed: {response.text}")
            return False
            
    except Exception as e:
        print_error(f"Exception: {str(e)}")
        return False


def test_nested_field_projection():
    """Test nested field access with dot notation and array indexing"""
    print_section("Testing Nested Field Projection")
    
    test_cases = [
        {'fields': 'id,code.text', 'description': 'Dot notation'},
        {'fields': 'id,status,subject.reference', 'description': 'Nested object'},
    ]
    
    for test in test_cases:
        print(f"\n  Testing: {test['description']}")
        params = {
            'resourceType': 'Observation',
            'fields': test['fields']
        }
        
        try:
            response = requests.get(f"{BASE_URL}/records", params=params)
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    returned_fields = list(data[0].keys())
                    print_success(f"Fields returned: {returned_fields}")
                else:
                    print_info("No records found for this test")
            else:
                print_error(f"Failed: {response.status_code}")
                
        except Exception as e:
            print_error(f"Exception: {str(e)}")


def run_all_tests():
    """Run comprehensive test suite"""
    print(f"\n{BLUE}{'='*80}")
    print("🧪 ACME EHR API - Comprehensive Test Suite")
    print(f"{'='*80}{RESET}\n")
    
    # Track test results
    results = {
        'imports': [],
        'queries': [],
        'transforms': [],
        'exports': [],
        'analytics': False
    }
    
    # Test files to import
    test_files = [
        'edge_cases.jsonl',
        'mixed_resources.jsonl',
        'minimal_valid.jsonl',
        'large_batch.jsonl',
        'duplicates.jsonl'
    ]
    
    # 1. Test imports
    print(f"\n{BLUE}Phase 1: Testing Imports{RESET}")
    for filename in test_files:
        result = test_import(filename)
        results['imports'].append({
            'file': filename,
            'success': result is not None
        })
    
    # 2. Test GET /records with various filters
    print(f"\n{BLUE}Phase 2: Testing Record Queries{RESET}")
    
    query_tests = [
        {'params': {'resourceType': 'Observation'}, 'desc': 'Filter by resource type'},
        {'params': {'subject': 'Patient/PT-100'}, 'desc': 'Filter by subject'},
        {'params': {'resourceType': 'Observation', 'fields': 'id,status,effectiveDateTime'}, 'desc': 'Field projection'},
        {'params': {}, 'desc': 'All records'},
    ]
    
    for test in query_tests:
        print(f"\n  Query: {test['desc']}")
        result = test_get_records(test['params'])
        results['queries'].append({
            'test': test['desc'],
            'success': result is not None
        })
    
    # 3. Test GET /records/:id
    print(f"\n{BLUE}Phase 3: Testing Single Record Retrieval{RESET}")
    test_get_record_by_id('obs-batch-001', fields='id,status,code')
    test_get_record_by_id('invalid-id-12345')  # Test 404
    
    # 4. Test nested field projection
    print(f"\n{BLUE}Phase 4: Testing Nested Field Access{RESET}")
    test_nested_field_projection()
    
    # 5. Test POST /transform
    print(f"\n{BLUE}Phase 5: Testing Transform Endpoint{RESET}")
    transform_result = test_transform(['Observation'], subject='Patient/PT-400')
    results['transforms'].append({
        'test': 'Transform with filters',
        'success': transform_result is not None
    })
    
    # 6. Test exports
    print(f"\n{BLUE}Phase 6: Testing Export Formats{RESET}")
    csv_result = test_export_csv('Observation')
    results['exports'].append({
        'format': 'CSV',
        'success': csv_result
    })
    
    # 7. Test analytics
    print(f"\n{BLUE}Phase 7: Testing Analytics{RESET}")
    analytics_result = test_analytics()
    results['analytics'] = analytics_result is not None
    
    # 8. Test duplicate handling
    print(f"\n{BLUE}Phase 8: Testing Duplicate Detection{RESET}")
    print_info("Re-importing duplicates.jsonl to test skip behavior")
    test_import('duplicates.jsonl')
    
    # Print summary
    print_section("Test Summary")
    
    print("\n📥 Import Tests:")
    for result in results['imports']:
        status = "✓" if result['success'] else "✗"
        color = GREEN if result['success'] else RED
        print(f"  {color}{status}{RESET} {result['file']}")
    
    print("\n🔍 Query Tests:")
    for result in results['queries']:
        status = "✓" if result['success'] else "✗"
        color = GREEN if result['success'] else RED
        print(f"  {color}{status}{RESET} {result['test']}")
    
    print("\n🔄 Transform Tests:")
    for result in results['transforms']:
        status = "✓" if result['success'] else "✗"
        color = GREEN if result['success'] else RED
        print(f"  {color}{status}{RESET} {result['test']}")
    
    print("\n📊 Export Tests:")
    for result in results['exports']:
        status = "✓" if result['success'] else "✗"
        color = GREEN if result['success'] else RED
        print(f"  {color}{status}{RESET} {result['format']} export")
    
    status = "✓" if results['analytics'] else "✗"
    color = GREEN if results['analytics'] else RED
    print(f"\n📈 Analytics: {color}{status}{RESET}")
    
    print(f"\n{BLUE}{'='*80}")
    print("✨ Test suite completed!")
    print(f"{'='*80}{RESET}\n")


if __name__ == "__main__":
    run_all_tests()