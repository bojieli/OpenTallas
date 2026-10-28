#!/bin/bash
# DIE-KV-12: OpenSTA min-pulse-width (report_check_types -min_pulse_width, both clock edges propagated) on the die netlist with
# real register clock pins (kit sta/die_top.v stand-ins + DFFHQNx1 + OT_CLAT, each partition clock pin on its own built tap),
# routed clock RC from the combo GRT SPEF, spice clock calibration as a clock-network derate (x1.0485 TT / x1.0552 FF).
# usage: mpw.sh V CORNER [SUFFIX]   (MAXONLY=1: early = late = combo max delays)
V=$1; C=$2; X=${3:-}; R=/srv/opentallas-scratch2/claude/die-kv-12-1028; K=$R/kit_$V; O=$R/mpw_${V}_$C$X
mkdir -p $O
python3 $R/mk_mpw.py $K $R/clk_$V $R/out_${V}_$C/die_$C.sdf $C $O > $O/mk.log 2>&1 || { cat $O/mk.log; exit 1; }
cat $O/mk.log
python3 - $K $C $O <<'PY'
import sys
sys.path.insert(0, "/srv/opentallas-scratch2/claude/die-kv-12-1028/qc11/tools/die_plan")
import glob, die_sta
k, c, o = sys.argv[1:4]
cells = die_sta.clat_cells_used(glob.glob(k + "/sta/parts/*/6_final.v"))
open(o + "/clat_%s.lib" % c, "w").write(die_sta.clat_lib(cells, c))
bh = die_sta.bhold_cells_used(glob.glob(k + "/sta/parts/*/6_final.v"))
open(o + "/bhold.lib", "w").write(die_sta.bhold_lib(bh))
print("bhold cells", sorted(bh))
print("clat cells", sorted(cells))
PY
S=$([ $C = TT ] && echo 1.0485 || echo 1.0552)
{
echo 'foreach f [glob $::env(LIBDIR)/*RVT_$::env(CORNER)_nldm*.lib*] { read_liberty $f }'
echo "read_liberty /out/clat_$C.lib"
echo "read_liberty /out/bhold.lib"
for f in $K/sta/parts/*/6_final.v; do echo "read_verilog /work/sta/parts/$(basename $(dirname $f))/6_final.v"; done
echo "read_verilog /out/die_mpw.v"
echo "link_design die_mpw"
echo "read_sdf /out/die_$C.sdf"
echo "report_annotated_delay -list_not_annotated -max_lines 5"
echo "create_clock -name clk -period 833.333 [get_ports clk]"
echo "set_propagated_clock [all_clocks]"
echo "set_driving_cell -lib_cell BUFx24_ASAP7_75t_R -pin Y [get_ports clk]"
echo "set_timing_derate -clock -cell_delay -early $S"
echo "set_timing_derate -clock -cell_delay -late $S"
echo "set_timing_derate -clock -net_delay -early $S"
echo "set_timing_derate -clock -net_delay -late $S"
echo 'puts "OT_DFF_CLK [llength [get_pins -hierarchical */CLK]]"'
echo 'puts "OT_MPW_WORST_BEGIN"'
echo 'report_check_types -min_pulse_width -verbose'
echo 'puts "OT_MPW_WORST_END"'
echo 'puts "OT_MPW_VIOL_BEGIN"'
echo 'report_check_types -min_pulse_width -violators'
echo 'puts "OT_MPW_VIOL_END"'
echo 'puts OT_DONE'
} > $O/mpw.tcl
docker run --rm --name dkv12-mpw-$V-$C$X --memory=96g --memory-swap=96g --cpus=8 -e CORNER=$C \
  -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM -v $K:/work:ro -v $O:/out openroad/orfs:latest \
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v sta -no_init -exit /out/mpw.tcl > /out/mpw_$C.log 2>&1; echo EXIT \$? >> /out/mpw_$C.log; chown -R 1000:1000 /out"
grep -E "EXIT|OT_DFF_CLK|Maximum resident" $O/mpw_$C.log
