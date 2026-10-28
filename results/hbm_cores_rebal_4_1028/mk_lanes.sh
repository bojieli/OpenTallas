#!/bin/bash
# HBM-CORES-REBAL-4: lanes__canon kit = plan c20e_k2m (c20e_k2s + lanes_oneclk.py) + plan-fixed macros mp3_lanes__canon.json
set -eu
W=/srv/opentallas-scratch2/claude/wt/hbm-cores-rebal-4; R=/srv/opentallas-scratch2/claude/hbm-cores-rebal-4
P=$R/c20e_k2m; V=$R/views_k2m.json; F=$R/fixes; m=ot_hbm_su_static_pgslice_lg__lanes__canon_cf1e77
cd $W/physical/die_plan/hbm_arch_cores
python3 views_b2r2.py --plan $P/die_plan.json --out $V > $R/views_k2m.log 2>&1
python3 $W/results/die_hbm_kits_1027/mk_c20.py $P $V $R/slices_k2m $R/kits $W $m --islands-only --ft-pin-dx-um 1.08 > $R/mk_slices_k2m.log 2>&1
v=$(python3 -c "import json;print([v[\"view\"] for v in json.load(open(\"$V\"))[\"view_list\"] if v[\"module\"]==\"$m\"][0])")
rm -rf $R/kits/${m}_*-_c20ek2m $R/preflight/${m}_*
python3 $F/run_canon_kit.py $W $F --views $V --view $v --out $R/kits --master-slice $R/slices_k2m --trial --tag _c20ek2m \
  --macro-placement $R/mp3_lanes__canon.json --macro-inst-fmt "{k}" > $R/kits/gen_$m.log 2>&1; echo "$m rc=$?"
bash $W/results/die_hbm_kits_1027/pf_all.sh $P $R/kits $R/preflight $W
