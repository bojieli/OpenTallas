#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
OUT=$(realpath -m "$1")
mkdir -p "$OUT"
YOSYS=${YOSYS:-$HOME/.local/opentallas-tools/yosys-0.68/bin/yosys}
"$YOSYS" -Q -T -p "read_verilog -sv -lib physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2_bb.v; read_verilog -sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_sfu_q.sv rtl/hdc/ot_hdc_vstream_lane.sv; chparam -set WR 16 -set AW 24 -set NW 18 -set LANE 0 -set KV_FP8 1 -set ML 1 -set TLS 1 -set QLA 3 -set QLM 3 -set SFH 0 ot_hdc_vstream_lane; synth -top ot_hdc_vstream_lane -flatten -noabc -nofsm -noshare; write_json $OUT/generic.json" > "$OUT/frontend.log" 2>&1
python3 tools/qwen_flat_native_2000/bound_flat_graph.py "$OUT/generic.json" --top ot_hdc_vstream_lane --out "$OUT/generated" > "$OUT/construction.log" 2>&1
