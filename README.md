# Acme EHR - FHIR Data Processing API

A lightweight Flask-based API for importing, validating, and querying FHIR-like healthcare records.

---

## Quick Start

```bash
# Clone and run
gh repo clone karthikp32/acme-ehr
cd acme-ehr
make run
```

The API will be available at `http://localhost:5000/api/v1`

---

## Running Tests

A comprehensive test suite is provided to validate all API endpoints.
```bash
# Run the test suite
python src/tests/test_all_endpoints.py
```

**Prerequisites:**
- API server must be running (`make run`)
- Test data files in `data/` directory

**What it tests:**
- ✅ Import endpoint with multiple JSONL files (valid, invalid, duplicates, edge cases)
- ✅ Query endpoints with filters and field projection
- ✅ Single record retrieval (including 404 handling)
- ✅ Nested field access (dot notation and array indexing)
- ✅ Transform endpoint with flatten/extract operations
- ✅ Export formats (CSV, TXT)
- ✅ Analytics endpoint
- ✅ Duplicate detection and Last-Write-Wins behavior

**Expected output:**
```
================================================================================
🧪 ACME EHR API - Comprehensive Test Suite
================================================================================

Phase 1: Testing Imports
...
Phase 7: Testing Analytics
...

Test Summary
================================================================================

📥 Import Tests:
  ✓ edge_cases.jsonl (3 imported, 10 failed)
  ✓ mixed_resources.jsonl (12 imported, 0 failed)
  ✓ minimal_valid.jsonl (5 imported, 0 failed)
  ✓ large_batch.jsonl (16 imported, 0 failed)
  ✓ duplicates.jsonl (5 imported, 0 failed)

...

✨ Test suite completed!
```

---

## Configuration

The system's behavior is controlled by two configuration files in `src/config/`:

### 📋 Validation Rules (`validation_config.py`)

Defines what fields are required and what values are valid for each resource type.

**Structure:**
```python
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
        "valid_status": ["completed", "active"]
    },
    "Procedure": {
        "required": ["code", "status"],
        "valid_status": ["completed", "in-progress"]
    },
    "Condition": {
        "required": ["code"]
    }
}
```

Resources that fail validation are rejected with detailed error messages.

### 🔍 Extraction Rules (`extraction_config.py`)

Defines which fields are extracted from raw FHIR data for fast querying.

**Structure:**
```python
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
```

Extracted fields are stored in the `extracted_fields` column for efficient queries without parsing full JSON.

---

## API Endpoints

### 📥 Import Records
Upload and validate FHIR resources from a JSONL file.

```bash
curl -X POST http://localhost:5000/api/v1/import \
  -F "file=@data/sample.jsonl"
```

**Returns:** Import summary with success/failure counts and validation errors.

---

### 📊 List Records
Query records with filters and field projection.

**Basic query:**
```bash
curl 'http://localhost:5000/api/v1/records?resourceType=Observation'
```

**Filter by patient:**
```bash
curl 'http://localhost:5000/api/v1/records?subject=Patient/PT-001'
```

**Project specific fields:**
```bash
curl 'http://localhost:5000/api/v1/records?fields=id,status,effectiveDateTime'
```

**Nested field access:**
```bash
# Use -g flag for array indexing
curl -g 'http://localhost:5000/api/v1/records?fields=id,code.text,component[0].valueQuantity.value'
```

**Export as CSV:**
```bash
curl 'http://localhost:5000/api/v1/records?resourceType=Observation&format=csv' -o data.csv
```

**Export as TXT:**
```bash
curl 'http://localhost:5000/api/v1/records?subject=Patient/PT-001&format=txt' -o data.txt
```

**Query Parameters:**
- `resourceType` - Filter by type (Observation, Procedure, etc.)
- `subject` - Filter by patient reference (Patient/PT-001)
- `fields` - Comma-separated list of fields to return
- `format` - Export format: `json` (default), `csv`, `txt`

---

### 🔎 Get Single Record
Retrieve a specific record by ID.

```bash
curl 'http://localhost:5000/api/v1/records/obs-001'
```

**With field projection:**
```bash
curl 'http://localhost:5000/api/v1/records/obs-001?fields=id,status,code'
```

**Check for 404:**
```bash
curl -w "\n%{http_code}\n" 'http://localhost:5000/api/v1/records/invalid-id'
```

---

### 🔄 Transform Records
Apply transformations to reshape data without saving.

```bash
curl -X POST http://localhost:5000/api/v1/transform \
  -H "Content-Type: application/json" \
  -d '{
    "resourceTypes": ["Observation"],
    "transformations": [
      {"action": "flatten", "field": "code.coding[0]"},
      {"action": "extract", "field": "valueQuantity.value", "as": "value"},
      {"action": "extract", "field": "valueQuantity.unit", "as": "unit"}
    ],
    "filters": {
      "subject": "Patient/PT-001"
    }
  }'
```

**Transformation Actions:**
- `flatten` - Flatten nested objects into top-level fields with prefixes
- `extract` - Pull out a specific nested value and optionally rename it

**Example:**
```json
// Before
{"code": {"coding": [{"system": "http://loinc.org", "code": "2339-0"}]}}

// After flatten on "code.coding[0]"
{"code_system": "http://loinc.org", "code_code": "2339-0"}
```

---

### 📈 Analytics
Get data quality metrics and statistics.

```bash
curl 'http://localhost:5000/api/v1/analytics'
```

**Returns:**
```json
{
  "total_records": 150,
  "records_by_type": {
    "Observation": 100,
    "Procedure": 30,
    "MedicationRequest": 20
  },
  "unique_subjects": 25,
  "missing_fields_top5": [
    ["effectiveDateTime", 45],
    ["status", 12]
  ]
}
```

---

## Tips

**Nested Field Access:**
- Use `-g` flag with curl when using brackets: `curl -g '...fields=component[0].value'`
- Dot notation: `code.text`, `subject.reference`
- Array indexing: `component[0].valueQuantity.value`

**Check HTTP Status:**
```bash
curl -i 'http://localhost:5000/api/v1/records/obs-001'  # Shows headers + status
curl -w "\n%{http_code}\n" '...'  # Appends status code to output
```

---

## Project Structure

```
acme-ehr/
├── src/
│   ├── config/           # Validation & extraction rules
│   ├── services/         # Business logic (validation, extraction, etc.)
│   ├── routes/           # API endpoints
│   └── models/           # Database models
├── data/                 # Sample JSONL files
└── Makefile             # Run commands
```

---

## Technical Details

**Stack:**
- Python 3.x + Flask
- SQLite database
- SQLAlchemy ORM

**Key Features:**
- ✅ JSONL bulk import with validation
- ✅ Configurable field extraction
- ✅ Flexible querying with filters and projections
- ✅ Nested field access (dot notation + array indexing)
- ✅ Data transformation pipeline
- ✅ Multiple export formats (JSON, CSV, TXT)
- ✅ Data quality analytics
- ✅ Duplicate detection (skips existing IDs)

**Database Schema:**
- `fhir_resources` - Stores resources with extracted fields for fast queries
- `import_logs` - Tracks import history and validation errors