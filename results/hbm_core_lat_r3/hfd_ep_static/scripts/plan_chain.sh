#!/bin/bash
# HBM-CORE-LAT-R3 hfd_ep_static: placed phase-1 kit -> GEO -> core_infra_htree plan -> phys_gate (uf_phys3) prediction
#   -> plan record -> core_plan_to_infra slice (slice2/<module>.json).  Plan geometry only; no CTS, no measurement.
# usage: plan_chain.sh KIT OUTDIR [SPLITS=2,2,4,4] [SMAX=70]
set -euo pipefail
K=$(cd "$1" && pwd -P); O=$2; SPL=${3:-2,2,4,4}; SMAX=${4:-70}
D=/srv/opentallas-scratch2/claude/hbm-core-lat-r3-ep; W=/srv/opentallas-scratch2/claude/wt/hbm-core-lat-r3-ep
mkdir -p $O; O=$(cd $O && pwd -P)
R=$(ls -d $K/run/results/asap7/*/base)
docker run --rm --memory=8g -v $K:/work -v $D:/d -v $O:/o openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; \
  ODB=/work/run/results/asap7/hbc_hfd_ep_static/base/3_place.odb OUT=/o/geo.txt CLK=clk ENTRY='125.28 187.92' openroad -exit /d/bin/dump_geo_core.tcl 2>&1 | grep DUMP_GEO; \
  ODB=/work/run/results/asap7/hbc_hfd_ep_static/base/2_4_floorplan_pdn.odb OUT=/o/sites.txt openroad -exit /d/bin/dump_sites.tcl 2>&1 | grep DUMP_SITES; chown -R $(id -u):$(id -g) /o"
cd $O
python3 $W/tools/die_plan/core_infra_htree.py geo.txt plan.tcl --libtt $D/lib/invbuf_tt.lib --libff $D/lib/invbuf_ff.lib --splits $SPL --smax $SMAX > htree.log 2> htree.err || { tail -5 htree.err; exit 1; }
echo '{"seg_um": {}}' > asbuilt_empty.json
OT_PHYS_FIT=$W/results/model_refit3_1026/uf_phys3_v1.json python3 $W/results/qc_su_prog_l1_1026/phys_gate.py plan.tcl asbuilt_empty.json geo.txt $D/lib pred_uf3.json | tee pred_uf3.line
python3 $D/bin/htree_record.py plan.tcl plan.tcl.json geo.txt pred_uf3.json record.json --name hfd_ep_static_ht_$(echo $SPL | tr , _)
mkdir -p slice2
python3 $W/tools/die_plan/core_plan_to_infra.py record.json --sites sites.txt --module hfd_ep_static --clock-port clk --die hbm --outline 250.56,375.84 --band info --out slice2/hfd_ep_static.json > convert.log 2>&1 || { tail -5 convert.log; exit 1; }
tail -3 convert.log
# macro clock pins: same-stage sibling leaves (core_infra.named_tree_report convention) -> load_class macro
python3 - <<PY
import json
r = json.load(open("record.json")); s = json.load(open("slice2/hfd_ep_static.json"))
mac = {"mp_ck_" + n for n in r.get("macro_leaves", [])}
n = 0
for l in s["core_tree"]["leaves"]:
    if l["node"] in mac: l["load_class"] = "macro"; n += 1
s["plan_conversion"]["macro_leaves"] = n
json.dump(s, open("slice2/hfd_ep_static.json", "w"), indent=1)
print("SLICE2", len(s["core_tree"]["nodes"]), "nodes", len(s["core_tree"]["leaves"]), "leaves", n, "macro leaves", s["plan_conversion"]["displacement_um"])
PY
