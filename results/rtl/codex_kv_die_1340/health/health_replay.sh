#!/bin/bash
set -euo pipefail
python3 source/tools/qwen_kv_die/kv_health_plane.py install --run run --strict --parameter-profiles profiles.json > health_replay.log 2>&1
