#!/usr/bin/env python
"""Standalone startup script with extensive debug logging."""

import sys
import os
import traceback

def main():
    print("=" * 50, flush=True)
    print("PHOENIX BACKEND STARTUP DEBUG", flush=True)
    print("=" * 50, flush=True)
    print(f"Python version: {sys.version}", flush=True)
    print(f"Working directory: {os.getcwd()}", flush=True)
    print(f"PORT env: {os.environ.get('PORT', 'NOT SET')}", flush=True)
    print(f"Contents of /app:", flush=True)
    
    try:
        for item in os.listdir('/app'):
            print(f"  - {item}", flush=True)
    except Exception as e:
        print(f"  Error listing /app: {e}", flush=True)
    
    print("-" * 50, flush=True)
    print("Attempting to import Flask...", flush=True)
    
    try:
        from flask import Flask
        print("✓ Flask imported successfully", flush=True)
    except ImportError as e:
        print(f"✗ Flask import failed: {e}", flush=True)
        traceback.print_exc()
        sys.exit(1)
    
    print("Attempting to import api.server...", flush=True)
    
    try:
        from api.server import app
        print(f"✓ api.server.app imported successfully: {app}", flush=True)
    except ImportError as e:
        print(f"✗ api.server import failed: {e}", flush=True)
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error during api.server import: {e}", flush=True)
        traceback.print_exc()
        sys.exit(1)
    
    print("-" * 50, flush=True)
    print("All imports successful! Starting Gunicorn...", flush=True)
    print("=" * 50, flush=True)
    
    # Use exec to replace current process with gunicorn
    port = os.environ.get('PORT', '8080')
    gunicorn_cmd = [
        sys.executable, '-m', 'gunicorn',
        'api.server:app',
        '--bind', f'0.0.0.0:{port}',
        '--workers', '2',
        '--threads', '2',
        '--timeout', '120',
        '--access-logfile', '-',
        '--error-logfile', '-'
    ]
    print(f"Exec command: {' '.join(gunicorn_cmd)}", flush=True)
    os.execv(sys.executable, gunicorn_cmd)

if __name__ == "__main__":
    main()
