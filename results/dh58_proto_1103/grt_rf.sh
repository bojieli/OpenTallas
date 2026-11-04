#!/bin/bash
# DH58-PROTO: combo die GRT (signal kit M4-M7 + die clock M8-M9 in one global_route, 50 it; mk_combo_kv.py, ADJ 0.75) on
# the l48rf kit, with the both-edge readout (die_trial readout --cells ck_*) + duty + die SDF = DIE-HEAD-51 clk_sth.sh form.
# usage: grt_rf.sh V CORNER   (kit = $P/kit_V/kit, readout = $P/readout_V.tcl, out = $P/out_V_CORNER)
set -u; P=/srv/opentallas-scratch2/claude/dh58/proto; R=/srv/opentallas-scratch2/claude/die-head-48
V=$1; C=$2; K=$P/kit_$V/kit; CK=$P/ck_$V; O=$P/out_${V}_$C; mkdir -p $CK $O
cp $K/clock/ctree.v $K/clock/tree.json $CK/; cp $K/clock/ctree.tcl $CK/ctree_ck89.tcl
CORNER=$C ADJ=0.75 ADJ7=0.75 python3 $R/clk/mk_combo_kv.py $K $CK $O || exit 1
python3 - $O/combo.tcl $P/readout_$V.tcl <<"PY"
import sys
p = sys.argv[1]; s = open(p).read(); r = open(sys.argv[2]).read()
extra = r"""set fh [open /out/duty_$::env(CORNER).txt w]
foreach p [get_ports t_*] { puts $fh "D [get_full_name $p] [expr {833.333 - [get_property $p slack_max_rise]}] [expr {833.333 - [get_property $p slack_max_fall]}] [get_property $p slew_max_rise] [get_property $p slew_max_fall]" }
close $fh
""" + r + "\nwrite_sdf -divider / /out/die_$::env(CORNER).sdf\nputs OT_DONE\n"
assert s.count("puts OT_DONE") == 1
open(p, "w").write(s.replace("puts OT_DONE\n", extra))
PY
docker run --rm --name dh58proto-grt-$V-$C --memory=10g --memory-swap=10g --cpus=8 -e CORNER=$C \
  -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM -v $K:/work:ro -v $O:/out openroad/orfs:latest \
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -no_init -threads 8 -exit /out/combo.tcl > /out/combo_$C.log 2>&1; echo EXIT \$? >> /out/combo_$C.log; chown -R 1000:1000 /out"
grep -E "EXIT|Total overflow|Maximum resident" $O/combo_$C.log | tail -n 3
