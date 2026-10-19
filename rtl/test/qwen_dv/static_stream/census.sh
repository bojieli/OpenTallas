#!/bin/bash
set -euo pipefail
mkdir -p out
for mode in 0 1; do
 yosys -Q -T -p "read_verilog -sv rtl/qwen_dv/qfd_dv_stream.sv rtl/qwen_dv/qfd_dv_stream_packer.sv; chparam -set STATIC_PACKER $mode qfd_dv_stream_packer; hierarchy -top qfd_dv_stream_packer; synth -top qfd_dv_stream_packer -flatten -noabc -nofsm -noshare; write_json out/net$mode.json; stat" > "out/yosys$mode.log" 2>&1
 python3 tools/qwen_dv/soft_cone_inventory.py "out/net$mode.json" --top qfd_dv_stream_packer --out "out/inventory$mode.json" > "out/summary$mode.log"
done
