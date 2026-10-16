#!/usr/bin/env bash
# H-HARDEN 2026-10-16: folded DMA parent (collar MODE1/CW308/RELF2/TGT_PIN inside ot_hgi_dma_back_static_vp4_banks_cp)
# programmed through the real host ingress, lockstep with the die composition it replaces; 7 compiled valid moves
# (2,769 write beats), every output every edge.  Negatives: wrong command slice (CP_MUT 1) and wrong identity strap
# (tgt 105 on the folded parent) must FAIL.
#   bench_dma_vp4_banks_cp.sh <out>
set -euo pipefail
out=${1:?out}; mkdir -p "$out"
P=rtl/hbm_accel/generic/peers/static
S=(physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
   rtl/hbm_accel/host_static_20261015/ot_static_cmd_target.sv rtl/hbm_accel/host_static_20261015/ot_hbm_host_static_ingress.sv
   $P/ot_hgi_dma_back_static_vp_banks.sv $P/ot_hgi_dma_back_static_vp4_banks.sv $P/ot_hgi_dma_back_static_vp4_banks_cp.sv)
iverilog -g2012 -s tb_dma_vp4_banks_cp -o "$out/pos.vvp" "${S[@]}" $P/tb_dma_vp4_banks_cp.sv > "$out/pos.build.log" 2>&1
vvp "$out/pos.vvp" > "$out/pos.log" 2>&1; grep 'CP_FOLD PASS' "$out/pos.log"
iverilog -g2012 -DCP_MUT=1 -s tb_dma_vp4_banks_cp -o "$out/slice.vvp" "${S[@]}" $P/tb_dma_vp4_banks_cp.sv > "$out/slice.build.log" 2>&1
if vvp "$out/slice.vvp" > "$out/slice.log" 2>&1 && grep -q 'CP_FOLD PASS' "$out/slice.log"; then echo 'slice mutant survived'; exit 1; fi
grep -m1 -E 'FATAL|FAIL' "$out/slice.log" | sed 's/^/slice mutant REJECTED: /'
sed "s/\.tgt(8'd104),\.clk_bank/.tgt(8'd105),.clk_bank/" $P/tb_dma_vp4_banks_cp.sv > "$out/tb_strap.sv"
cmp -s "$out/tb_strap.sv" $P/tb_dma_vp4_banks_cp.sv && { echo 'strap mutant not applied'; exit 3; }
iverilog -g2012 -s tb_dma_vp4_banks_cp -o "$out/strap.vvp" "${S[@]}" "$out/tb_strap.sv" > "$out/strap.build.log" 2>&1
if vvp "$out/strap.vvp" > "$out/strap.log" 2>&1 && grep -q 'CP_FOLD PASS' "$out/strap.log"; then echo 'strap mutant survived'; exit 1; fi
grep -m1 -E 'FATAL|FAIL' "$out/strap.log" | sed 's/^/strap mutant REJECTED: /'
echo 'DMA_CP_FOLD_GATE PASS (folded parent == die composition through host ingress; slice and strap mutants rejected)'
