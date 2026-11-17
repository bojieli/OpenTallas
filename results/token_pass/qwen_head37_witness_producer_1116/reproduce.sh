#!/bin/bash
# In a NEW private copy containing only source.f,input/,dw.hex,preparation.json,
# generate_masks.py and run.sh. Existing evidence/trace files are never replaced.
set -euo pipefail
cd "$(dirname "$0")"
python3 -I generate_masks.py
exec bash run.sh
