
def scan_and_generate_tests(src_dir, output_dir, adapter, mode="file"):
    import os
    os.makedirs(output_dir, exist_ok=True)

    for filename in os.listdir(src_dir):
        if not filename.endswith(".php"):
            continue

        filepath = os.path.join(src_dir, filename)

        if mode == "file":
            adapter.generate_test_case_from_file(filepath, output_dir)
        else:
            with open(filepath, "r") as f:
                source_code = f.read()
            test_code = adapter.generate_test_case(source_code, filename)

            output_path = os.path.join(output_dir, f"{filename.replace('.php', 'Test.php')}")
            with open(output_path, "w") as out:
                out.write(test_code)