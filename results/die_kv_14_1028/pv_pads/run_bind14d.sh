#!/bin/bash
# DIE-KV-14d: strict KV bind with the PV column equalisation pads (recipe_kv14_s6) + the KV regen_constants check.
# usage: run_bind14d.sh OUT [RECIPE]     (run via: ssh intel2 ~/.local/bin/ot-run --mem 48 --hosts intel1 --dir <wt> -- bash ...)
# image (optional): IMG_WT=<worktree of claude/kv-image-13-1028@5bf44b6224> QC_BIND=<qc bind> -> run_constants2 + emit_assets
# Untracked inputs (gunzip once): results/die_kv_13_1028/event/ from event_gz/, and
#   physical/die_plan/qwen_kvsys/bind/kvbind1025/composition_heads_astk_1clk_oddstrap.json from its .json.gz, and
#   results/die_kv_7_1028/input/ (hard-core pin tables; untracked, copy from intel1 wt/die-kv-6 until committed)
set -u
W=$(git -C "$(dirname "$0")" rev-parse --show-toplevel); cd "$W"
P=${P:-results/die_kv_13_1028/event/plan.json}; RC=${2:-physical/die_plan/qwen_kvsys/dcal_rom/bind/position2144b19/recipe_kv14_s6.json}; O=$1
for f in $P physical/die_plan/qwen_kvsys/bind/kvbind1025/composition_heads_astk_1clk_oddstrap.json results/die_kv_7_1028/input/core_latency.json; do
  [ -s "$f" ] || { echo "MISSING untracked input $f (gunzip the tracked .gz)"; exit 2; }; done
mkdir -p $O
if [ ! -s $O/asbuilt.json ]; then echo "$(date) elab"; python3 tools/die_plan/bind.py elab $P --asbuilt $RC --out $O --mem 48 > $O/elab.log 2>&1 || { echo ELAB_RC=$?; tail -5 $O/elab.log; exit 4; }; fi
echo "$(date) bind"; python3 tools/die_plan/bind.py bind $P --asbuilt $RC --out $O --mem 48 --strict > $O/bind.log 2>&1; echo BIND_RC=$?
head -c 3000 $O/bind.log; echo
grep -q '"errors": 0' $O/bind.log || { echo BIND_ERRORS; exit 3; }
python3 - "$O" <<'PY'
import json, sys
p = json.load(open(sys.argv[1] + "/param_regen.json"))
print("PV_TRUNK", json.dumps(p["record"].get("pv_trunk")), [c for c in p["changed"] if c["param"] in ("TRUNK_D", "FLAG_D")])
PY
# the hook (kv_pv_col_regen.py) already failed closed unless every PV column owes 0 pads on this bind
python3 tools/die_plan/regen_constants.py --die qwen_kvsys --bound $O ${QC_BIND:+--peer $QC_BIND} --src-root "$W" --out-json $O/kv_constants.json > $O/kv_constants.log 2>&1; echo KV_CONSTANTS_RC=$?
grep -E "^\[(MISMATCH|ERROR|WARN)|TRUNK_D|FLAG_D|REGEN_CONSTANTS" $O/kv_constants.log
if [ -n "${IMG_WT:-}" ]; then
  export KV_BIND=$O OUT=$O/img KV_SRC_LABEL="claude/die-kv-14d-1028 recipe_kv14_s6" QC_SRC_LABEL="${QC_SRC_LABEL:-codex/qc-bind-1027 fresh_v3}"
  : "${QC_BIND:?set QC_BIND for the pair image}"
  bash $IMG_WT/results/kv_native_image_13/run_constants2.sh
  python3 $IMG_WT/results/kv_native_image_13/emit_assets.py; echo EMIT_RC=$?
  grep -E "^\[(MISMATCH|ERROR)|REGEN_CONSTANTS" $O/img/kv_constants2.log $O/img/qc_constants2.log
fi
echo "$(date) DONE"
