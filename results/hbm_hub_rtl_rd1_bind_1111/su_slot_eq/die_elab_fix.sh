#!/bin/bash
# fresh control elaboration with the fixed scorer source (private base_fix), no prune: count latches, then scorer EQ
set -o pipefail
P=/srv/opentallas-scratch2/claude/hbm-hub-rtl-1/rd1plan; SRC=$P/src; O=$P/eq/elab_fix; mkdir -p $O; touch $O/DO_NOT_COUNT
python3 -I - <<PY
import json
a=json.load(open("$P/ctl/asbuilt_ctl_t19.json")); a["base"]="$P/base_fix"
a["note"]+=" | EQ: base_fix = tip2 + non-latching scorer loop (HBM-HUB-RTL-1 11-12)"
json.dump(a,open("$P/eq/asbuilt_ctl_fix.json","w"),indent=1)
PY
cd $SRC && python3 tools/die_plan/bind.py elab $P/t19/die_plan.json --out $O --asbuilt $P/eq/asbuilt_ctl_fix.json --mem 48 > $P/eq/elab_fix.log 2>&1; echo "ELAB rc $?"
python3 -I - <<PY
import json,collections
M=json.load(open("$O/asbuilt.json"))["modules"]
print("DIE latches", sum(1 for m in M.values() for c in m.get("cells",{}).values() if "latch" in c["type"]), "mem cells", sum(1 for m in M.values() for c in m.get("cells",{}).values() if c["type"].startswith("$mem")))
PY
python3 -I $P/eq/scorer_eq.py /srv/opentallas-scratch2/claude/die-hbm-92-su/exp/bind_e0/asbuilt.json $O/asbuilt.json $P/eq/scorer_pair.json
for M in ot_hbm_su_static_pgslice_s; do python3 -I $P/eq/mod_eq.py /srv/opentallas-scratch2/claude/die-hbm-92-su/exp/bind_e0/asbuilt.json $O/asbuilt.json $P/eq/su_pair.json $M; sed s/scorer_pair/su_pair/ $P/eq/scorer_eq.ys > $P/eq/su_eq.ys; docker run --rm --memory=32g -u $(id -u):$(id -g) -v $P/eq:/w openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/yosys/bin/yosys -q -l /w/su_eq.log /w/su_eq.ys > /dev/null 2>&1; echo "SU_EQ rc $?"; grep -h "are proven|ERROR" $P/eq/su_eq.log | tail -2; done
docker run --rm --memory=16g -u $(id -u):$(id -g) -v $P/eq:/w openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/yosys/bin/yosys -q -l /w/scorer_eq.log /w/scorer_eq.ys > /dev/null 2>&1; echo "SCORER_EQ rc $?"; grep -h 'Found\|equivalent\|unproven\|ERROR' $P/eq/scorer_eq.log | tail -4
