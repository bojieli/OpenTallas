#!/bin/bash
# IDX.INDEX ix2 MUTANT bench (el1013 redesign-idx): the randomized equivalence bench against ot_hgi_idx_index_w with
# ix2 built at MUT = <m> (1 head weight of the next head, 2 R taken from the wrong lane, 3 keep divide).  Must print
# "IX2EQ MUT=<m> ... FAIL"; a build failure prints BUILD FAILED and exits 2 (never mistaken for a killed mutant).
#   usage (repo root): tools/hgi_unit_tput/run_ix2_mut.sh OUT [MUT=1]
set -uo pipefail
out=$(realpath -m "$1"); mu=${2:-1}; mkdir -p "$out"
V=${VERILATOR:-$( [ -x "$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" ] && echo "$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" || echo verilator)}
D=rtl/hbm_accel/generic/idx
$V --binary --timing -O2 -j 4 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ -Wno-BLKANDNBLK -Wno-MULTIDRIVEN -Wno-CMPCONST \
  --top-module tb_hgi_idx_ix2_equiv -GMUT=$mu -Mdir "$out/obj" $D/ix2/ot_hgi_idx_ix2_lane.sv $D/ix2/ot_hgi_idx_ix2_kp.sv \
  $D/ix2/ot_hgi_idx_ix2_qa.sv $D/ix2/ot_hgi_idx_ix2_pk.sv $D/ix2/ot_hgi_idx_ix2_wp.sv $D/ix2/ot_hgi_idx_ix2_ct.sv \
  $D/ix2/ot_hgi_idx_ix2.sv $D/ot_hgi_idx_index_w.sv $D/ix2/tb_hgi_idx_ix2_equiv.sv > "$out/build.log" 2>&1 \
  || { tail -20 "$out/build.log"; echo "BUILD FAILED"; exit 2; }
timeout 1800 "$out/obj/Vtb_hgi_idx_ix2_equiv" +SEED=1 +FRAMES=40 > "$out/run.log" 2>&1 || true
grep -E "IX2EQ MUT" "$out/run.log" | tail -1
grep -q "IX2EQ MUT=$mu .*PASS" "$out/run.log" && exit 0
grep -q "IX2EQ MUT=$mu .*FAIL" "$out/run.log" && exit 1
echo "BUILD FAILED: no verdict"; exit 2
