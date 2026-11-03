#!/bin/bash
# DIE-KV-61/grt (= DIE-KV-58 grt_st.sh / DIE-KV-47-SD grt_b.sh): combo whole-die GRT (die_trial signal kit route.v M4-M7 + die clock ctree M8-M9)
# in ONE global_route, 50 congestion iterations, ADJ 0.75 / ADJ7 0 (results/land_kv_1027/mk_combo_kv.py), plus both-edge duty + SDF.
# usage: grt.sh V CORNER CLKDIR   (CLKDIR: ctree.v + ctree.tcl of the clock to route; tree.json from the kit)
V=$1; C=$2; SRC=$3; B=/home/ubuntu/scratch-root/claude/die-kv-61/grt; R=$B/grt_$V; K=$B/tree_kv61/kit; CK=$R/clk; O=$R/out_$C
mkdir -p $CK $O
cp $SRC/ctree.v $K/clock/tree.json $CK/; cp $SRC/ctree.tcl $CK/ctree_ck89.tcl
CORNER=$C ADJ=0.75 ADJ7=0 python3 $B/mk_combo_kv.py $K $CK $O || exit 1
python3 - $O/combo.tcl <<"PY"
import sys
p = sys.argv[1]; s = open(p).read()
extra = r"""set fh [open /out/duty_$::env(CORNER).txt w]
foreach p [get_ports t_*] { puts $fh "D [get_full_name $p] [expr {833.333 - [get_property $p slack_max_rise]}] [expr {833.333 - [get_property $p slack_max_fall]}] [get_property $p slew_max_rise] [get_property $p slew_max_fall]" }
close $fh
write_sdf -divider / /out/die_$::env(CORNER).sdf
puts OT_DONE
"""
assert s.count("puts OT_DONE") == 1
open(p, "w").write(s.replace("puts OT_DONE\n", extra))
PY
docker run --rm --name dkv61-grt-$V-$C --memory=48g --memory-swap=48g --cpus=8 -e CORNER=$C \
  -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM -v $K:/work:ro -v $O:/out openroad/orfs:latest \
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -threads 8 -exit /out/combo.tcl > /out/combo_$C.log 2>&1; echo EXIT \$? >> /out/combo_$C.log; chown -R 1000:1000 /out"
grep -E "EXIT|Total overflow" $O/combo_$C.log | tail -n 2
