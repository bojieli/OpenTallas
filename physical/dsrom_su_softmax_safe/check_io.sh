#!/bin/bash
# Full SS setup and FF hold IO qualification, each >=15 ps. Missing paths fail.
set -euo pipefail
D=${1:?route directory}; H=$(cd "$(dirname "$0")/../dsrom_su_softmax_r5" && pwd)
bash "$H/io_budget.sh" "$D/work/orfs" "$D/io" 150 100 | tee "$D/io_budget.txt"
python3 "$(dirname "$0")/check_io.py" "$D/io_budget.txt"
