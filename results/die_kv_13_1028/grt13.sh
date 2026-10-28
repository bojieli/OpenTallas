#!/bin/bash
# DIE-KV-13: DIE-KV-12 grt.sh (combo die GRT0 incl clock, mk_combo_kv ADJ .75/ADJ7 0, 50 it) on kit_inv_r150, re-run to dump
# MEASURED falling-edge arrivals (F per tap port, M per clock cell, FLOW-GEN-1 6672c5921 form) beside the T/N rise rows, and
# the max clock slew at both edges (COORD 09:38 slew finding).  usage: grt13.sh CORNER
C=$1; V=inv_r150; R12=/srv/opentallas-scratch2/claude/die-kv-12-1028; K=$R12/kit_$V; CK=$R12/clk_$V
R=/srv/opentallas-scratch2/claude/die-kv-13-1028; O=$R/out_${V}_$C; LK=/srv/opentallas-scratch2/claude/land-kv-1027
mkdir -p $O
CORNER=$C ADJ=0.75 ADJ7=0 python3 $LK/mk_combo_kv.py $K $CK $O || exit 1
python3 - $O/combo.tcl <<'PY'
import sys
p = sys.argv[1]; s = open(p).read()
n = [l for l in s.splitlines() if l.startswith("foreach i [get_cells ck_*]") and '"N ' in l]
assert len(n) == 1, len(n)
f = (n[0] + "\n" + 'foreach p [get_ports t_*] { puts $fh "F [get_full_name $p] [expr {833.333 - [get_property $p slack_max_fall]}] [get_property $p slack_min_fall]" }\n'
     + 'foreach i [get_cells ck_*] { set q [get_pins [get_full_name $i]/Y]; puts $fh "M [string range [get_full_name $i] 3 end] [get_property $q arrival_max_fall] [get_property $q arrival_min_fall]" }\n'
     + 'set smr 0; set smf 0; foreach i [get_cells ck_*] { foreach pn {A Y} { set q [get_pins [get_full_name $i]/$pn]; set r [get_property $q slew_max_rise]; set fl [get_property $q slew_max_fall]; if {$r > $smr} {set smr $r}; if {$fl > $smf} {set smf $fl} } }\n'
     + 'foreach p [get_ports t_*] { set r [get_property $p slew_max_rise]; set fl [get_property $p slew_max_fall]; if {$r > $smr} {set smr $r}; if {$fl > $smf} {set smf $fl} }\n'
     + 'puts "OT_SLEWMAX rise $smr fall $smf"')
s = s.replace(n[0], f, 1)
open(p, "w").write(s)
PY
docker run --rm --name dkv13-grt-$C --memory=48g --memory-swap=48g --cpus=8 -e CORNER=$C \
  -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM -v $K:/work:ro -v $O:/out openroad/orfs:latest \
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -threads 8 -exit /out/combo.tcl > /out/combo_$C.log 2>&1; echo EXIT \$? >> /out/combo_$C.log; chown -R 1000:1000 /out"
grep -E "EXIT|Total overflow|OT_SLEWMAX" $O/combo_$C.log | tail -n 3
python3 $R/tta_fall.py $CK/tree.json $O/arr_$C.txt $C $R/proof_fall/tap_arrivals_$C.json
