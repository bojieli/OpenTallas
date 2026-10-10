#!/bin/bash
# mtp-lead 2026-10-09: run_export.sh MASTER BASE OUT  (BASE = the installed ORFS base dir with 6_final.{odb,sdc,spef})
# SS / FF / TT timing models + abstract LEF in the ORFS container, three corners in parallel; records input hashes.
set -e
M=$1; B=$2; O=$3
here=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$O"
python3 "$here/mk_export.py" "$M" "$O"
sha256sum "$B/6_final.odb" "$B/6_final.sdc" "$B/6_final.spef" > "$O/input_sha256.txt"
for c in ss ff tt; do
  docker run --rm -u "$(id -u):$(id -g)" -v "$B:/in:ro" -v "$O:/w" openroad/orfs:asap7lock bash -lc \
    "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -exit /w/export_$c.tcl" > "$O/export_$c.log" 2>&1 &
done
wait
grep -h "OT_.*_WS\|OT_EXPORT_DONE" "$O"/export_*.log
ls -la "$O"
