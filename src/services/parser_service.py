import json

def parse_jsonl_file(file_content):
    """
    Parses a JSONL file content line by line.

    Args:
        file_content: A string containing the content of the JSONL file.

    Yields:
        A tuple of (line_number, parsed_json, error).
        - line_number: The 1-based line number.
        - parsed_json: The parsed JSON object, or None if parsing failed.
        - error: An error message string if parsing failed, otherwise None.
    """
    for i, line in enumerate(file_content.strip().split('\n')):
        line_number = i + 1
        try:
            if not line.strip():
                continue
            yield line_number, json.loads(line), None
        except json.JSONDecodeError as e:
            yield line_number, None, f"Invalid JSON: {e}"