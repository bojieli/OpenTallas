#!/usr/bin/env bash
# KV-ATTN2 2026-10-19: whole-tile pair lockstep tb_kvs_attn_rv_pair (A = qkd_kvs_attn_fl_ba5, B = qkd_kvs_attn_fl rv, B = A + 1 edge).
#   rv_pair_bench.sh RUN_DIR MUT [MODES] [NAME=VALUE ...]     (MODES default "0 1 2 3 4 5 6 7 8 9 10")
# B variant: RVB=rv (default, qkd_kvs_attn_rv.sv / qkd_kvs_attn_fl_rv.sv) | r16 (qkd_kvs_attn_r16.sv / qkd_kvs_attn_fl_r16.sv).
# Verilator 5.050 (the closure daemon's pinned version).  One line per mode, then
#   KVS_RVPAIR_ALL PASS|FAIL mut=M modes=N checks=C fails=F
# exit 0 only on ALL PASS.
set -euo pipefail
RUN=${1:?run dir}; MUT=${2:-0}; MODES=${3:-"0 1 2 3 4 5 6 7 8 9 10"}; shift 3 || shift $#
for _d in "$HOME/.local/opentallas-tools/verilator-5.050/bin" /opt/verilator-5.050/bin; do [ -x "$_d/verilator" ] && PATH="$_d:$PATH"; done
ROOT=$(cd "$(dirname "$0")/../../.." && pwd)
S=$ROOT/rtl/qwen_sys/split_20261014; B=$ROOT/rtl/qwen_sys/kv_bootage_20261019; K=$ROOT/rtl/qwen_sys/static_kv_die_20261017
SRC="$S/qkd_native_attention_programme.sv $S/qkd_native_attention_static_ctl.sv $S/qkd_native59_descriptor_producer.sv $S/qkd_native_attention_record.sv $S/qkd_native59_command_guard.sv
 $B/qkd_attn_service_root_b.sv $B/qkd_attn_result_face_sc.sv $K/qkd_attn_fault_root.sv $B/qkd_attn_cal_gen_b.sv
 $B/qkd_native_attention_static_ctl_ba4.sv $B/qkd_native_attention_programme_ba4.sv $B/qkd_kvs_attn_ba5.sv
 $ROOT/rtl/lib/face_land/qkd_kvs_attn_fl_ba5.sv $ROOT/rtl/lib/ot_rst_relay.sv $ROOT/rtl/lib/ot_pin_land.sv
 $B/qkd_kvs_attn_${RVB:-rv}.sv $ROOT/rtl/lib/face_land/qkd_kvs_attn_fl_${RVB:-rv}.sv $ROOT/rtl/test/kv_bootage_1019/tb_kvs_attn_rv_pair.sv"
G=(-GMUT="$MUT"); for kv in "$@"; do G+=(-G"$kv"); done
TAG=$(printf '%s_' "${RVB:-rv}" "m$MUT" "$@" | tr -c 'A-Za-z0-9_\n' '_')
mkdir -p "$RUN"; OBJ="$RUN/obj_$TAG"
echo "KVS_RVPAIR build B=${RVB:-rv} mut=$MUT $* verilator $(verilator --version)"
verilator --binary -j 8 --build-jobs 8 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTH -Wno-SELRANGE -Wno-MULTIDRIVEN \
  --top-module tb_kvs_attn_rv_pair "${G[@]}" -Mdir "$OBJ" $SRC > "$RUN/build_$TAG.log" 2>&1 \
  || { tail -40 "$RUN/build_$TAG.log"; echo "KVS_RVPAIR_ALL FAIL build mut=$MUT"; exit 1; }
n=0; fails=0; tot=0
for m in $MODES; do
  "$OBJ/Vtb_kvs_attn_rv_pair" +MODE=$m > "$RUN/sim_${TAG}mode$m.log" 2>&1 || true
  grep -E '^(KVS_RVPAIR|MISMATCH)' "$RUN/sim_${TAG}mode$m.log" | head -12
  n=$((n+1))
  if grep -q '^KVS_RVPAIR PASS' "$RUN/sim_${TAG}mode$m.log"; then
    c=$(grep -o 'checks=[0-9]*' "$RUN/sim_${TAG}mode$m.log" | head -1 | cut -d= -f2); tot=$((tot+c))
  else fails=$((fails+1)); fi
done
if [ "$fails" = 0 ]; then echo "KVS_RVPAIR_ALL PASS mut=$MUT modes=$n checks=$tot fails=0"; exit 0; fi
echo "KVS_RVPAIR_ALL FAIL mut=$MUT modes=$n checks=$tot fails=$fails"; exit 1
