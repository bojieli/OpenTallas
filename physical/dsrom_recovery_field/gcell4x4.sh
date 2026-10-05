#!/bin/bash
# 4x4-GCell use/cap windows of a routed screen block (DS-ROM recovery lever "field"): re-runs ORFS global routing on
# the block's 4_cts.odb with the platform's own layer adjustments (asap7 platform defaults: M2-M7, adjustment 0.25, clock M4-M7) and dumps per 4x4
# window capacity/usage per layer, then summarises max use/cap per layer and the GRT overflow.
#   gcell4x4.sh <orfs dir (keep-workdir/orfs)> <out.json>
set -e
O=$(readlink -f $1); J=$2
odb=$(ls $O/results/asap7/*/base/4_cts.odb)
cat > $O/gcell4x4.tcl <<'TCL'
read_db ODBPATH
set_global_routing_layer_adjustment M2-M7 0.25
set_routing_layers -clock M4-M7
set_routing_layers -signal M2-M7
global_route -congestion_iterations 30 -verbose
set blk [ord::get_db_block]
set out [open /work/gcell_usage.txt w]
set grid [$blk getGCellGrid]
set gx [$grid getGridX]; set gy [$grid getGridY]
set tech [ord::get_db_tech]
foreach ln {M2 M3 M4 M5 M6 M7} {
  set layer [$tech findLayer $ln]
  set nx [llength $gx]; set ny [llength $gy]
  for {set j 0} {$j < $ny} {incr j 4} {
    set row {}
    for {set i 0} {$i < $nx} {incr i 4} {
      set cap 0; set use 0
      for {set jj $j} {$jj < min($j+4,$ny)} {incr jj} {
        for {set ii $i} {$ii < min($i+4,$nx)} {incr ii} {
          set cap [expr {$cap + [$grid getCapacity $layer $ii $jj]}]
          set use [expr {$use + [$grid getUsage $layer $ii $jj]}]
        }
      }
      lappend row "$cap/$use"
    }
    puts $out "L $ln $j [join $row { }]"
  }
}
close $out
TCL
rel=${odb#$O/}
sed -i "s|ODBPATH|/work/$rel|" $O/gcell4x4.tcl
docker run --rm -v $O:/work openroad/orfs:latest bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; cd /work && openroad -exit -no_init -threads 8 gcell4x4.tcl 2>&1 | grep -E 'GRT-0096|^M[0-9]|^Total|overflow' ; true" > $O/gcell4x4.log 2>&1 || true
python3 - $O $J <<'PY'
import json, sys
o, j = sys.argv[1], sys.argv[2]
per = {}
for ln in open(o + "/gcell_usage.txt"):
    f = ln.split()
    e = per.setdefault(f[1], dict(windows=0, max_use_over_cap=0.0, over_0p9=0, over_1=0))
    for c in f[3:]:
        cap, use = (float(x) for x in c.split("/"))
        if cap <= 0:
            continue
        r = use / cap
        e["windows"] += 1; e["over_0p9"] += r > 0.9; e["over_1"] += r > 1.0
        e["max_use_over_cap"] = max(e["max_use_over_cap"], round(r, 4))
log = open(o + "/gcell4x4.log").read()
json.dump(dict(per_layer=per, worst_window_use_cap=max(v["max_use_over_cap"] for v in per.values()),
               grt_log=log.strip().splitlines()[-12:]), open(j, "w"), indent=1)
print(j, max(v["max_use_over_cap"] for v in per.values()))
PY
