#!/bin/bash
set -uo pipefail
B=/srv/opentallas-scratch2/claude/codex-xfin-local-relief-1400
K=/srv/opentallas-scratch2/claude/codex-xfin-1101/kits/ot_s81dv_eng_finish_c155
P=$B/grt_R4_140_probe
if [ -e "$P" ]; then echo 'Refuse existing probe output'; exit 9; fi
mkdir -p "$P/inputs" "$P/logs" "$P/reports" "$P/objects"
cp "$B/prep_R4_140/local_relief_prep.odb" "$P/inputs/local_relief_prep.odb"
cp "$K/run/results/asap7/kl_ot_s81dv_eng_finish_c155/base/4_cts.sdc" "$P/inputs/4_cts.sdc"
cp "$B/relief_probe.tcl" "$P/relief_probe.tcl"
docker run --rm --name codex-xfin-relief-grt-50-$$ --memory=8g --memory-swap=8g --cpus=8 -v "$K":/work:ro -v "$P":/probe -e HUID=$(id -u) -e HGID=$(id -g) -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 -I /work/kit_modes.py check /work --step grt --session "tc bc" --hold-repair > /probe/modes.log 2>&1 || exit 8; python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /probe/mm_patch.log 2>&1 || exit 9; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/probe/run RESULTS_DIR=/probe/inputs LOG_DIR=/probe/logs REPORTS_DIR=/probe/reports OBJECTS_DIR=/probe/objects NUM_CORES=8 GLOBAL_ROUTE_ARGS="-congestion_iterations 50" RUN_SCRIPT=/probe/relief_probe.tcl RUN_LOG_NAME_STEM=combined_probe run; rc=$?; chown -R "$HUID:$HGID" /probe; exit "$rc"' > "$P/native.log" 2>&1
RC=$?
if ! grep -q RELIEF_INITIAL_PROBE_DONE_NO_REPAIR_NO_STA_NO_DRT "$P/native.log"; then RC=2; fi
printf '%s\n' "$RC" > "$P/exit.txt"
exit "$RC"
