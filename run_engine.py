#!/Users/jungsunghoon/Desktop/Phoenix/venv/bin/python
import os
import sys

# Ensure project root is in path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

from engine.core import run_engine

if __name__ == "__main__":
    print(f"Starting Project Phoenix Engine from {project_root}...")
    run_engine()
