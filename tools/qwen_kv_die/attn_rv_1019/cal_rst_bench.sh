#!/usr/bin/env bash
# KV-ATTN4 2026-10-20: reset witness of the r17 calendar (S1..S9 sync reset) on Verilator 5.050, 3 random power-up seeds.
#   cal_rst_bench.sh RUN_DIR MUT     -> CALRST_ALL PASS|FAIL mut=M ; exit 0 only on ALL PASS
set -euo pipefail
RUN=${1:?run dir}; MUT=${2:-0}
for _d in "$HOME/.local/opentallas-tools/verilator-5.050/bin" /opt/verilator-5.050/bin; do [ -x "$_d/verilator" ] && PATH="$_d:$PATH"; done
ROOT=$(cd "$(dirname "$0")/../../.." && pwd)
SRC="$ROOT/rtl/qwen_sys/split_20261014/qkd_native_attention_record.sv $ROOT/rtl/qwen_sys/split_20261014/qkd_native59_command_guard.sv $ROOT/rtl/qwen_sys/kv_bootage_20261019/qkd_kvs_attn_r17.sv $ROOT/rtl/test/kv_bootage_1019/tb_qkd_attn_cal_gen_r17_rst.sv"
mkdir -p "$RUN"; OBJ="$RUN/obj_calrst_m$MUT"
echo "CALRST build mut=$MUT verilator $(verilator --version)"
verilator --binary -j 4 --build-jobs 4 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTH --x-initial unique --x-assign unique \
  --top-module tb_qkd_attn_cal_gen_r17_rst -GMUT="$MUT" -Mdir "$OBJ" $SRC > "$RUN/build_calrst_m$MUT.log" 2>&1 \
  || { tail -30 "$RUN/build_calrst_m$MUT.log"; echo "CALRST_ALL FAIL build mut=$MUT"; exit 1; }
f=0
for seed in 1 7 29; do
  "$OBJ/Vtb_qkd_attn_cal_gen_r17_rst" +verilator+rand+reset+2 +verilator+seed+$seed > "$RUN/sim_calrst_m${MUT}_s$seed.log" 2>&1 || true
  grep -E '^(CALRST|NONZERO|COMMAND)' "$RUN/sim_calrst_m${MUT}_s$seed.log" | head -6
  grep -q '^CALRST PASS' "$RUN/sim_calrst_m${MUT}_s$seed.log" || f=$((f+1))
done
if [ "$f" = 0 ]; then echo "CALRST_ALL PASS mut=$MUT seeds=3"; exit 0; fi
echo "CALRST_ALL FAIL mut=$MUT seeds=3 failed=$f"; exit 1
