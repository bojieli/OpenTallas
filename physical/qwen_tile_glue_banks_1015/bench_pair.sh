#!/bin/bash
# r13 NL helper: exact benches of the PM-H-S face masters. usage: bench_pair.sh OUT {x1028|w514} MUT
set -euo pipefail
out=$1; which=$2; mutant=${3:-0}; mkdir -p "$out"
src="rtl/qwen_sys/head_staging_20261015/ot_qkh_packet_stage.sv rtl/lib/ot_rst_relay.sv rtl/qwen_sys/tile_glue_banks_20261015/qwen_glue_x1028.sv rtl/qwen_sys/tile_glue_banks_20261015/qwen_glue_w514.sv"
if [[ $which == x1028 ]]; then
 iverilog -g2012 -s tb_glue_x1028 -Ptb_glue_x1028.MUT="$mutant" -o "$out/bench.vvp" rtl/test/qwen_head_staging/tb_glue_x1028.sv $src
else
 iverilog -g2012 -DQKH_PACKET_DUT=qwen_glue_w514 -s tb_packet_stage -Ptb_packet_stage.W=514 -Ptb_packet_stage.MUT="$mutant" -o "$out/bench.vvp" rtl/test/qwen_head_staging/tb_packet_stage.sv $src
fi
vvp "$out/bench.vvp" | tee "$out/result.log"
if grep -q '^FAIL ' "$out/result.log"; then exit 1; fi
