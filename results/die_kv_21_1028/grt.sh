#!/bin/bash
# DIE-KV-21 (= DIE-KV-12 recipe): combo die GRT0 incl clock (DIE-KV-11 grt_rt.sh recipe: land-kv-1027/mk_combo_kv.py ADJ 0.75 / ADJ7 0, M8-M9 clock,
# 50 congestion iterations, -critical_nets_percentage 0) on kit_<V>, one corner; plus the DIE-KV-11 duty readout (rise AND fall
# arrival per tap, root driven by vclk) and a SPEF of the routed die (for the MPW run on the die netlist with real DFF pins).
# usage: grt.sh V CORNER
V=$1; C=$2; R=/srv/opentallas-scratch2/claude/die-kv-21-1028; K=$R/kit_$V; CK=$R/clk_$V; O=$R/out_${V}_$C
LK=/srv/opentallas-scratch2/claude/land-kv-1027
mkdir -p $CK $O
mkdir -p $CK; cp $K/clock/ctree.v $K/clock/tree.json $CK/; cp $K/clock/ctree.tcl $CK/ctree_ck89.tcl
CORNER=$C ADJ=0.75 ADJ7=0 python3 $LK/mk_combo_kv.py $K $CK $O || exit 1
python3 - $O/combo.tcl <<'PY'
import sys
p = sys.argv[1]; s = open(p).read()
extra = r'''set fh [open /out/duty_$::env(CORNER).txt w]
foreach p [get_ports t_*] { puts $fh "D [get_full_name $p] [expr {833.333 - [get_property $p slack_max_rise]}] [expr {833.333 - [get_property $p slack_max_fall]}] [get_property $p slew_max_rise] [get_property $p slew_max_fall]" }
close $fh
write_sdf -divider / /out/die_$::env(CORNER).sdf
puts OT_DONE
'''
assert s.count("puts OT_DONE") == 1
open(p, "w").write(s.replace("puts OT_DONE\n", extra))
PY
docker run --rm --name dkv21-grt-$V-$C --memory=48g --memory-swap=48g --cpus=8 -e CORNER=$C \
  -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM -v $K:/work:ro -v $O:/out openroad/orfs:latest \
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -threads 8 -exit /out/combo.tcl > /out/combo_$C.log 2>&1; echo EXIT \$? >> /out/combo_$C.log; chown -R 1000:1000 /out"
grep -E "EXIT|Total overflow" $O/combo_$C.log | tail -n 2
