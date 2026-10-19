#!/bin/bash
set -euo pipefail
out=$(realpath -m ../mutants)
mkdir -p "$out"
v=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
for m in 7 8; do
 $v --binary --timing -Wno-fatal -j 8 --top-module tb_idx_link_pipe --Mdir "$out/obj$m" -GMUT=$m -GSAFE_RING=1 -GSAFE_CARRY=1 -GSAFE_COPIES=1 -GEMIT_GAP=0 rtl/test/hbm_idx_static/tb_idx_link_pipe.sv rtl/hbm_accel/index/ot_hbm_idx_topk_link_static_p.sv rtl/hbm_accel/index/ot_hbm_idx_topk_link_static.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v >"$out/build$m.log" 2>&1
 set +e
 (ulimit -c 0; "$out/obj$m/Vtb_idx_link_pipe") >"$out/run$m.log" 2>&1
 rc=$?
 set -e
 if [ "$rc" = 0 ]; then echo "MUTANT$m ESCAPED"; exit 1; fi
 grep -E "IDX_LINK_PIPE_TOTAL MUT$m .*errors[1-9]" "$out/run$m.log"
done
