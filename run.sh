#!/usr/bin/env bash
# Startup script for REC-8K Video Transformation Studio
# One command to run the backend and UI (Clean Code rule E1)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

export PYTHONPATH="$SCRIPT_DIR/packages:$PYTHONPATH"

echo "========================================================"
echo "🚀 Starting REC-8K Video Transformation Studio..."
echo "📂 Working Directory: $SCRIPT_DIR"
echo "🌐 UI Available at: http://localhost:8000"
echo "========================================================"

exec python3 main.py
