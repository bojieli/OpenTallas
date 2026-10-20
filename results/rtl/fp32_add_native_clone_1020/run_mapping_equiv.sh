#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../../.."
R=$PWD;G=$R/graph/mapping_equiv;mkdir -p "$G"
cat > "$G/prove.ys" <<'YS'
read_verilog -sv /src/rtl/hdc/ot_hdc_fp32_add_lat.sv /src/rtl/hdc/ot_hdc_prefix.sv /src/rtl/hdc/ot_hdc_fastfp.sv /src/results/rtl/fp32_add_native_clone_1020/probe.sv
hierarchy -top fan32_graph_input
proc
flatten
async2sync
dffunmap
opt_clean
rename fan32_graph_input gold
design -stash gold
read_verilog /src/graph/cells.v /src/graph/mapped.v
hierarchy -top fan32_graph_input
proc
flatten
async2sync
dffunmap
opt_clean
rename fan32_graph_input gate
design -stash gate
design -copy-from gold -as gold gold
design -copy-from gate -as gate gate
equiv_make gold gate equiv
hierarchy -top equiv
equiv_simple -seq 1 -undef
equiv_induct -seq 8 -undef
equiv_status -assert
YS
docker run --rm -v "$R:/src:ro" -v "$G:/out" openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null; yosys -l /out/proof.log -s /out/prove.ys' > "$G/stdout.log" 2>&1
