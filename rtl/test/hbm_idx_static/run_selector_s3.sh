#!/bin/bash
# L2H-IDXSEL s3: Verilator 5.050 (the closure daemon's pinned version) full-shape bench of the landed IDX selector cluster
# ot_hbm_idx_selector_s3 (tb_selector_s3.sv).  Run on the fleet (ot-run), never on localhost.
# Usage: run_selector_s3.sh OUT CASE     CASE = m0 (must PASS) | d1 d3 d5 d6 (design mutants) | rt7 (choose spacing one
#        edge short) | dr3 (scan drain one short) | l1 l2 (lp landing 0 bypassed / read K+1): all must FAIL with
#        "fullshape exact selector mismatch".  Exit = the simulator's exit code.
set -euo pipefail
root=$(cd "$(dirname "$0")/../../.." && pwd)
cd "$root"
out=$(realpath -m "${1:-/tmp/hbm-idx-selector-s3}")
c=${2:-m0}
g=()
case "$c" in
 m0) ;; d1) g=(-GDMUT=1);; d3) g=(-GDMUT=3);; d5) g=(-GDMUT=5);; d6) g=(-GDMUT=6);;
 rt7) g=(-GRT=7);; dr3) g=(-GDRAIN=3);; l1) g=(-GMUT=1);; l2) g=(-GMUT=2);;
 *) echo "unknown case $c"; exit 2;;
esac
mkdir -p "$out/vec"
python3 tools/hbm_idx_s3_selector_vectors.py "$out/vec"
vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
[ -x "$vl" ]||vl=verilator
"$vl" --version
src=(rtl/hbm_accel/index/sel_s3/ot_hbm_idx_selector_s3.sv rtl/hbm_accel/index/sel_s3/lp/ot_hidx_s3_flat_lp.sv
 rtl/hbm_accel/index/sel_s3/ot_hidx_s3_ctl.sv rtl/hbm_accel/index/sel_s3/ot_hidx_s3_q.sv rtl/common/landed_parent/ot_pl_land.sv
 rtl/lib/ot_rst_relay.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v
 rtl/test/hbm_idx_static/tb_selector_s3.sv)
sha256sum "${src[@]}" tools/hbm_idx_s3_selector_vectors.py rtl/test/hbm_idx_static/run_selector_s3.sh > "$out/sources_$c.sha256"
"$vl" --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style --top-module tb_selector_s3 "${g[@]}" -Mdir "$out/obj_$c" \
 "${src[@]}" > "$out/vbuild_$c.log" 2>&1 || { tail -40 "$out/vbuild_$c.log"; exit 3; }
set +e
(cd "$out/vec" && "$out/obj_$c/Vtb_selector_s3") > "$out/vrun_$c.log" 2>&1
rc=$?
set -e
cat "$out/vrun_$c.log"
exit "$rc"
