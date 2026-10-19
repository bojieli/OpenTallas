#!/usr/bin/env bash
# KV-BOOTAGE 2026-10-19: lockstep benches of the boot-programmable static-schedule age successors against the closed
# modules (rtl/test/kv_bootage_1019/tb_kvba_*.sv).  Verilator 5.050 (the closure daemon's pinned version) when present.
#   kv_bootage_bench.sh RUN_DIR BENCH MUT [NAME=VALUE ...]
#   BENCH = vport (D R)   | pvctl (A)   | attn (PL FD FMUT)   | calgen (Q R F)   | dcfg
# Verdict line: KVBA_<BENCH> PASS|FAIL ...; exit 0 only on PASS.
set -euo pipefail
RUN=${1:?run dir}; BENCH=${2:?bench}; MUT=${3:-0}; shift 3 || true
for _d in "$HOME/.local/opentallas-tools/verilator-5.050/bin"; do [ -x "$_d/verilator" ] && PATH="$_d:$PATH"; done
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
B=$ROOT/rtl/qwen_sys/kv_bootage_20261019
case "$BENCH" in
  vport)  SRC="$ROOT/rtl/qwen_sys/static_kv_20261014/qkd_pv16_vport.sv $B/qkd_pv16_vport_b.sv"; TOP=tb_kvba_vport ;;
  pvctl)  SRC="$ROOT/rtl/hdc/nearhbm/ot_qwen_tp8_pv_wide_pair.sv $ROOT/rtl/hdc/nearhbm/ot_qwen_tp8_pv_wide_ctl_t.sv $ROOT/rtl/hdc/nearhbm/ot_qwen_tp8_pv_wide_ctl_tb.sv"; TOP=tb_kvba_pvctl ;;
  attn)   SRC="$ROOT/rtl/qwen_sys/split_20261014/qkd_attn_service_root.sv $ROOT/rtl/qwen_sys/split_20261014/qkd_attn_result_face_s.sv $B/qkd_attn_service_root_b.sv $B/qkd_attn_result_face_sb.sv"; TOP=tb_kvba_attn ;;
  calgen) SRC="$ROOT/rtl/qwen_sys/split_20261014/qkd_attn_cal_gen.sv $B/qkd_attn_cal_gen_b.sv"; TOP=tb_kvba_calgen ;;
  dcfg)   SRC="$ROOT/rtl/qwen_sys/static_kv_20261014/qkd_kv_die_cfg.sv $B/qkd_kv_die_cfg_a.sv"; TOP=tb_kvba_dcfg ;;
  *) echo "kv_bootage_bench: unknown bench $BENCH" >&2; exit 2 ;;
esac
G=(-GMUT="$MUT")
for kv in "$@"; do G+=(-G"$kv"); done
mkdir -p "$RUN"
TAG=$(printf '%s_' "$BENCH" "$MUT" "$@" | tr -c 'A-Za-z0-9_\n' '_')
OBJ="$RUN/obj_$TAG"
echo "KVBA build $BENCH mut=$MUT $* verilator $(verilator --version | awk '{print $2}')"
verilator --binary -j 4 --build-jobs 1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTH -Wno-SELRANGE \
  --top-module "$TOP" "${G[@]}" -Mdir "$OBJ" $SRC "$ROOT/rtl/test/kv_bootage_1019/$TOP.sv" > "$RUN/build_$TAG.log" 2>&1 \
  || { tail -30 "$RUN/build_$TAG.log"; echo "KVBA_${BENCH^^} FAIL build mut=$MUT $*"; exit 1; }
"$OBJ/V$TOP" | tee "$RUN/sim_$TAG.log"
grep -q "^KVBA_${BENCH^^} PASS" "$RUN/sim_$TAG.log"
