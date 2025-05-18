import json
import os
from collections import defaultdict

def group_by_original_file_path(data, output_dir):
    """
    Groups the "escaped" and "uncovered" mutants in the Infection JSON file by their originalFilePath.

    Args:
        input_file (str): Path to the input Infection JSON file.
        output_dir (str): Directory to save the grouped JSON files.
    """

    grouped_data = defaultdict(lambda: {"escaped": [], "uncovered": []})

    # Group escaped mutants
    for mutant in data.get("escaped", []):
        mutator = mutant.get("mutator", {})
        original_file_path = mutator.get("originalFilePath", "unknown")
        sanitized_name = os.path.basename(original_file_path).replace("/", "_").replace("\\", "_").replace(":", "_")
        element = {
            "diff": mutant["diff"],
            "startLine": mutator.get("originalStartLine", 1)
        }
        grouped_data[sanitized_name]["uncovered"].append(element)

    # Group uncovered mutants
    for mutant in data.get("uncovered", []):
        mutator = mutant.get("mutator", {})
        original_file_path = mutator.get("originalFilePath", "unknown")
        sanitized_name = os.path.basename(original_file_path).replace("/", "_").replace("\\", "_").replace(":", "_")
        element = {
            "diff": mutant["diff"],
            "startLine": mutator.get("originalStartLine", 1)
        }
        grouped_data[sanitized_name]["uncovered"].append(element)
    return grouped_data

def save_grouped_data(grouped_data, output_dir):
        # Ensure the output directory exists
        os.makedirs(output_dir, exist_ok=True)
        # Save each group to a separate JSON file
        for original_file_path, content in grouped_data.items():
            # Extract only the file name from the originalFilePath
            sanitized_name = os.path.basename(original_file_path).replace("/", "_").replace("\\", "_").replace(":", "_")
            output_file = os.path.join(output_dir, f"{sanitized_name}.json")
            with open(output_file, 'w') as f:
                json.dump(content, f, indent=4)

if __name__ == "__main__":
    input_json = "infection.json"  # Replace with your input Infection JSON file
    output_directory = "grouped_infection_files"  # Replace with your desired output directory
    group_by_original_file_path(input_json, output_directory)
