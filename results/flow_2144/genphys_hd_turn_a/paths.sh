#!/bin/bash
set -eu
B=/srv/opentallas-scratch2/claude/codex-genphys-ab-2144/seq_tt
cat > "$B/seq_paths.tcl" <<'TCL'
source /work/postcts_gate.tcl
report_checks -path_delay max -group_path_count 3 -format full_clock_expanded -fields {slew cap fanout input_pin net} > /work/diag_paths_setup.rpt
report_checks -path_delay min -group_path_count 3 -format full_clock_expanded -fields {slew cap fanout input_pin net} > /work/diag_paths_hold.rpt
TCL
for C in TT FF; do
 docker run --rm --cpus 2 --memory 8g --memory-swap 8g -v "$B":/work -e OT_POSTCTS_GRT=1 -e OT_CORNER=$C -e ODB=/work/run/results/asap7/dp_hd_turn_a/base/5_1_grt.odb openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /work/seq_paths.tcl > /work/diag_paths_$OT_CORNER.log 2>&1; mv /work/diag_paths_setup.rpt /work/diag_paths_setup_$OT_CORNER.rpt; mv /work/diag_paths_hold.rpt /work/diag_paths_hold_$OT_CORNER.rpt; chown -R 1000:1000 /work'
done
