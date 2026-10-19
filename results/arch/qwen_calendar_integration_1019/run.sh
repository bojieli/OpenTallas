#!/bin/bash
set -euo pipefail
cd run
python3 source_body.py ../sourcegen
python3 ../src/tools/qwen_layerbench/finite_calendar_body.py --input body.json --out image
python3 playback.py
