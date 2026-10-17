#!/usr/bin/env bash
set -euo pipefail
task_script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
python3 -m unittest discover -s "$task_script_dir" -p 'test_die_case_v16*py' -v
