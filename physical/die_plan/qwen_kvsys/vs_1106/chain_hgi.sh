#!/bin/bash
# KV-SLGLAND-1/vS hgi_v8 chain: event -> install -> checks -> elab -> strict bind -> kits. Stops at the first failure; marker file = state.
set -uo pipefail
V=/srv/opentallas-scratch3/claude/kv-slgland-1-vs/hgi; S=/srv/opentallas-scratch2/claude/kv-slgland-1-vs/wt
D=physical/die_plan/qwen_kvsys/plan_of_record; P=$D/plan_c.json; AB=$V/asbuilt.json; ST=$V/STATE
st(){ echo "$(date) $*" >> $ST; }
cd $S || exit 2
st START
git sparse-checkout add physical/asap7_memory_macros >> $V/chain.log 2>&1
if [ "${SKIP_EVENT:-0}" = 1 ]; then st EVENT_REUSED; else
git checkout HEAD -- $P $D/eW_sidecar.json
timeout 1800 nice python3 -I physical/die_plan/qwen_kvsys/vs_1106/vs_split.py physical/die_plan/qwen_kvsys/vs_1106/hgi_cfg.json $P $D/eW_sidecar.json $V >> $V/chain.log 2>&1 || { st EVENT_FAIL; exit 3; }
fi
st EVENT_OK
cp $V/plan_c.json $P; cp $V/eW_sidecar.json $D/eW_sidecar.json
nice python3 -I - >> $V/check.log 2>&1 <<PY
import sys,json
sys.path.insert(0,"tools/die_plan")
import schema as S, landing_contract as LC
raw=json.load(open("$P")); side=json.load(open("$D/eW_sidecar.json"))
try: S.validate(raw); print("VALIDATE OK")
except Exception as e: print("VALIDATE FAIL",e)
try: print("LANDING",LC.check(S.Plan(raw,"$P"),side))
except Exception as e: print("LANDING FAIL",e)
PY
st "CHECKS_DONE (advisory, see check.log)"
mkdir -p $V/bind
nice python3 -I tools/die_plan/bind.py elab $P --out $V/bind --asbuilt $AB --mem 32 >> $V/bind.log 2>&1 || { st ELAB_FAIL; exit 4; }
st ELAB_OK
nice python3 -I tools/die_plan/bind.py bind $P --out $V/bind --asbuilt $AB --strict >> $V/bind.log 2>&1 || { st BIND_FAIL; exit 5; }
st BIND_OK
for T in kv3_hgi_v8 kv3_hgi_v8_a; do
  W=$V/kits/${T}_vS; rm -rf $W/gen $W/rtl; mkdir -p $W/logs
  python3 tools/die_plan/bind.py kit-rtl $P --out $V/bind --asbuilt $AB --type $T --kit $W/rtl > $W/logs/kit_rtl.log 2>&1 || { st KITRTL_FAIL $T; exit 6; }
  python3 -I tools/die_plan/kit_topology.py prepare-stations $P $T $W/rtl --native-plan $P --asbuilt $AB > $W/logs/kit_topology.log 2>&1 || { st TOPO_FAIL $T; exit 7; }
  python3 tools/die_plan/gen.py phys $P --out $W/gen --types $T --rtl-root $S --kit-rtl $T=$W/rtl/kit_rtl.f --cland-pinslot all --hold-ff-margin 0 --clock-landing $S/$D/eW_sidecar.json --native-cell-cap 517000 > $W/logs/gen.log 2>&1 || { st GEN_FAIL $T; exit 8; }
  python3 tools/die_plan/kit_preflight.py $W/gen/$T --plan-dir $S/$D > $W/logs/preflight.log 2>&1 || { st PREFLIGHT_FAIL $T; exit 9; }
  st KIT_OK $T
done
st KITS_READY
