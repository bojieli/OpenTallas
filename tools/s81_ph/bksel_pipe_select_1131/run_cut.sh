#!/bin/bash
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
exec python3 "$HERE/run_cut.py" "$1"
