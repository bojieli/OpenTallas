#!/usr/bin/env bash
set -euo pipefail
mode=${1:?positive or mutant}; build=${2:?build directory}
mkdir -p "$build"
src=rtl/hbm_accel/generic/collective/p2p/ot_hgi_coll_control256_program.sv
if [[ $mode == mutant ]]; then
 python3 - "$src" "$build/mutant.sv" <<'PY'
import pathlib,sys
p=pathlib.Path(sys.argv[1]).read_text()
old='always @(posedge clk)pin_data<=data;'
assert p.count(old)==1
pathlib.Path(sys.argv[2]).write_text(p.replace(old,"always @(posedge clk)pin_data<=data ^ 512'b1;"))
PY
 src="$build/mutant.sv"
elif [[ $mode != positive ]]; then
 exit 2
fi
verilator --binary --timing -Wno-fatal --top-module tb_hcoll_control_capture -j 2 --Mdir "$build/obj" \
 "$src" rtl/hbm_accel/generic/collective/p2p/tb_hcoll_control_capture.sv > "$build/build.log" 2>&1
"$build/obj/Vtb_hcoll_control_capture" > "$build/run.log" 2>&1
cat "$build/run.log"
