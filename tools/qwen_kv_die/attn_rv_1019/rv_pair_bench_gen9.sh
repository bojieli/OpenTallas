#!/usr/bin/env bash
# KV-BIND4 10-19: rv_pair_bench.sh with A = the GEN9 die's OWN boot-age attention tile (module qkd_kvs_attn of
# rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_tiles_hroot_ff_k_mu_ba.sv in its face-land wrapper qkd_kvs_attn_fl_ba.sv),
# renamed to the bench's A names (qkd_kvs_attn_ba5 / qkd_kvs_attn_fl_ba5), instead of the codex ba5 lineage.  B = r16.
#   rv_pair_bench_gen9.sh RUN_DIR MUT [MODES] [NAME=VALUE ...]   -> KVS_RVPAIR_ALL PASS|FAIL
set -euo pipefail
RUN=${1:?run dir}; MUT=${2:-0}; MODES=${3:-"0 1 2 3 4 5 6 7 8 9 10"}; shift 3 || shift $#
for _d in "$HOME/.local/opentallas-tools/verilator-5.050/bin" /opt/verilator-5.050/bin; do [ -x "$_d/verilator" ] && PATH="$_d:$PATH"; done
ROOT=$(cd "$(dirname "$0")/../../.." && pwd)
S=$ROOT/rtl/qwen_sys/split_20261014; B=$ROOT/rtl/qwen_sys/kv_bootage_20261019; K=$ROOT/rtl/qwen_sys/static_kv_die_20261017
mkdir -p "$RUN/a_src"
python3 - "$K/qkd_kvs_tiles_hroot_ff_k_mu_ba.sv" "$ROOT/rtl/lib/face_land/qkd_kvs_attn_fl_ba.sv" "$RUN/a_src" <<'PY'
import re, sys
t = open(sys.argv[1]).read()
m = re.search(r'(?ms)^\s*module\s+qkd_kvs_attn\b.*?^\s*endmodule', t)
open(sys.argv[3] + '/a_tile.sv', 'w').write('`timescale 1ns/1ps\n' + re.sub(r'module\s+qkd_kvs_attn\b', 'module qkd_kvs_attn_ba5', m.group(0), 1) + '\n')
w = open(sys.argv[2]).read()
w = re.sub(r'module\s+qkd_kvs_attn_fl\b', 'module qkd_kvs_attn_fl_ba5', w, 1)
w = re.sub(r'\bqkd_kvs_attn\s+u_core\b', 'qkd_kvs_attn_ba5 u_core', w, 1)
open(sys.argv[3] + '/a_fl.sv', 'w').write(w)
PY
SRC="$S/qkd_native_attention_programme.sv $S/qkd_native_attention_static_ctl.sv $S/qkd_native59_descriptor_producer.sv $S/qkd_native_attention_record.sv $S/qkd_native59_command_guard.sv
 $B/qkd_attn_service_root_b.sv $B/qkd_attn_result_face_sb.sv $K/qkd_attn_fault_root.sv $B/qkd_attn_cal_gen_b.sv
 $RUN/a_src/a_tile.sv $RUN/a_src/a_fl.sv $ROOT/rtl/lib/ot_rst_relay.sv $ROOT/rtl/lib/ot_pin_land.sv
 $B/qkd_kvs_attn_r16.sv $ROOT/rtl/lib/face_land/qkd_kvs_attn_fl_r16.sv $ROOT/rtl/test/kv_bootage_1019/tb_kvs_attn_rv_pair.sv"
G=(-GMUT="$MUT"); for kv in "$@"; do G+=(-G"$kv"); done; G+=(+define+RV_RS)
TAG=$(printf '%s_' gen9 "m$MUT" "$@" | tr -c 'A-Za-z0-9_\n' '_'); OBJ="$RUN/obj_$TAG"
echo "KVS_RVPAIR build A=GEN9 B=r16 mut=$MUT $* verilator $(verilator --version)"
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
