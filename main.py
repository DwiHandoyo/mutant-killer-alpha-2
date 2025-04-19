import os
import subprocess
from typing import Any, Dict

from flask_cors import CORS
from flask import Flask, request, jsonify
from flask_socketio import SocketIO

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app)

CLONED_REPOS_DIR = "cloned_repos"  # Directory to store cloned repos

if not os.path.exists(CLONED_REPOS_DIR):
    os.makedirs(CLONED_REPOS_DIR)


def get_repo_path(repo_name: str) -> str:
    """Gets the full path to a cloned repository."""
    return os.path.join(CLONED_REPOS_DIR, repo_name)


@socketio.on('connect')
def handle_connect():
    print('Client connected')


@app.route('/mutation-test', methods=['POST'])
def mutation_test():
    data: Dict[str, Any] = request.get_json()
    if not data or 'repository_url' not in data:
        return jsonify({'error': 'Missing repository_url'}), 400

    repository_url: str = data['repository_url']
    repo_name: str = repository_url.split('/')[-1].replace('.git', '')  # Extract repo name
    local_directory: str = get_repo_path(repo_name)

    try:
        if not os.path.exists(local_directory):
            clone_repository(repository_url, local_directory)
            send_websocket_notification("Repository cloned successfully.")
        else:
            send_websocket_notification("Repository already cloned, skipping clone.")

        is_php: bool = detect_language(local_directory)
        send_websocket_notification(f"Is PHP project: {is_php}")

        if is_php:
            run_mutation_testing(local_directory)
            send_websocket_notification("Mutation testing completed.")
        else:
            send_websocket_notification("Not a PHP project, skipping mutation testing.")
            return jsonify({'status': 'Not a PHP project'}), 400

        # Placeholder for analyzing unkilled mutants
        # In a real implementation, you'd parse the output of Infection
        # and extract information about unkilled mutants.
        # For now, we'll just simulate it.
        # unkilled_mutants = analyze_unkilled_mutants(local_directory)
        # send_websocket_notification(f"Unkilled mutants: {unkilled_mutants}")

        return jsonify({'status': 'Mutation testing completed successfully.'}), 200

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
    socketio.emit('notification', {'message': message})


if __name__ == "__main__":
    socketio.run(app, debug=True)


def clone_repository(repository_url: str, local_directory: str) -> None:
    """Clones a Git repository to a local directory.

    Raises:
      RuntimeError: If the git clone command fails.
    """
    result = subprocess.run(["git", "clone", repository_url, local_directory], capture_output=True, text=True)
    if result.returncode != 0:
      raise RuntimeError(f"Git clone failed with error: {result.stderr}")

def detect_language(local_directory: str) -> bool:
    """Detects if a repository is a PHP project by checking for the existence of a 'composer.json' file.

    Raises:
        OSError: If there's an issue accessing or reading the file.
    """
    composer_file_path = os.path.join(local_directory, "composer.json")
    return os.path.exists(composer_file_path)


def run_mutation_testing(local_directory: str) -> None:
    """Runs mutation testing using Infection and PHPUnit.

    Raises:
        RuntimeError: If the mutation testing command fails.
    """
    try:
        result = subprocess.run(["./vendor/bin/infection", "-s"], cwd=local_directory, capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired:
        raise RuntimeError("Mutation testing timed out after 10 minutes.")

    if result.returncode != 0:
        raise RuntimeError(f"Mutation testing failed with error: {result.stderr}")