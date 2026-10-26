#!/bin/bash
# KV-CORES/ASTK 10-25 (rev. after COORD root-merge reject: no post-route ECO stage, owner rule 10-25 / KV ruling 5):
#   cts (resume from 3_place, in-flow HOLD_SLACK_MARGIN 5) -> CTS hold STOP gate -> route -> signoff (in run_kit_kv.sh).
#   astk_chain.sh KIT   (heavy steps through ot-run).  NOT SIGNED at route = review + structural fix, never an ECO.
# STOP rule: after CTS, hold WNS < -100 ps or > 2000 hold-violating endpoints = stop (no route).
set -uo pipefail
if [ "$#" -ne 1 ]; then echo "usage: $0 KIT" >&2; exit 2; fi
K=$1; OTR=${OT_RUN:-$HOME/.local/bin/ot-run}
echo "$(date) cts $K"
$OTR --mem 32 --threads 16 --stage $K --dir $K -- bash $K/run_kit_kv.sh $K cts 32 16
rc=$?
echo "$(date) cts rc=$rc"
if [ "$rc" -ne 0 ]; then exit "$rc"; fi
python3 - "$K" <<"PY" || { echo "$(date) CTS HOLD STOP"; exit 2; }
import json,glob,sys,math
fs=sorted(glob.glob(sys.argv[1]+"/run/logs/asap7/*/base/4_1_cts.json"))
if not fs: print("no 4_1_cts.json"); sys.exit(1)
d=json.load(open(fs[0])); h={k:v for k,v in d.items() if "hold" in k}
ws=[v for k,v in h.items() if k.endswith("hold__ws")]; n=[v for k,v in h.items() if "hold_violation_count" in k]
if not ws or not n:
 print("missing CTS hold WNS or endpoint-count metric"); sys.exit(1)
if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in ws+n):
 print("invalid CTS hold metric"); sys.exit(1)
ws=min(ws); n=max(n)
if n < 0:
 print("negative CTS endpoint count"); sys.exit(1)
print(f"CTS hold WNS {ws:.1f} ps, endpoints {n}")
sys.exit(1 if (ws < -100 or n > 2000) else 0)
PY
$OTR --mem 32 --threads 16 --stage $K --dir $K -- bash $K/run_kit_kv.sh $K route 32 16
rc=$?
echo "$(date) route rc=$rc verdict=$(python3 -c "import json; print(json.load(open(\"$K/signoff/signoff.json\")).get(\"verdict\"))" 2>/dev/null)"

if [ "$rc" -ne 0 ]; then exit "$rc"; fi
python3 - "$K/signoff/signoff.json" <<"PY"
import json,sys
try:
 d=json.load(open(sys.argv[1]))
except (OSError, ValueError) as e:
 print(f"signoff NOT RUN: {e}"); sys.exit(3)
v=d.get("verdict")
print(f"final signoff {v}")
sys.exit(0 if v == "SIGNED" else 3)
PY
