#!/bin/bash
# KV-CORES/ASTK 10-25: cts (resume from 3_place, in-flow HOLD_SLACK_MARGIN 5) -> CTS hold STOP gate -> route ->
#   warm m8 post-route ECO -> signoff.   astk_chain.sh KIT   (run detached on epyc1; heavy steps through ot-run)
# STOP rule (brief c): after CTS, hold WNS < -100 ps or > 2000 hold-violating endpoints = stop (no route).
set -uo pipefail
K=$1; WT=/srv/opentallas-scratch2/claude/wt/kv-cores-astk; H=$WT/physical/die_plan/qwen_kvsys/cores/harden
OTR=~/.local/bin/ot-run
echo "$(date) cts $K"
$OTR --mem 32 --threads 16 --stage $K --dir $K -- bash $K/run_kit_kv.sh $K cts 32 16
echo "$(date) cts rc=$?"
python3 - "$K" <<'PY' || { echo "$(date) CTS HOLD STOP"; exit 2; }
import json,glob,sys
fs=sorted(glob.glob(sys.argv[1]+"/run/logs/asap7/*/base/4_1_cts.json"))
if not fs: print("no 4_1_cts.json"); sys.exit(1)
d=json.load(open(fs[0])); h={k:v for k,v in d.items() if "hold" in k}
print("CTS hold metrics:",h)
ws=[v for k,v in h.items() if k.endswith("hold__ws")]; n=[v for k,v in h.items() if "hold_violation_count" in k]
ws=min(ws) if ws else 0.0; n=max(n) if n else 0
wsp=ws   # ORFS ASAP7 metrics are in ps
print(f"CTS hold WNS {wsp:.1f} ps, endpoints {n}")
sys.exit(1 if (wsp < -100 or n > 2000) else 0)
PY
$OTR --mem 32 --threads 16 --stage $K --dir $K -- bash $K/run_kit_kv.sh $K route 32 16
echo "$(date) route rc=$?"
test -f $(ls -d $K/run/results/asap7/*/base)/5_2_route.odb || { echo "no routed odb"; exit 1; }
E=${K}.m8
bash $H/eco/mk_eco.sh $K $E m8 $WT || exit 1; cp $H/eco/run_eco.sh $E/
echo "$(date) eco m8 $E"
$OTR --mem 32 --threads 8 --stage $E --dir $E -- bash $E/run_eco.sh $E 8 32
echo "$(date) eco rc=$?"
