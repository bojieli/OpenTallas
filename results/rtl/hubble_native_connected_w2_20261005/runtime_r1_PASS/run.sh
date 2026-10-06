#!/bin/bash
set -euo pipefail
job=/srv/opentallas-scratch2/jobs/hubble-native-connected-w2-r1
export TMPDIR="$job/tmp" OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
ulimit -t unlimited
ulimit -v unlimited
ulimit -f unlimited
cd "$job/src"
trap 'rc=$?; printf "%s\n" "$rc" > "$job/terminal.exit"' EXIT
verilator --version > "$job/toolchain.log"
printf 'a86d3cfd3\n' > "$job/source.commit"
python3 tools/hubble_w2_connected_runtime.py build --work "$job/build" --case "$job/case" --donor-sources "$job/hubble-native-w2-donor-sources.json" --jobs 4
python3 tools/hubble_w2_connected_runtime.py run --work "$job/build" --case "$job/case" --original-prefix "$job/original/mem"
