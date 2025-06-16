import os
import subprocess
import shutil
import time
import zipfile
import re
import json
from typing import Any, Dict
from flask import Flask, request, jsonify, send_file, send_from_directory, render_template
from flask_socketio import SocketIO
from flask_cors import CORS
from llm.core.scanner import scan_and_generate_tests
from llm.core.models import model_factory
from git import Repo, GitCommandError
from parser.infection_parser import group_by_original_file_path
import logging
logging.basicConfig(level=logging.INFO)

HOST = os.getenv("HOST", "0.0.0.0")
PORT = os.getenv("PORT", 5000)  
MODEL = 'gemini'

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

CLONED_REPOS_DIR = os.path.join(os.getcwd(), "cloned_repos")  # Directory to store cloned repos
GENERATED_ZIPS_DIR = os.path.join(os.getcwd(), "generated_zips")  # Directory to store cloned repos

MAX_REFINEMENT_ITERATIONS = 2

if not os.path.exists(CLONED_REPOS_DIR):
    os.makedirs(CLONED_REPOS_DIR)

if not os.path.exists(GENERATED_ZIPS_DIR):
    os.makedirs(GENERATED_ZIPS_DIR)

def get_repo_path(repo_name: str) -> str:
    """Gets the full path to a cloned repository."""
    return os.path.join(CLONED_REPOS_DIR, repo_name)


@socketio.on('connect')
def handle_connect():
    
    send_websocket_notification("connected")
    logging.info('Client connected')

@socketio.on('my_event')
def handle_my_custom_event(json_data):
    logging.info(f"Received WebSocket message: {json_data}")

def clone_repository(repository_url: str, local_directory: str) -> None:
    """Clones a Git repository using GitPython."""
    try:
        logging.info("cloning repository...")
        Repo.clone_from(repository_url, local_directory)
        logging.info("Repository cloned successfully.")
    except GitCommandError as e:
        raise RuntimeError(f"Git clone failed: {str(e)}")


def detect_language(local_directory: str) -> bool:
    """
    Detects if a repository is a PHP project by checking for:
    1. 'composer.json' file
    2. Any .php files in the directory (recursively)
    3. Common PHP config files (e.g., phpunit.xml, infection.json)

    Returns:
        True if likely a PHP project, False otherwise.
    """
    # 1. Check for composer.json
    composer_file_path = os.path.join(local_directory, "composer.json")
    if os.path.exists(composer_file_path):
        return True

    # 2. Recursively check for .php files
    for root, _, files in os.walk(local_directory):
        for filename in files:
            if filename.endswith(".php"):
                return True

    # 3. Check for other PHP-related config files
    common_php_configs = ["phpunit.xml", "phpunit.xml.dist", "infection.json", ".php_cs", ".php_cs.dist"]
    for config_file in common_php_configs:
        if os.path.exists(os.path.join(local_directory, config_file)):
            return True

    return False

def ensure_default_files(local_directory: str):
    composer_path = os.path.join(local_directory, "composer.json")
    if not os.path.exists(composer_path):
        with open(composer_path, "w") as f:
            json.dump(DEFAULT_COMPOSER_JSON, f, indent=2)
        send_websocket_notification("Default composer.json has been created.")

    infection_config_path = os.path.join(local_directory, "infection.json5")
    if not os.path.exists(infection_config_path):
        with open(infection_config_path, "w") as f:
            json.dump(DEFAULT_INFECTION_JSON5, f, indent=2)
        send_websocket_notification("Default infection.json5 has been created.")

def run_composer_install(local_directory: str) -> None:
    # ensure_default_files(local_directory)
    # send_websocket_notification("Running `composer update`...")
    # subprocess.run(["composer", "update", "infection/infection", "--no-interaction", "--prefer-dist"], cwd=local_directory, shell=True)
    # subprocess.run(["composer", "update"], cwd=local_directory, shell=True)

        # Copy vendor and custom-mutators folders, and infection.json5
    source_vendor = os.path.join(app.root_path, 'vendor')
    target_vendor = os.path.join(local_directory, 'vendor')
    source_mutators = os.path.join(app.root_path, 'custom-mutators')
    target_mutators = os.path.join(local_directory, 'custom-mutators')
    source_infection = os.path.join(app.root_path, 'infection.json5')
    target_infection = os.path.join(local_directory, 'infection.json5')
    source_composer = os.path.join(app.root_path, 'composer.json')
    target_composer = os.path.join(local_directory, 'composer.json')
    source_composer_lock = os.path.join(app.root_path, 'composer.lock')
    target_composer_lock = os.path.join(local_directory, 'composer.lock')
    source_php_unit = os.path.join(app.root_path, 'phpunit.xml')
    target_php_unit = os.path.join(local_directory, 'phpunit.xml')

    
    vendor_zip_path = os.path.join(app.root_path, 'vendor.zip')

    send_websocket_notification("composer install preparation")
    # Copy vendor folder using zip strategy
    if os.path.exists(vendor_zip_path):

        # Copy the zip file to the target directory
        target_zip_path = os.path.join(local_directory, 'vendor.zip')
        shutil.copy2(vendor_zip_path, target_zip_path)

        if os.path.exists(target_vendor):
            logging.info("removing vendor folder")
            
            if os.name == 'nt':
                os.system('rmdir /S /Q "{}"'.format(target_vendor))
            else:
                os.system('rm -rf "{}"'.format(target_vendor))

        # Extract the zip file in the target directory
        with zipfile.ZipFile(target_zip_path, 'r') as zipf:
            zipf.extractall(target_vendor)

        # Clean up the zip files
        try :
            os.remove(vendor_zip_path)
        except PermissionError:
            logging.info("PermissionError: Unable to remove vendor.zip. It might be in use.")

    # Copy custom-mutators folder
    if os.path.exists(source_mutators):
        if os.path.exists(target_mutators):
            if os.name == 'nt':
                os.system('rmdir /S /Q "{}"'.format(target_mutators))
            else:
                os.system('rm -rf "{}"'.format(target_mutators))
        shutil.copytree(source_mutators, target_mutators)

    # Copy infection.json5 file
    if os.path.exists(source_infection):
        shutil.copy2(source_infection, target_infection)

    # Copy composer.json file
    if os.path.exists(source_composer):
        shutil.copy2(source_composer, target_composer)

    # Copy composer.lock file
    if os.path.exists(source_composer_lock):
        shutil.copy2(source_composer_lock, target_composer_lock)

    # Copy php_unit.xml file
    if os.path.exists(source_php_unit):
        shutil.copy2(source_php_unit, target_php_unit)

    send_websocket_notification("Running `composer install`...")
    composer_cmd = ["composer", "install", "--no-interaction", "--prefer-dist", "--no-plugins"]
    result = subprocess.run(composer_cmd, cwd=local_directory, text=True, shell=True)
    
    if result.returncode != 0:
        raise RuntimeError(f"Composer install failed:\n{result.stderr}")

def parse_phpunit_summary(raw_output: str):
    # Regex untuk mencari baris ringkasan
    summary_pattern = re.compile(
        r"Tests:\s*(\d+),\s*Assertions:\s*(\d+),"
        r"(?:\s*Failures:\s*(\d+),)?"
        r"(?:\s*Errors:\s*(\d+),)?"
        r"(?:\s*Warnings:\s*(\d+),)?"
        r"(?:\s*Deprecations:\s*(\d+)\.?)?"
    )

    match = summary_pattern.search(raw_output)
    if not match:
        return None

    # Ambil hasil, jika tidak ada maka 0
    tests = int(match.group(1))
    assertions = int(match.group(2))
    failures = int(match.group(3) or 0)
    errors = int(match.group(4) or 0)
    warnings = int(match.group(5) or 0)
    deprecations = int(match.group(6) or 0)

    return {
        "tests": tests,
        "assertions": assertions,
        "failures": failures,
        "errors": errors,
        "warnings": warnings,
        "deprecations": deprecations
    }

def parse_infection_failures_and_errors(raw_output: str):
    """
    Mengembalikan:
      - failure_count: int
      - failure_messages: list[str]
      - error_count: int
      - error_messages: list[str]
    """
    failure_count = 0
    failure_messages = ''
    error_count = 0
    error_messages = ''

    # Regex blok failure
    failure_header = re.search(r"There (?:was|were) (\d+) failure", raw_output)
    if failure_header:
        failure_count = int(failure_header.group(1))
        failure_blocks = re.findall(
            r"\d+\)\s+([^\n]+)\n((?:\s{9,}.*\n)+)", raw_output
        )
        for test_name, message_block in failure_blocks:
            message = test_name.strip() + "\n" + message_block.strip()
            failure_messages += message

    # Regex blok error
    error_header = re.search(r"There (?:was|were) (\d+) error", raw_output)
    if error_header:
        error_count = int(error_header.group(1))
        error_blocks = re.findall(
            r"\d+\)\s+([^\n]+)\n((?:\s{9,}.*\n)+)", raw_output
        )
        # Untuk error, filter blok yang mengandung kata 'Error:' pada message_block
        for test_name, message_block in error_blocks:
            if 'Error:' in message_block:
                message = test_name.strip() + "\n" + message_block.strip()
                error_messages += message
    infection_report = {
        "failure_count": failure_count,
        "error_count": error_count
        }
    logging.info(f"failure count: {failure_count}, error count: {error_count}")
    return error_messages +  failure_messages, infection_report


def run_php_testing(local_directory: str) -> None:
    """Runs PHPUnit tests."""
    send_websocket_notification("Running PHPUnit tests...")

    main_command = "vendor/bin/phpunit"
    # if machine is windows then adjust the command
    if os.name == 'nt':
        main_command = "vendor\\bin\\phpunit"
    try:
        result = subprocess.run([
            main_command,
            "--fail-on-skipped",
            "--coverage-xml",
            ".mutagen-tmp/coverage",
            "--log-junit",
            ".mutagen-tmp/junit.xml"
            ],
            cwd=local_directory,
            text=True,
            timeout=600,
            shell=True,
            capture_output=True
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("PHPUnit tests timed out after 10 minutes.")
    

    result_out = result.stdout.strip()

    send_websocket_notification("PHPUnit tests completed.")
    # find errors and errors in the output, start with 'errors' and ends with second '--
    errors_index = result_out.find('errors:')
    # find all occurencies of --
    errors_end_index = result_out.find('--', errors_index + 1)
    error_message = result_out[errors_index: errors_end_index].strip() if errors_index != -1 else ''

    failures_index = result_out.find('failures:')
    failures_end_index = result_out.find('--', failures_index + 1)
    failures_message = result_out[failures_index: failures_end_index].strip() if failures_index != -1 else ''
    test_summary = parse_phpunit_summary(result_out)
    return error_message + '\n' + failures_message, test_summary

def generate_tests(local_directory: str) -> Dict[str, Any]:
    first_infection_result, first_test_report, first_infection_report = {}, {}, {}
    for i in range(MAX_REFINEMENT_ITERATIONS):
        error = ''
        test_report = {}
        infection_report = {}
        try:
            test_error, test_report= run_php_testing(local_directory)
            error += test_error + '\n'
        except Exception as e:
            error += "error in phpunit: " + str(e) + '\n'
            send_websocket_notification("PHPUnit tests failed, skipping mutation testing.")

        try:
            infection_error, infection_report = run_mutation_testing(local_directory)
            error += infection_error + '\n'
        except Exception as e:
            error += "error in mutation testing: " + str(e) + '\n'
            send_websocket_notification("Mutation testing failed, skipping test generation.")

        infection_result = {}
        with open(os.path.join(local_directory, 'infection.json'), 'r') as f:
            infection_result = json.load(f)
        infection_result_map = group_by_original_file_path(infection_result, local_directory)

        
        error_files = extract_failed_classes(test_error + infection_error)


        if i == 0:
            first_infection_result = infection_result
            first_test_report = test_report
            first_infection_report = infection_report
            error = None
        
        try: 
            model = model_factory(MODEL, infection_result_map)
            scan_and_generate_tests(os.path.join(local_directory, 'src'), os.path.join(local_directory, 'tests'), model, error, error_files)
        except RuntimeError as e:
            send_websocket_notification("Failed to generate tests using LLM, skipping.")
        except Exception as e:
            logging.info(e)

    #final evaluation
    try:
        test_error_final_iteration, _ = run_php_testing(local_directory)
        infection_error_final_iteration, _ = run_mutation_testing(local_directory)
        logging.info(f"Test error final iteration: {extract_failed_classes(infection_error_final_iteration)}")
        error_files = extract_failed_classes(test_error_final_iteration + infection_error_final_iteration)
        test_files = os.listdir(os.path.join(local_directory, 'tests'))
        logging.info(f"Error files to remove: {error_files}")
        logging.info(f"Test files: {test_files}")
        send_websocket_notification("Removing test files for errors: " + str(error_files))
        ## remove errors files with case insensitive name
        for error_file in error_files:
            error_file = error_file.lower()
            for test_file in test_files:
                if test_file.lower().startswith(error_file):
                    test_file_path = os.path.join(local_directory, 'tests', test_file)
                    logging.info(f"Removing test file: {test_file_path}")
                    os.remove(test_file_path)
    except Exception as e:
        error += "error in phpunit: " + str(e) + '\n'
        send_websocket_notification("PHPUnit tests failed, skipping mutation testing.")

    return first_infection_result, first_test_report, first_infection_report
    

def extract_failed_classes(raw):
    # Match patterns like '1) SomeNamespace\ClassName::', '* SomeNamespace\ClassName::', etc.
    matches_error = re.findall(r'\d+\)\s+([A-Za-z0-9_\\]+)::', raw)
    matches_star = re.findall(r'\*\s+([A-Za-z0-9_\\]+)::', raw)
    # Extract only the class name (last part after backslash)
    def get_class_name(s):
        return s.split('\\')[-1]
    all_matches = matches_error + matches_star
    return list(set(get_class_name(m) for m in all_matches))

def run_mutation_testing(local_directory: str) -> None:
    """Runs composer install and then mutation testing using Infection."""
    send_websocket_notification("Running mutation testing via Infection...")
    main_command = "vendor/bin/infection"
    # if machine is windows then adjust the command
    if os.name == 'nt':
        main_command = "vendor\\bin\\infection"
    try:
        result = subprocess.run(
            [main_command],
            cwd=local_directory,
            text=True,
            timeout=600,
            shell=True,
            capture_output=True
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("Mutation testing timed out after 10 minutes.")

    # html_report = os.path.join(local_directory, "infection.html")
    # if not os.path.exists(html_report):
    #     raise RuntimeError("Mutation report (infection.html) not found after running Infection.")
    
    # html = open(html_report, "r").read()

    result_out = result.stdout.strip()
    logging.info(f"Mutation testing output: {result_out}")
    error_message, infection_report = parse_infection_failures_and_errors(result_out)
    logging.info(f"infection report: {infection_report}")
    logging.info(f"error message: {error_message}")
    send_websocket_notification("Mutation testing completed and report generated.")
    return error_message, infection_report


def extract_ast_from_php(directory):
    send_websocket_notification("Extracting php code...")

    # Lokasi asli dan target script
    src_script = "ast-utils/extract_ast.php"
    target_script = os.path.join(directory, "extract_ast.php")

    # Salin ke dalam repo target
    shutil.copy(src_script, target_script)
    targets = ['src', 'tests']

    for target in targets:
        # Jalankan dari dalam folder repo
        src_dir = os.path.join(directory, target)
        output_dir = os.path.join(directory, "output-ast")

        subprocess.run([
            "php", "extract_ast.php", src_dir, output_dir
        ], cwd=directory,
                capture_output=True,
                text=True, shell=True)

    # time.sleep(100)
    # (Opsional) hapus setelah selesai
    os.remove(target_script)
    send_websocket_notification("AST extracted.")

def mutation_test_handler(repository_url: str, websocket_endpoint: str) -> Dict[str, Any]:
   
    send_websocket_notification(f"Received repository URL: {repository_url}")
    send_websocket_notification(f"Using WebSocket endpoint: {websocket_endpoint}")

    repo_name: str = repository_url.split('/')[-1].replace('.git', '')  # Extract repo name
    local_directory: str = get_repo_path(repo_name)
    send_websocket_notification("running")

    try:
        if not os.path.exists(local_directory):
            clone_repository(repository_url, local_directory)
            send_websocket_notification("Repository cloned successfully.")
        else:
            send_websocket_notification("Repository already cloned, skipping clone.")

        is_php: bool = detect_language(local_directory)
        send_websocket_notification(f"project is php")


        if not is_php:
            send_websocket_notification("Not a PHP project, skipping mutation testing.")
            return jsonify({'status': 'Not a PHP project'}), 400
        
        run_composer_install(local_directory)
        send_websocket_notification("Composer install completed.")

        first_infection_result, first_test_report, first_infection_report = generate_tests(local_directory)
        
        try:
            test_error, final_test_report = run_php_testing(local_directory)

            infection_error, final_infection_report = run_mutation_testing(local_directory)
        except RuntimeError as e:
            send_websocket_notification("PHPUnit tests failed, skipping mutation testing.")

        final_infection_result = {}
        with open(os.path.join(local_directory, 'infection.json'), 'r') as f:
            final_infection_result = json.load(f)

        # Create a zip file of the 'src' and 'tests' directories only
        zip_filename = f"{repo_name}.zip"
        zip_filepath = os.path.join(app.root_path, GENERATED_ZIPS_DIR, zip_filename)
        with zipfile.ZipFile(zip_filepath, 'w') as zipf:
            for folder in ['src', 'tests']:
                folder_path = os.path.join(local_directory, folder)
                if os.path.exists(folder_path):
                    for root, _, files in os.walk(folder_path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, local_directory)
                            zipf.write(file_path, arcname)

        # Return the download URL for the zip file
        download_url = request.host_url.rstrip('/') + f"/download/{zip_filename}"
        send_websocket_notification(f"first test report: {first_test_report}")
        send_websocket_notification(f"final test report: {final_test_report}")
        send_websocket_notification(f"first infection report: {first_infection_report}")
        send_websocket_notification(f"final infection report: {final_infection_report}")
        return {
            'status': 'Mutation testing completed successfully.',
            'download_url': download_url,
            "first_infection_result": first_infection_result,
            "final_infection_result": final_infection_result,
            "first_test_report": first_test_report,
            "final_test_report": final_test_report,
            "first_infection_report": first_infection_report,
            "final_infection_report": final_infection_report
        }

    except RuntimeError as e:
        send_websocket_notification(f"Error: {e}")
        return {'error': str(e)}

@app.route('/download/<filename>')
def download_file(filename):
    filepath = os.path.join(GENERATED_ZIPS_DIR, filename)
    return send_file(filepath, as_attachment=True)

@app.route('/mutation-test', methods=['POST'])
def mutation_test():
    logging.info("testing mutation test endpoint")
    data: Dict[str, Any] = request.get_json()
    if not data or 'repository_url' not in data or 'websocket_endpoint' not in data:
        return jsonify({'error': 'Missing repository_url or websocket_endpoint'}), 400

    repository_url: str = data['repository_url']
    websocket_endpoint: str = data['websocket_endpoint']

    try:
        response = mutation_test_handler(repository_url, websocket_endpoint)
        return jsonify(response), 200

    except RuntimeError as e:
        send_websocket_notification(f"Error: {e}")
        return jsonify({'error': str(e)}), 500


def analyze_unkilled_mutants(local_directory: str) -> str:
    """Abstract method for analyzing unkilled mutants and generating test cases."""
    # In a real implementation, this function would:
    # 1. Parse the output of the Infection run (likely an HTML or JSON report).
    # 2. Identify the mutants that were not killed by the existing test suite.
    # 3. Potentially suggest or generate new test cases to target those mutants.
    # For this example, we'll just return a placeholder message.
    return "Analysis of unkilled mutants (implementation needed)"


def send_websocket_notification(message: str) -> None:
    """Sends a notification to the client via WebSocket."""
    logging.info(f"Sending WebSocket notification: {message}")
    socketio.emit('notification', {'message': message})

# Serve index.html at root
@app.route('/')
def landing_page():
    return send_from_directory('static', 'landing.html')

@app.route('/scan')
def scan_dashboard():
    return send_from_directory('static', 'index.html')


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=PORT, debug=True, allow_unsafe_werkzeug=True)



import json

DEFAULT_COMPOSER_JSON = {
    "autoload": {
        "psr-4": {
            "App\\": "src/",
            "func\\": "src/",
            "SecurityService\\": "src/",
            "App\\Mutator\\": "custom-mutators/"
        }
    },
    "autoload-dev": {
        "psr-4": {
            "Tests\\": "tests/"
        }
    },
    "require-dev": {
        "phpunit/phpunit": "^10.5.16",
        "infection/infection": "^0.26.21",
        "rector/rector": "^2.0"
    },
    "require": {
        "infection/mutator": "^0.4.0"
    },
    "config": {
        "allow-plugins": {
            "infection/extension-installer": True
        },
        "process-timeout": 0
    }
}

DEFAULT_INFECTION_JSON5 = {
    "source": {
        "directories": ["src", "tests"],
        "excludes": ["vendor"]
    },
    "phpUnit": {
        "configDir": "."
    },
    "mutators": {
        "@default": True
    },
    "timeout": 10,
    "logs": {
        "text": "infection.log",
        "html": "infection.html",
        "json": "infection.json",
        "summary": "summary.log"
    }
}


def parse_phpunit_failures(raw_output: str):
    # Cari jumlah failure
    failure_count = 0
    failure_messages = []

    # Regex untuk mendeteksi blok "There was X failure(s):"
    failure_header = re.search(r"There (?:was|were) (\d+) failure", raw_output)
    if failure_header:
        failure_count = int(failure_header.group(1))

        # Regex untuk mengambil setiap blok failure
        # Blok dimulai dengan angka dan nama test, diikuti pesan hingga baris kosong
        failure_blocks = re.findall(
            r"\d+\)\s+([^\n]+)\n((?:\s{9,}.*\n)+)", raw_output
        )
        for test_name, message_block in failure_blocks:
            # Gabungkan dan strip pesan
            message = test_name.strip() + "\n" + message_block.strip()
            failure_messages.append(message)

    return failure_count, failure_messages

# @socketio.on('mutation_test')
# def handle_mutation_test_socketio(data):
#     # Frontend (web) biasanya mengirim: { git_url, room_name }
#     repo_url = data.get('git_url') or data.get('repository_url')
#     room = data.get('room_name') or data.get('websocket_endpoint')
#     if not repo_url or not room:
#         socketio.emit('mutation_test_result', {'error': 'Missing git_url/repository_url or room_name/websocket_endpoint'})
#         return
#     # Jalankan proses utama
#     response = mutation_test_handler(repo_url, room)
#     # Kirim hasil ke room yang sesuai (agar user yang request dapat hasilnya saja)
#     socketio.emit('mutation_test_result', response, room=room)
