import os
from services.parser_service import parse_jsonl_file
from services.validator_service import validate_resource

def main():
    """
    Main function to read, parse, and validate a JSONL file.
    """
    file_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'sample.jsonl')
    
    try:
        with open(file_path, 'r') as f:
            file_content = f.read()
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return

    all_errors = []
    for line_number, resource, error in parse_jsonl_file(file_content):
        if error:
            all_errors.append(f"Line {line_number}: {error}")
            continue
        
        validation_errors = validate_resource(resource, line_number)
        all_errors.extend(validation_errors)

    if all_errors:
        for err in all_errors:
            print(err)
    else:
        print("All resources are valid.")

if __name__ == "__main__":
    main()
