#!/bin/bash
set -eu
H=$(cd "$(dirname "$0")" && pwd)
python3 "$H/apply_D.py" "$1"
