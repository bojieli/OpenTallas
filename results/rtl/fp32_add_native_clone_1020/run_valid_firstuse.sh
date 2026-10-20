#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../../.."
R=$PWD;G=$R/graph/valid_firstuse;mkdir -p "$G"
cat > "$G/prove.ys" <<'YS'
read_verilog -sv /src/graph/cells.v /src/graph/native.v /src/rtl/hdc/ot_hdc_fp32_add_lat.sv /src/rtl/hdc/ot_hdc_prefix.sv /src/rtl/hdc/ot_hdc_fastfp.sv /src/results/rtl/fp32_add_native_clone_1020/probe.sv /src/results/rtl/fp32_add_native_clone_1020/valid_firstuse_miter.sv
hierarchy -top fan32_valid_miter
proc
flatten
opt_clean
async2sync
dffunmap
opt_clean
sat -seq 20 -set-def-inputs -set clk 1 -set-at 1 rst_n 0 -prove bad 0 -prove-skip 1 -verify -show-inputs -show-outputs -dump_vcd /out/counterexample.vcd
YS
docker run --rm -v "$R:/src:ro" -v "$G:/out" openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null; yosys -l /out/proof.log -s /out/prove.ys' > "$G/stdout.log" 2>&1
