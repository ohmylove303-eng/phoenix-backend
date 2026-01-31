#!/Users/jungsunghoon/Desktop/Phoenix/venv/bin/python
import os
import sys

# Ensure project root is in path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

from api.server import app

if __name__ == "__main__":
    print(f"Starting Project Phoenix API from {project_root}...")
    app.run(host='0.0.0.0', port=5002, debug=True, use_reloader=False)
