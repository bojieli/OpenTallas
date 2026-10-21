#!/bin/bash
# HF-5a fc_xr2 bench (run from the repo root): run_bench.sh <workdir> [MUT_X1|MUT_L1]; Verilator 5.050 (closure daemon pin).
set -u
W=$1; M=${2:-}
export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
mkdir -p "$W"
D=(); [ -n "$M" ] && D=(-DOT_SMH_FC_XR2_$M)
verilator --version
verilator --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -DSYNTHESIS "${D[@]}" \
  --top-module tb_fc_xr2 --Mdir "$W/obj" -o tb \
  rtl/hbm_accel/sm/test/tb_fc_xr2.sv rtl/hbm_accel/sm/ot_hbm_accel_smh_fc_xr2.sv \
  rtl/hbm_accel/sm/ot_hbm_accel_smh.sv rtl/lib/ot_rst_relay.sv > "$W/build.log" 2>&1 || { tail -20 "$W/build.log"; echo "FCXR2 BUILD FAIL"; exit 1; }
"$W/obj/tb" | tee "$W/run.log"
grep -q "FCXR2 PASS" "$W/run.log"
