#!/bin/bash
# DIE-HEAD-51 helper st: die clock event l48w-st = l48c ot_clk kit + 1251 START stage taps (st_ctree.py patch of ctree.v/.tcl),
# then clk_l48c.sh steps: run_clock (clock-only) + grt.sh combo GRT TT/FF, with the FLOW-ONEMODEL-2 both-edge readout added.
set -u; R=/srv/opentallas-scratch2/claude/die-head-48; S=$R/clk_st51; K=$S/kit_l48w_st/kit
if [ "${1:-}" = clock ]; then MEM=8 bash $K/run_clock.sh; echo CLOCK rc=$?; grep -h EXIT $K/clock/ctree_*.log; exit; fi
C=$1; CK=$S/ck; O=$S/out_$C; mkdir -p $CK $O
cp $K/clock/ctree.v $K/clock/tree.json $CK/; cp $K/clock/ctree.tcl $CK/ctree_ck89.tcl
CORNER=$C ADJ=0.75 ADJ7=0.75 python3 $R/clk/mk_combo_kv.py $K $CK $O || exit 1
python3 - $O/combo.tcl $S/readout.tcl <<"PY"
import sys
p = sys.argv[1]; s = open(p).read(); r = open(sys.argv[2]).read()
extra = r"""set fh [open /out/duty_$::env(CORNER).txt w]
foreach p [get_ports t_*] { puts $fh "D [get_full_name $p] [expr {833.333 - [get_property $p slack_max_rise]}] [expr {833.333 - [get_property $p slack_max_fall]}] [get_property $p slew_max_rise] [get_property $p slew_max_fall]" }
close $fh
""" + r + "\nwrite_sdf -divider / /out/die_$::env(CORNER).sdf\nputs OT_DONE\n"
assert s.count("puts OT_DONE") == 1
open(p, "w").write(s.replace("puts OT_DONE\n", extra))
PY
docker run --rm --name dh51st-clkst-$C --memory=64g --memory-swap=64g --cpus=8 -e CORNER=$C \
  -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM -v $K:/work:ro -v $O:/out openroad/orfs:latest \
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -no_init -threads 8 -exit /out/combo.tcl > /out/combo_$C.log 2>&1; echo EXIT \$? >> /out/combo_$C.log; chown -R 1000:1000 /out"
grep -E "EXIT|Total overflow|Maximum resident" $O/combo_$C.log | tail -n 3
