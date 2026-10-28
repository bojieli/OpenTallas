#!/bin/bash
# MESO-START-2: QC K2 count-aligned re-plan + die STA (spice) with the feed-edge start tree. usage: run_qc.sh TAG [plan flags]
set -u
R=/srv/opentallas-scratch2/claude/meso-start-2/qc_k2; Q=/srv/opentallas-scratch2/claude/die-qc4-1028; C=$Q/K2/CA_2w2s
PLAN=/srv/opentallas-scratch2/claude/wt/die-qc4-1028/physical/die_plan/qwen_compute/die_plan_sliceclk.json
TAG=$1; shift; O=$R/$TAG; mkdir -p $O; MT=/srv/opentallas-scratch2/claude/wt/meso-start-2/tools/die_plan
X=$C/grp_spice_xing_lpo.json
python3 $MT/count_align_plan.py $X "$@" --out $O/plan.json > $O/plan.log 2>&1; echo "plan rc $?" >> $O/chain.log
python3 -I - $X $O/plan.json $O/xing_INFO.json <<'PY' >> $O/chain.log
import json, sys
d = json.load(open(sys.argv[1])); p = json.load(open(sys.argv[2]))
bad = {o["port"] for o in p["crossings"] if not o.get("rtl") and not o.get("start_only") and o.get("kind") != "hop_relayed"}
for k in d["corners"]:
    d["corners"][k]["all"] = [r for r in d["corners"][k]["all"] if r["port"] not in bad]
json.dump(d, open(sys.argv[3], "w")); print("INFO drop", len(bad), sorted(bad)[:8])
PY
python3 $MT/count_align_bind.py $X --from-ocv --parts ocv --samples 2000 "$@" --out $O/bind.json > $O/bind.log 2>&1; rc=$?
echo "bind rc $rc" >> $O/chain.log
if [ ! -s $O/bind.json ]; then
  python3 $MT/count_align_bind.py $O/xing_INFO.json --from-ocv --parts ocv --samples 2000 "$@" --out $O/bind.json >> $O/bind.log 2>&1; echo "bind INFO rc $?" >> $O/chain.log
fi
python3 $MT/die_sta_related.py $C/proof --plan $PLAN --out $O/sta --corner TT --corner FF --clock-ocv table --clock-droop shared --droop-regions $C/proof/droop_regions.json --hold-buffers none --cppr-lca --clock-cal spice --count-align $O/bind.json --count-align-key region > $O/sta.log 2>&1; echo "sta rc $?" >> $O/chain.log
grep COUNT-ALIGN $O/sta.log >> $O/chain.log
