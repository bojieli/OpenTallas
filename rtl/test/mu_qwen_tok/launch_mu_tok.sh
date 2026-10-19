#!/bin/bash
# MU.TOK.QW launcher (MU-ADOPT-TOK 2026-10-19).  Spec: results/rtl/mu_qwen_1018/tok/README.md.
#   launch_mu_tok.sh cases OUT                      emit the case tables (record, record_cp, rtl_layer, cmdplane4, ...)
#   launch_mu_tok.sh smoke SRC_ON_FLEET WORK        the command-plane smoke on the fleet (Verilator 5.050, ot-run)
#   launch_mu_tok.sh gate COMPUTE_DIE_V KV_DIE_V    precondition gate of the REAL run: refuses (exit 2) unless the die
#                                                   netlists/GEN sources carry the MU RTL (B3) and the case table of
#                                                   record is RTL-playable (B1); prints the per-case real-run steps
set -u
D=$(cd "$(dirname "$0")" && pwd); ROOT=$(cd "$D/../../.." && pwd)
case "${1:-}" in
cases)
    OUT=${2:?OUT}; cd "$ROOT/tools" && python3 -m qwen_static_schedule.mu_tok_cases --out "$OUT" &&
        python3 -m qwen_static_schedule.mu_tok_cases --brief --out "$OUT" ;;
smoke)
    SRC=${2:?SRC_ON_FLEET}; W=${3:?WORK}
    exec /home/ubuntu/bin/ot-run --mem 8 --threads 8 --dir "$SRC" --disk 5 -- bash rtl/test/mu_qwen_tok/run_mu_tok_smoke.sh "$W" ;;
gate)
    C=${2:?COMPUTE_DIE_V}; K=${3:?KV_DIE_V}; rc=0
    for m in qfd_dv_cmd_cal_mu qfd_dv_amax_mu; do
        grep -q "$m" "$C" || { echo "BLOCKED B3: compute die $C has no $m (MU-ADOPT-CTLM / MU-ADOPT-SLICE)"; rc=2; }
    done
    for m in qkd_kv_mu_wrow qkd_kv_mu_rrow; do
        grep -q "$m" "$K" || { echo "BLOCKED B3: KV die $K has no $m (MU-ADOPT-KV)"; rc=2; }
    done
    cd "$ROOT/tools" && python3 - <<'PY' || rc=2
import sys
from qwen_static_schedule import mu_tok_cases as T
p = T.cases("record", tokens=2)["playability"]
if not p["rtl_playable"]:
    print("BLOCKED B1: calendar of record not playable by qfd_dv_cmd_cal_mu:", p["reason"],
          {u: v["intra_layer_op_gaps"] for u, v in p["per_user"].items()})
    sys.exit(2)
PY
    if [ $rc = 0 ]; then
        cat <<'TXT'
GATE OPEN.  Real-run steps (README section 3), each on the fleet with Verilator 5.050, per-user cases from `cases`:
  T1 compute layer x4 users  (extends QW-CLAYER2 stage benches + QW-REALSTG real operands, colW5 slice of the MU GEN)
  T2 KV attention x4 users   (extends QW-KVATTN/QW-KVATTN2 kvs_attn step on the MU KV GEN, rows 64+l+256u)
  T3 D2D pair x4 users       (extends Q-XDIE pair_r2 with the calendar's per-user record cycles)
  T4 TP8 collective          (MU-QWEN mu_bi, rerun only if the GEN's collective calendar LS changed)
  T5 LM head chunks          (MU-QWEN-HEAD tb_amax_mu on the slice of the MU GEN; 8 chunks per filler)
  T6 host 4 outstanding      (MU-QWEN-HOST tb_qkd_host_mu_out on the KV GEN host)
  T7 composition             (measured spans placed on the calendar -> per-user + aggregate tok/s, real cycles)
TXT
    fi
    exit $rc ;;
*)
    sed -n 2,9p "$0"; exit 1 ;;
esac
