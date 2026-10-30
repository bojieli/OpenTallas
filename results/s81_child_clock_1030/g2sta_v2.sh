#!/bin/bash
# Read-only GRT STA: exact kit corner libraries/SDC/RC, standard FF overlay,
# then related-pair CPPR skew. No kit verdict or physical checkpoint is overwritten.
set -euo pipefail
K=$1; O=$2
mkdir -p "$O"
test ! -e "$O/result_tt.log"
B=$(find "$K/run/results" -name 5_1_grt.odb -print -quit); test -n "$B"
python3 - "$K" "$O" <<'PY'
import sys
from pathlib import Path
k,o=map(Path,sys.argv[1:]);s=(k/'postcts_gate.tcl').read_text();s=s.replace('/work/postcts_gate_', '/g2/postcts_gate_')
s+='''
if {$ot_pg_C eq "FF"} {
 set g2_clock_names {}
 foreach g2_ck [all_clocks] {
  foreach g2_src [get_property $g2_ck sources] {lappend g2_clock_names [get_full_name $g2_src]}
 }
 set g2_din {}
 foreach g2_port [all_inputs] {
  if {[lsearch -exact $g2_clock_names [get_full_name $g2_port]] < 0} {lappend g2_din $g2_port}
 }
 if {[llength $g2_din]} {set_input_delay -min -40 -clock [lindex $ot_pg_virtual 0] $g2_din}
 if {[llength [all_outputs]]} {set_output_delay -min 0 -clock [lindex $ot_pg_virtual 0] [all_outputs]}
}
puts [format "G2_STD %s setup_ps %.3f hold_ps %.3f parasitics %s" $ot_pg_C [expr {[sta::worst_slack_cmd max]*1e12}] [expr {[sta::worst_slack_cmd min]*1e12}] $ot_pg_mode]
report_checks -path_delay max -group_path_count 3 -format full_clock_expanded > /g2/max_${ot_pg_c}.rpt
report_checks -path_delay min -group_path_count 3 -format full_clock_expanded > /g2/min_${ot_pg_c}.rpt
set ::env(CORNER) $ot_pg_C
set ::env(OT_PS_OUT) /g2/pair_${ot_pg_c}.tsv
source /work/pair_skew.tcl
'''
(o/'g2sta.tcl').write_text(s)
PY
for C in ${G2_CORNERS:-TT FF}; do
 docker run --rm --name "codex-s81-g2sta-$C-$$" --cpus 4 --memory 28g --memory-swap 28g \
 -v "$K":/work:ro -v "$O":/g2 -w /work -e OT_CORNER="$C" -e OT_POSTCTS_GRT=1 \
 -e ODB="/work/${B#"$K/"}" openroad/orfs:asap7lock bash -lc \
 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /g2/g2sta.tcl' > "$O/result_${C,,}.log" 2>&1
 done
 grep -E 'G2_STD|OT_PS .*worst|OT_POSTCTS_GATE' "$O"/result_*.log
