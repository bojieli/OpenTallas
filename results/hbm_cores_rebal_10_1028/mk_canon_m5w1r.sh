#!/bin/bash
# HBM-CORES-REBAL-10: lanes__canon kit at MLAT 5 + WCOPY 1, snapped macros (as REBAL-9 _c20ek2m_m5w1g), with
#  - the WCOPY copy registers KEPT per column (RTL (* keep *), ot_hbm_su_static_data_store.sv), and
#  - the generator's opt-in GPL guide per SRAM for its own copy registers (--macro-reg-guide g_wcopy, MRG_UM um).
# Same inputs as REBAL-9 mk_canon_m5w1.sh (plan c20e_k2m, views_k2m, slices_k2m, plan-fixed macros mp3_lanes__canon.json).
# GUIDE=off regenerates the default form (no guide) for the byte-identity check.
set -eu
W=${W:-/srv/opentallas-scratch2/claude/wt/hbm-cores-rebal-10}; R4=/srv/opentallas-scratch2/claude/hbm-cores-rebal-4
R=/srv/opentallas-scratch2/claude/hbm-cores-rebal-10; F=$R/fixes_m5w1; m=ot_hbm_su_static_pgslice_lg__lanes__canon_cf1e77
P=$R4/c20e_k2m; V=$R4/views_k2m.json; MLAT=${MLAT:-5}; WCOPY=${WCOPY:-1}; TAG=${TAG:-_c20ek2m_m5w1gk}
GUIDE=${GUIDE:-on}; MRG_UM=${MRG_UM:-15}
rm -rf $F; mkdir -p $R/kits $R/preflight; cp -r $R4/fixes $F
python3 - $F/canon_wrappers/$m.sv $MLAT $WCOPY <<PY
import sys, re
from pathlib import Path
p = Path(sys.argv[1]); t = p.read_text()
old = "    ot_hbm_su_pg_lanes4_core u_core ("
assert t.count(old) == 1, "canon wrapper core instance not found once"
t = t.replace(old, f"    ot_hbm_su_pg_lanes4_core #(.MLAT({sys.argv[2]}),.WCOPY({sys.argv[3]})) u_core (")
p.write_text("// HBM-CORES-REBAL-9: lane build MLAT %s WCOPY %s passed to the generated core (mk_canon_m5w1.sh)\n" % tuple(sys.argv[2:4]) + t)
PY
EXTRA=""; [ "$GUIDE" = on ] && EXTRA="--macro-reg-guide g_wcopy --macro-reg-guide-um $MRG_UM"; [ -n "${RELAY:-}" ] && EXTRA="$EXTRA --relay-reg-guide $RELAY"
cd $W/physical/die_plan/hbm_arch_cores
v=$(python3 -c "import json;print([v[\"view\"] for v in json.load(open(\"$V\"))[\"view_list\"] if v[\"module\"]==\"$m\"][0])")
rm -rf $R/kits/${m}_*-$TAG
python3 $F/run_canon_kit.py $W $F --views $V --view $v --out $R/kits --master-slice $R4/slices_k2m --trial --tag $TAG \
  --macro-placement $R4/mp3_lanes__canon.json --macro-inst-fmt "{k}" $EXTRA > $R/kits/gen_$m$TAG.log 2>&1; echo "$m rc=$?"
bash $W/results/die_hbm_kits_1027/pf_all.sh $P $R/kits $R/preflight $W
# reset contract (DIE-HBM-10 per-kit copy, same module): kit LEC window 64 edges
K=$(ls -d $R/kits/${m}_*-$TAG); K4=$(ls -d $R4/kits/${m}_*-_c20ek2m)
python3 -c "import json,sys;d=json.load(open(sys.argv[1]));assert d[\"modules\"]==[sys.argv[2]] and d[\"edges\"]==64" $K4/reset_contract.json $m
cp $K4/reset_contract.json $K/; cp -r $K4/reset_contract $K/
