import logging
logging.basicConfig(level=logging.INFO)

def scan_and_generate_tests(src_dir, output_dir, adapter, itteration_error=None, error_files=[], mode="file"):
    import os
    os.makedirs(output_dir, exist_ok=True)

    error_files_lowercased = [f.lower() for f in error_files]
    test_files = os.listdir(output_dir)
    test_files_lowercased = [test_file.lower().replace('.php', '') for test_file in test_files]

    for filename in os.listdir(src_dir):
        if not filename.endswith(".php"):
            continue

        filepath = os.path.join(src_dir, filename)
        test_filename = filename.replace('.php', 'test').lower()
        if test_filename not in error_files_lowercased and test_filename in test_files_lowercased and itteration_error:
            logging.info(f"Skipping {test_filename} as it is not in the error files list.")
            continue
        if mode == "file":
            adapter.generate_test_case_from_file(filepath, output_dir, itteration_error)
        else:
            with open(filepath, "r") as f:
                source_code = f.read()
            test_code = adapter.generate_test_case(source_code, filename)

            output_path = os.path.join(output_dir, f"{filename.replace('.php', 'Test.php')}")
            with open(output_path, "w") as out:
                out.write(test_code.replace("```php", "").replace("```", ""))