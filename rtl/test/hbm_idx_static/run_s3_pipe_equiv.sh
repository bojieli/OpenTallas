#!/bin/bash
# HBM-IDX6: FAN32 s3 quadrant + ctl vs the s3 originals, lockstep on every port (tb_hidx_s3_equiv.sv). Verilator 5.050
# (closure daemon pin).  Run on the fleet (ot-run), never on localhost.
# Usage: run_s3_equiv.sh OUT CASE   CASE = m0 (must PASS, seeds 1 2 3) | d1 d3 d5 c6 (mutants on the new design: FAIL)
set -euo pipefail
root=$(cd "$(dirname "$0")/../../.." && pwd); cd "$root"
out=$(realpath -m "${1:-/tmp/hbm-idx6-s3-equiv}"); c=${2:-m0}; mkdir -p "$out"
g=(-GPIPE_HAZARD=1);case "$c" in m0);; d1)g+=(-GDMUT=1);; d3)g+=(-GDMUT=3);; d5)g+=(-GDMUT=5);; c6)g+=(-GCMUT=6);; d7)g+=(-GDMUT=7);; p8)g+=(-GDMUT=8);; *)echo "unknown $c";exit 2;;esac
vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; [ -x "$vl" ]||vl=verilator; "$vl" --version
src=(rtl/hbm_accel/index/sel_s3/ot_hidx_s3_q.sv rtl/hbm_accel/index/sel_s3/ot_hidx_s3_ctl.sv rtl/test/hbm_idx_static/ot_hidx_s3_q_ref.sv
 rtl/test/hbm_idx_static/ot_hidx_s3_ctl_ref.sv rtl/lib/ot_rst_relay.sv
 physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v rtl/test/hbm_idx_static/tb_hidx_s3_equiv.sv)
sha256sum "${src[@]}" rtl/test/hbm_idx_static/run_s3_pipe_equiv.sh > "$out/sources_$c.sha256"
"$vl" --binary --timing -j 4 -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN --top-module tb_hidx_s3_equiv "${g[@]}" -Mdir "$out/obj_$c" \
 "${src[@]}" > "$out/vbuild_$c.log" 2>&1 || { tail -40 "$out/vbuild_$c.log"; exit 3; }
rc=0
if [ "$c" = m0 ]; then seeds="1 2 3"; else seeds="1"; fi
for s in $seeds; do "$out/obj_$c/Vtb_hidx_s3_equiv" +seed=$s +verilator+seed+$s > "$out/vrun_${c}_s$s.log" 2>&1 || rc=1; cat "$out/vrun_${c}_s$s.log"; done
exit $rc
