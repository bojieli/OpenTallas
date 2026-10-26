#!/bin/bash
# MU.TOK.QW launcher (MU-ADOPT-TOK 2026-10-19).  Spec: results/rtl/mu_qwen_1018/tok/README.md.
#   launch_mu_tok.sh cases OUT                      emit the case tables (record, record_cp, rtl_layer, cmdplane4, ...)
#   launch_mu_tok.sh smoke SRC_ON_FLEET WORK        the command-plane smoke on the fleet (Verilator 5.050, ot-run)
#   launch_mu_tok.sh gate COMPUTE_DIE_V KV_DIE_V TOKQW_RECORD GOLD_DIR
#                                                   precondition gate of the REAL run (MU-QW-B1 10-19: B1 / B2 closed,
#                                                   the case table of record is `record_op`).  Refuses (exit 2) only on
#                                                   B3: the die netlists / GEN sources lack the MU RTL (compute:
#                                                       qfd_dv_cmd_cal_mu, qfd_dv_amax_mu, the OPSEG leaf
#                                                       qfd_sys_face_mu_dhuser; KV: qkd_kv_mu_wrow / _rrow);
#                                                   B4: TOKQW_RECORD (the single-user TOK.QW record) has no "TOK_QW PASS";
#                                                   B5: GOLD_DIR lacks per-user goldens (a file named *u1* / *u2* / *u3*).
#                                                   A record_op compile error is a calendar bug (exit 3), not a blocker.
#                                                   Prints the per-case real-run steps when open.
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
    C=${2:?COMPUTE_DIE_V}; K=${3:?KV_DIE_V}; R4=${4:-}; G5=${5:-}; rc=0
    # MU-DQ-TOK 10-19: a die GEN's die.v names only the tile masters (the MU blocks sit inside qfd_tt_ctlm_dv /
    # qfd_dv_slice2_e/w / qkd_* tiles), so the MU build is proven by the GEN record: compute die.v.params.json
    # (qfd_tt_ctlm_dv NU 4 + OPSEG 1, qfd_dv_slice2_e/_w MU_NU 4) and the KV run's kv_flags.env OT_KV_MU=1; a die.v that
    # names the MU blocks (flat netlist) passes as before.
    cmu=$(python3 - "$C.params.json" <<'PY' 2>/dev/null
import json, sys
m = json.load(open(sys.argv[1])).get("masters", {})
ok = m.get("qfd_tt_ctlm_dv", {}).get("NU", 1) >= 4 and m.get("qfd_tt_ctlm_dv", {}).get("OPSEG", 0) == 1 and \
     all(m.get(k, {}).get("MU_NU", 1) >= 4 for k in ("qfd_dv_slice2_e", "qfd_dv_slice2_w"))
print("MU" if ok else "NO")
PY
)
    if [ "$cmu" != MU ]; then
        for m in qfd_dv_cmd_cal_mu qfd_dv_amax_mu qfd_sys_face_mu_dhuser; do
            grep -q "$m" "$C" || { echo "BLOCKED B3: compute die $C has no $m and no MU params (NU 4 / OPSEG 1 / MU_NU 4) in $C.params.json"; rc=2; }
        done
    fi
    kf=$(dirname "$K")/../kv_flags.env
    if ! grep -q "OT_KV_MU='\?1" "$kf" 2>/dev/null; then
        for m in qkd_kv_mu_wrow qkd_kv_mu_rrow; do
            grep -q "$m" "$K" || { echo "BLOCKED B3: KV die $K has no $m and $kf lacks OT_KV_MU=1 (MU-ADOPT-KV)"; rc=2; }
        done
    fi
    { [ -n "$R4" ] && grep -q "TOK_QW PASS" "$R4"; } || { echo "BLOCKED B4: no single-user TOK.QW PASS record (${R4:-not given})"; rc=2; }
    for u in 1 2 3; do
        { [ -n "$G5" ] && ls "$G5" 2>/dev/null | grep -q "u$u"; } || { echo "BLOCKED B5: no user-$u golden in ${G5:-<GOLD_DIR not given>}"; rc=2; }
    done
    (cd "$ROOT/tools" && python3 - <<'PY') || { echo "CALENDAR ERROR: record_op does not compile (mu_opcal)"; exit 3; }
from qwen_static_schedule import mu_tok_cases as T
c = T.cases("record_op")
assert c["playability"]["rtl_playable"]
print("record_op:", round(c["aggregate_tok_s_modelled"], 1), "tok/s,", c["leaf"]["entries"], "leaf entries (B1 closed)")
PY
    if [ $rc = 0 ]; then
        cat <<'TXT'
GATE OPEN.  Real-run steps (README section 3), each on the fleet with Verilator 5.050, per-user cases from `cases --variant record_op`:
  T1 compute layer x4 users  (extends QW-CLAYER2 stage benches + QW-REALSTG real operands, colW5 slice of the MU GEN, OPSEG 1 leaf image)
  T2 KV attention x4 users   (extends QW-KVATTN/QW-KVATTN2 kvs_attn step on the MU KV GEN, rows 64+l+256u)
  T3 D2D pair x4 users       (extends Q-XDIE pair_r2 with the calendar's per-user record cycles)
  T4 TP8 collective          (MU-QWEN mu_bi, rerun only if the GEN's collective calendar LS changed)
  T5 LM head chunks          (MU-QWEN-HEAD tb_amax_mu on the slice of the MU GEN; 8 chunks per filler)
  T6 host 4 outstanding      (MU-QWEN-HOST tb_qkd_host_mu_out on the KV GEN host)
  T7 composition             (measured spans placed on the record_op frame -> per-user + aggregate tok/s, real cycles)
TXT
    fi
    exit $rc ;;
*)
    sed -n 2,9p "$0"; exit 1 ;;
esac
