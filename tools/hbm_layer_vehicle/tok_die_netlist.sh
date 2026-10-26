#!/usr/bin/env bash
# HBMc/TOKEN2 (10-22): HBM token bench on a GEN die netlist of a die chain (tok_func_hbm.sh --die-netlist, MODE=gen_rtl).
#   tok_die_netlist.sh <chain-artifacts-dir A (…/plansM)> <remote chain root B on HOST> <chain worktree W> [CASE=case]
#   CASE=case   : S10 final GEN (post-S8b contract = $A/net/contract.json, l12 report $A/net/l12_banklat.json)  [default]
#   CASE=case_b : S7 GEN (pre-forest; contract = the case manifest's contract)   CASE=case_a : S3 (dry-run only)
#   env: OUT RUN(=0) MEM(=400) RUN_MEM(=64) STAGE_HOSTS HOST(=ot-epyc5) CONTRACT (override) L12_JSON (override)
# Steps: fetch GEN die.v -> gen_die_func.py (functional form from GEN connectivity + CONN_EQUIV vs contract; FAIL is
# reported, not hidden) -> tok_func_hbm.sh --die-netlist with the conn_p40 recipe (FIX_DS rsrc, QOP qop, CONNECTED_LOWERING=1).
set -u -o pipefail
T=$(cd "$(dirname "$0")" && pwd)
A=${1:?A}; B=${2:?B}; W=${3:?W}; CASE=${4:-case}; HOST=${HOST:-ot-epyc5}
SRC_REV=$(git -C "$W" rev-parse HEAD) || exit 2
OUT=${OUT:-/home/ubuntu/scratch/hbmc-token2/dn_$(basename "$(dirname "$A")")_$CASE}; mkdir -p "$OUT/gen"
say() { echo "$(date -Is) $*" | tee -a "$OUT/gen/summary.log"; }
timeout 900 scp -q "$HOST:$B/$CASE/die.v" "$OUT/gen/die.v" || { say "NO_GEN_DIE $HOST:$B/$CASE/die.v"; exit 4; }
timeout 300 scp -q "$HOST:$B/$CASE/manifest.json" "$OUT/gen/manifest.json" || true
if [ -z "${CONTRACT:-}" ]; then
  if [ "$CASE" = case ]; then CONTRACT=$A/net/contract.json
  else CONTRACT=$OUT/gen/contract.json
    cp=$(python3 -c "import json;print(json.load(open('$OUT/gen/manifest.json'))['contract'])")
    timeout 900 scp -q "$HOST:$cp" "$CONTRACT" || { say "NO_CASE_CONTRACT $cp"; exit 4; }
  fi
fi
L12=${L12_JSON:-$A/net/l12_banklat.json}
git -C "$W" show "$SRC_REV:tools/hbm_die_v16/contract_die_v.py" > "$OUT/gen/contract_die_v.py" || exit 2
say "GEN die=$HOST:$B/$CASE/die.v ($(sha256sum "$OUT/gen/die.v" | cut -c1-16)) contract=$CONTRACT ($(sha256sum "$CONTRACT" | cut -c1-16)) src=$SRC_REV"
python3 "$T/gen_die_func.py" --die "$OUT/gen/die.v" --contract "$CONTRACT" --out "$OUT/gen/die_func.v" \
  --report "$OUT/gen/gen_die_func.json" --cdv "$OUT/gen/contract_die_v.py" ${PATCH_OPEN:+--patch-open} | tee -a "$OUT/gen/summary.log" || { say GEN_DIE_FUNC_FAIL; exit 3; }
mkdir -p "$OUT"; [ -f "$L12" ] && cp "$L12" "$OUT/l12.json" || say "NO_L12_REPORT $L12 (CX emission needs it)"
OUT=$OUT SRC_REV=$SRC_REV CONTRACT=$CONTRACT FIX_DS=${FIX_DS:-/home/ubuntu/scratch/tok-func-hbm/rsrc} QOP=${QOP:-/home/ubuntu/scratch/tok-func-hbm/qop} \
  CONNECTED_LOWERING=1 MEM=${MEM:-400} JOBS=${JOBS:-16} RUN=${RUN:-0} RUN_MEM=${RUN_MEM:-64} TAG=${TAG:-$(basename "$OUT")} \
  REMOTE=${REMOTE:-/srv/opentallas-scratch/claude/hbmc-token2/$(basename "$OUT")} STAGE_HOSTS="${STAGE_HOSTS:-ot-epyc5 ot-gold1}" \
  bash "$T/tok_func_hbm.sh" --die-netlist "$OUT/gen/die_func.v"
