#!/bin/bash
# HBM-CORES-REBAL-11: lanes_plain canon (MLAT5/WCOPY1, keep + copy guides + relay guides) and programme_store_r10 kits
# from C24 plan 3ab76af4 (DIE-HBM-10) with the plan-fixed SRAM arrays + driver_rects of c24_side.json.
# lanes_plain gets the same die-local oneclk delta as lanes__canon (REBAL-4 lanes_oneclk.py, MOD swapped).
set -eu
W=/srv/opentallas-scratch2/claude/wt/hbm-cores-rebal-11; R=/srv/opentallas-scratch2/claude/hbm-cores-rebal-11
R4=/srv/opentallas-scratch2/claude/hbm-cores-rebal-4; C24=/srv/opentallas-scratch2/claude/die-hbm-10/c24
LP=ot_hbm_su_static_pgslice_lg__lanes_plain__canon_663526; PS=ot_hgi_sfu_programme_store_r10
P=$R/c24_lp; V=$R/views_c24lp.json; F=$R/fixes; TAG=${TAG:-_c24_m5w1gr}
RELAY=$W/results/hbm_cores_rebal_10_1028/relay_lanes_canon.json
rm -rf $P $F $R/slices; cp -r $C24 $P; cp -r $R4/fixes $F; mkdir -p $R/kits $R/preflight
sha256sum $C24/die_plan.json | cut -c1-8 > $R/c24_src_sha.txt
# 1) oneclk delta for lanes_plain (lanes_oneclk.py with MOD = lanes_plain canon)
sed "s/^MOD = .*/MOD = \"$LP\"/" $R4/lanes_oneclk.py > $R/bin/lp_oneclk.py
python3 $R/bin/lp_oneclk.py $P $F/canon_wrappers/$LP.sv $F/canon_wrappers > $R/lp_oneclk.log 2>&1; cat $R/lp_oneclk.log
# 2) MLAT5 / WCOPY1 on the lanes4 core instance (as REBAL-10 mk_canon_m5w1r.sh)
python3 - $F/canon_wrappers/$LP.sv 5 1 <<PY
import sys
from pathlib import Path
p = Path(sys.argv[1]); t = p.read_text()
old = "    ot_hbm_su_pg_lanes4_core u_core ("
assert t.count(old) == 1, "canon wrapper core instance not found once"
t = t.replace(old, f"    ot_hbm_su_pg_lanes4_core #(.MLAT({sys.argv[2]}),.WCOPY({sys.argv[3]})) u_core (")
p.write_text("// HBM-CORES-REBAL-11: lane build MLAT %s WCOPY %s passed to the generated core (mk_c24.sh)\n" % tuple(sys.argv[2:4]) + t)
PY
cd $W/physical/die_plan/hbm_arch_cores
python3 views_b2r2.py --plan $P/die_plan.json --out $V > $R/views_c24lp.log 2>&1
# 3) slices (12.2a1 pushdown, island ft pins 1.08) + C24 driver_rects + plan-fixed macro tables
python3 $W/results/die_hbm_kits_1027/mk_c20.py $P $V $R/slices $R/kits $W $LP,$PS --islands-only --ft-pin-dx-um 1.08 > $R/mk_slices.log 2>&1
python3 $R/bin/c24_slices_dr.py $W $P/c24_side.json $R/slices $R $LP,$PS
view() { python3 -c "import json;print([v[\"view\"] for v in json.load(open(\"$V\"))[\"view_list\"] if v[\"module\"]==\"$1\"][0])"; }
rm -rf $R/kits/${LP}_*-$TAG $R/kits/${PS}_*-_c24
python3 $F/run_canon_kit.py $W $F --views $V --view $(view $LP) --out $R/kits --master-slice $R/slices --trial --tag $TAG \
  --macro-placement $R/mp_$LP.json --macro-inst-fmt "{k}" --macro-reg-guide g_wcopy --macro-reg-guide-um 15 \
  --relay-reg-guide $RELAY > $R/kits/gen_$LP$TAG.log 2>&1; echo "$LP rc=$?"
python3 gen_core_kit_hbm.py --views $V --view $(view $PS) --out $R/kits --master-slice $R/slices --trial --tag _c24 \
  --macro-placement $R/mp_$PS.json --macro-inst-fmt "{k}" > $R/kits/gen_$PS.log 2>&1; echo "$PS rc=$?"
bash $W/results/die_hbm_kits_1027/pf_all.sh $P $R/kits $R/preflight $W
