import os
import subprocess
import shutil
import time
import zipfile
from typing import Any, Dict
from flask import Flask, request, jsonify, send_file
from flask_socketio import SocketIO
from flask_cors import CORS
from llm.core.scanner import scan_and_generate_tests
from llm.core.models import model_factory
from git import Repo, GitCommandError

HOST = os.getenv("HOST", "0.0.0.0")
PORT = os.getenv("PORT", 5000)  

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, host=HOST, port=PORT, cors_allowed_origins="*", async_mode='threading')

CLONED_REPOS_DIR = os.path.join(os.getcwd(), "cloned_repos")  # Directory to store cloned repos
GENERATED_ZIPS_DIR = os.path.join(os.getcwd(), "generated_zips")  # Directory to store cloned repos

if not os.path.exists(CLONED_REPOS_DIR):
    os.makedirs(CLONED_REPOS_DIR)


def get_repo_path(repo_name: str) -> str:
    """Gets the full path to a cloned repository."""
    return os.path.join(CLONED_REPOS_DIR, repo_name)


@socketio.on('connect')
def handle_connect():
    
    send_websocket_notification("connected")
    print('Client connected')

@socketio.on('my_event')
def handle_my_custom_event(json_data):
    print(f"Received WebSocket message: {json_data}")

def clone_repository(repository_url: str, local_directory: str) -> None:
    """Clones a Git repository using GitPython."""
    try:
        print("cloning repository...")
        Repo.clone_from(repository_url, local_directory)
        print("Repository cloned successfully.")
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

    send_websocket_notification("Running `composer install`...")
    composer_cmd = ["composer", "install", "--no-interaction", "--prefer-dist", "--no-plugins"]
    result = subprocess.run(composer_cmd, cwd=local_directory, text=True, shell=True)
    
    print(result)
    if result.returncode != 0:
        raise RuntimeError(f"Composer install failed:\n{result.stderr}")

def run_mutation_testing(local_directory: str) -> None:
    """Runs composer install and then mutation testing using Infection."""
    send_websocket_notification("Running mutation testing via Infection...")

    print(local_directory)
    try:
        result = subprocess.run(
            ["vendor\\bin\\infection"],
            cwd=local_directory,
            text=True,
            timeout=600,
            shell=True
        )
        print(result)
    except subprocess.TimeoutExpired:
        raise RuntimeError("Mutation testing timed out after 10 minutes.")

    if result.returncode != 0:
        raise RuntimeError(f"Infection failed:\n{result.stderr}")

    html_report = os.path.join(local_directory, "infection.html")
    if not os.path.exists(html_report):
        raise RuntimeError("Mutation report (infection.html) not found after running Infection.")
    
    html = open(html_report, "r").read()
    send_websocket_notification(html)
    send_websocket_notification("Mutation testing completed and report generated.")


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

        print(src_dir, output_dir)

        subprocess.run([
            "php", "extract_ast.php", src_dir, output_dir
        ], cwd=directory,
                capture_output=True,
                text=True, shell=True)

    # time.sleep(100)
    # (Opsional) hapus setelah selesai
    os.remove(target_script)
    send_websocket_notification("AST extracted.")

@app.route('/download/<filename>')
def download_file(filename):
    filepath = os.path.join(app.root_path, filename)
    return send_file(filepath, as_attachment=True)

@app.route('/mutation-test', methods=['POST'])
def mutation_test():
    data: Dict[str, Any] = request.get_json()
    if not data or 'repository_url' not in data or 'websocket_endpoint' not in data:
        return jsonify({'error': 'Missing repository_url or websocket_endpoint'}), 400

    repository_url: str = data['repository_url']
    websocket_endpoint: str = data['websocket_endpoint']

    send_websocket_notification(f"Received repository URL: {repository_url}")
    send_websocket_notification(f"Using WebSocket endpoint: {websocket_endpoint}")

    repo_name: str = repository_url.split('/')[-1].replace('.git', '')  # Extract repo name
    local_directory: str = get_repo_path(repo_name)
    send_websocket_notification("running")
    result = subprocess.run(["php", "-v"], capture_output=True, text=True)
    print(result)
    try:
        if not os.path.exists(local_directory):
            clone_repository(repository_url, local_directory)
            send_websocket_notification("Repository cloned successfully.")
        else:
            send_websocket_notification("Repository already cloned, skipping clone.")

        is_php: bool = detect_language(local_directory)
        send_websocket_notification(f"Is PHP project: {is_php}")


        if is_php:
            # run_composer_install(local_directory)
            send_websocket_notification("Composer install completed.")
            # run_mutation_testing(local_directory)
            send_websocket_notification("Mutation testing completed.")
        else:
            send_websocket_notification("Not a PHP project, skipping mutation testing.")
            return jsonify({'status': 'Not a PHP project'}), 400

        # for model_name in ['chatgpt', 'gemini', 'claude']:
        #     model = model_factory(model_name)
        #     scan_and_generate_tests(os.path.join(local_directory, 'src'), os.path.join(local_directory, 'test'), model)

        # Placeholder for analyzing unkilled mutants
        # In a real implementation, you'd parse the output of Infection
        # and extract information about unkilled mutants.
        # For now, we'll just simulate it.
        # unkilled_mutants = analyze_unkilled_mutants(local_directory)
        # send_websocket_notification(f"Unkilled mutants: {unkilled_mutants}")

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
        download_url = f"{HOST}:{PORT}/download/{zip_filename}"
        print(f"Download URL: {download_url}")
        return jsonify({'status': 'Mutation testing completed successfully.', 'download_url': download_url}), 200

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
    print(message)
    socketio.emit('notification', {'message': message})


if __name__ == "__main__":
    socketio.run(app, host=HOST, port=PORT, debug=True, allow_unsafe_werkzeug=True)



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
