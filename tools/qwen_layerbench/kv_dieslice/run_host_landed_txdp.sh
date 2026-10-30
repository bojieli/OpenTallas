#!/bin/bash
# Native SRAM link-end reproduction of the KV HOST record landing-latency failure.
# Usage: run_host_landed_txdp.sh OUT. Run with ot-run; no die/token/physical claim.
set -euo pipefail
R=$(cd "$(dirname "$0")/../../.." && pwd)
D=$(realpath -m "${1:?OUT}")
mkdir -p "$D"
SRC=("$R/rtl/test/qwen_split/tb_host_landed_txdp.sv"
 "$R/rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_sfm.sv"
 "$R/rtl/qwen_sys/context_transport_20261014/qkd_host_record_port.sv"
 "$R/rtl/qwen_sys/context_transport_20261014/qkd_context_records.sv"
 "$R/rtl/qwen_sys/split_20261014/ot_qwen_crc_parallel.sv"
 "$R/physical/asap7_memory_macros_v2/d2d_sram_1r1w_64x137_m1_r2c2_p192/d2d_sram_1r1w_64x137_m1_r2c2_p192.v")
sha256sum "${SRC[@]}" > "$D/source.sha256"
for m in 0 1 2; do
  iverilog -g2012 -s tb_host_landed_txdp -Ptb_host_landed_txdp.MUT=$m -o "$D/tb$m.vvp" "${SRC[@]}" >"$D/build$m.log" 2>&1
  vvp "$D/tb$m.vvp" >"$D/run$m.log" 2>&1
  cat "$D/run$m.log"
done
