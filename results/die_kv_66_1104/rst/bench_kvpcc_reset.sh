#!/bin/bash
# DIE-KV-66/LEC: PC core pin reset bench (iverilog). usage: bench_kvpcc_reset.sh OUTDIR MUT   (MUT 0 positive, 1..3 mutants) [LINK_TRAIN]
set -eu; D=$(cd "$(dirname "$0")" && pwd); R=$(cd "$D/../../.." && pwd); O=$1; M=$2; T=${3:-0}; mkdir -p "$O"
iverilog -g2012 -P tb_kvpcc_reset_contract.MUT=$M -P tb_kvpcc_reset_contract.LINK_TRAIN=$T -o "$O/tb_$M" "$D/tb_kvpcc_reset_contract.sv" "$R/results/die_kv_26_1029/rst/bind26b_cells.sv" \
  "$R/rtl/common/ot_meso_fifo.sv" "$R/rtl/common/ot_dp_clk_landing.sv" "$R/rtl/common/ot_dp_clk_landing_ca.sv" "$R/rtl/lib/ot_reset_sync.sv" "$R/rtl/qwen_sys/ot_qwen_sys_rst_seq.sv" "$R/rtl/qwen_sys/host_20261013/qkd_host_rst_role_pins.sv"
vvp -n "$O/tb_$M" | grep -E "KVPCCRST|FATAL" | head -n 12
