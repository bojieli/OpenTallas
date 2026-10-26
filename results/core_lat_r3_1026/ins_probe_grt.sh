#!/bin/bash
# CORE-LAT-R3: GRT=1 runs its own global_route M2-M5 on the CTS odb (as NUMBER-CHECK 06:59). S81-CORE-LAT diagnostic insertion probe (no flow change): kit postcts_gate.tcl on 4_cts.odb (or $3) at TT and FF,
# placement RC unless GRT=1, plus ALL register clock-pin arrivals (min/mean/max/n) -> KIT/ins_probe_{tt,ff}.json.
#   ins_probe.sh KITDIR [MEM_GB=8] [ODB_GLOB=4_cts.odb]
set -e
K=$(cd "$1" && pwd); MEM=${2:-8}; G=${3:-4_cts.odb}
sed -e 's#/work/postcts_gate_${ot_pg_c}.json#/work/ins_probe_pinreg_${ot_pg_c}.json#' \
    -e 's#!\[catch {estimate_parasitics -global_routing}\]#![catch {set_routing_layers -signal M2-M5 -clock M2-M5; global_route -allow_congestion; estimate_parasitics -global_routing}]#' \
    "$K/postcts_gate.tcl" > "$K/ins_probe.tcl"
cat >> "$K/ins_probe.tcl" <<'TCL'
set ot_all {}
foreach p [all_registers -clock_pins] { set a [ot_pinreg_arr $p [get_clocks clk]]; if {$a ne ""} { lappend ot_all $a } }
foreach p [get_pins -hierarchical -quiet */clk] { if {[[sta::sta_to_db_inst [$p instance]] getMaster] ne "" && [[[sta::sta_to_db_inst [$p instance]] getMaster] getType] eq "BLOCK"} { set a [ot_pinreg_arr $p [get_clocks clk]]; if {$a ne ""} { lappend ot_all $a } } }
set ot_all [lsort -real $ot_all]; set ot_n [llength $ot_all]
set fh [open /work/ins_probe_${ot_pg_c}.json w]
puts $fh [format "{\"corner\": \"%s\", \"parasitics\": \"%s\", \"all_n\": %d, \"all_min_ps\": %.2f, \"all_mean_ps\": %.2f, \"all_max_ps\": %.2f, \"pinreg_n\": %d, \"pinreg_mean_ps\": %.2f, \"pinreg_min_ps\": %.2f, \"pinreg_max_ps\": %.2f, \"bound_ps\": %.2f}" \
  $ot_pg_C $ot_pg_mode $ot_n [lindex $ot_all 0] [expr {[tcl::mathop::+ {*}$ot_all] / $ot_n}] [lindex $ot_all end] $n $mean [lindex $arr 0] [lindex $arr end] $ot_pg_bound]
close $fh
puts "OT_INS_PROBE $ot_pg_C $ot_pg_mode all n $ot_n min [lindex $ot_all 0] max [lindex $ot_all end] pinreg mean $mean"
TCL
ODB=$(ls $K/run/results/asap7/*/base/$G | tail -1); ODB=/work/${ODB#$K/}
VT=$(sed -n 's/^export OT_VCLK_TT = //p' $K/config.mk); VF=$(sed -n 's/^export OT_VCLK_FF = //p' $K/config.mk)
RC=$(sed -n 's/^export LAYER_PARASITICS_FILE = //p' $K/config.mk)
for C in TT FF; do
  docker run --rm --name "inspr-$(basename $K)-$C" --memory=${MEM}g -v "$K":/work -e OT_CORNER=$C -e ODB=$ODB -e OT_VCLK_TT=$VT -e OT_VCLK_FF=$VF \
    -e LAYER_PARASITICS_FILE=$RC -e OT_POSTCTS_GRT=${GRT:-0} -w /work openroad/orfs:asap7lock \
    bash -c "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; cd /OpenROAD-flow-scripts/flow && openroad -exit /work/ins_probe.tcl" > $K/ins_probe_$C.log 2>&1 || true
  grep -h "OT_INS_PROBE\|OT_POSTCTS_GATE" $K/ins_probe_$C.log || tail -n 5 $K/ins_probe_$C.log
done
