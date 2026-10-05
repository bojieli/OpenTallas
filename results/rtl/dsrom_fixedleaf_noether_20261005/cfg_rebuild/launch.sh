#!/usr/bin/env bash
# One explicit launch; no watcher/requeue. Run on EPYC2 after headroom release.
set -eu
CFG_SOURCE=/srv/opentallas/repos/noether-fixedleaf-7957cd35b
CFG_JOB=/srv/opentallas-scratch/codex/noether-fixedleaf-7957cd35b-r1/cfg
[ "$(git -C "$CFG_SOURCE" rev-parse HEAD)" = 7957cd35bac553804018405e52083f0c694d2f56 ]
[ -z "$(git -C "$CFG_SOURCE" status --porcelain)" ]
python3 - <<'PY'
from pathlib import Path
load = float(Path('/proc/loadavg').read_text().split()[0])
if load > 150:
    raise SystemExit(f'No CFG launch: non-P0 EPYC load {load} exceeds owner ceiling 150')
PY
[ ! -e "$CFG_JOB" ] || { echo 'Existing CFG output: inspect/reuse, do not overwrite or duplicate'; exit 2; }
mkdir "$CFG_JOB"
export NUM_CORES=16 OT_ORFS_NUM_CORES=16
export OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
ulimit -t unlimited
ulimit -v unlimited
ulimit -f unlimited
# Existing tool: eight concurrent copies, make -j2 each, 14 objects including controls.
nohup bash -c '
    src=$1; job=$2
    /srv/opentallas-scratch/admit.sh 16 -- bash -c '\''
        python3 "$1/tools/dsrom_elem_cfg_rw.py" run --work "$2/build" --jobs 8 --prefix-rev f23c56908 &&
        python3 "$1/tools/dsrom_elem_cfg_rw.py" record --work "$2/build" --out "$2/exact.json"
    '\'' cfg "$src" "$job"
    rc=$?
    printf "%s\n" "$rc" > "$job/terminal.rc"
    exit "$rc"
' cfg "$CFG_SOURCE" "$CFG_JOB" > "$CFG_JOB/runtime.log" 2>&1 < /dev/null &
printf '%s\n' "$!" > "$CFG_JOB/supervisor.pid"
printf 'CFG supervisor %s; output %s\n' "$!" "$CFG_JOB"
