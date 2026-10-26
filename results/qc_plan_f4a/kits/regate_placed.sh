#!/bin/bash
# QC-PLAN-F4A re-gate on the PLACED geometry (task 3): dump the MIF0 3_place.odb (kit dump_geo_m0.tcl, docker probe 8 GB cap)
# on the kit host, then (here) f4_g4c (G1 track / G2 / G3 / G4 strict + router-proof L1 + uf_asbuilt band) (G5 SRAM structure in column-view form;
# the stock r3 su_kit_gate re-plans its own tree and puts the G5 pin column beside the E/W edge = m2 pin face). Same plan model + flags as the planned run.
# usage: regate_placed.sh KITHOST KITROOT   (kits KITROOT/<module>_f4a)
set -euo pipefail
H=$1; KR=$2
W=$(cd "$(dirname "$0")/../../.." && pwd); R=$W/results/qc_plan_f4a; P=$R/placed; mkdir -p $P
LIB=/srv/opentallas-scratch2/claude/master-plan-r4-1026/su_refloor
UF=$W/results/master_plan_r5/su_unequal/su_tree_uf.py
SR=$W/physical/asap7_memory_macros_v2_col
for m in qfd_dv_s8x_vmr qfd_dv_s8_crh_rp1; do
  n=$([ $m = qfd_dv_s8x_vmr ] && echo vmr || echo rp1); K=$KR/${m}_f4a
  ssh -o ControlPath=none $H "cd $K && O=\$(ls run/results/asap7/*/base/3_place.odb) && docker run --rm -m 8g --cpus 2 -v $K:/work -e ODB=/work/\$O -e OUT=/work/placed.geo openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -exit /work/dump_geo_m0.tcl' > dump_geo.log 2>&1; grep DUMP_GEO dump_geo.log"
  scp -q -o ControlPath=none $H:$K/placed.geo $P/${n}_placed.geo
  # meta for G1: macro rect from the placed DB, orientation from the kit's fixed sites (asserted equal to the plan sites)
  python3 - $P/${n}_placed.geo $R/geo/${n}_f4s.geo.json <<'PY'
import json, sys
geo, plan = sys.argv[1], json.load(open(sys.argv[2]))
mac = [l.split() for l in open(geo) if l.startswith("MACRO")]
pm = {m[0].replace("\\", ""): m for m in plan["macros"]}
out = []
for f in mac:
    nm = f[1].replace("\\", ""); p = pm[nm]
    box = [float(v) for v in f[3:7]]
    assert all(abs(a - b) < 1e-3 for a, b in zip(box, p[2])), (nm, box, p[2])
    out.append([f[1], f[2], box, p[3], [float(f[8]), float(f[9])]])
json.dump(dict(macros=out, source=f"placed DB dump; orient from the kit fixed sites = plan {sys.argv[2]}"), open(geo + ".json", "w"), indent=1)
print("META", geo, len(out), "macros = plan sites")
PY
  (cd $P && prlimit --as=16000000000 python3 -u $R/f4_g4c.py ${n}_placed_g4c $P/${n}_placed.geo 6 $LIB $UF $SR ${n}_placed_g4c --l1 wp --l2 wp --l3 wp --clear L1 --isl-out-pinwin > ${n}_placed_g4c.log 2>&1; grep -h "VERDICT\| BAND" ${n}_placed_g4c.log | cut -c1-260) &
done
wait
