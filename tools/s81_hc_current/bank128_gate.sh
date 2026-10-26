#!/usr/bin/env bash
set -euo pipefail
out=${1:?output directory};mkdir -p "$out"
base=rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_ccf_bankpipe.sv
cand=rtl/dsrom_sys/s81_suhc/static/ot_s81_hc_ccf_bankpipe128.sv
fifo=rtl/link/ot_fifo_sram_fwft.sv
tb=rtl/dsrom_sys/s81_suhc/test/tb_s81_hc_bank128.sv
mem=physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v
iverilog -g2012 -s tb_s81_hc_bank128 -o "$out/base.vvp" "$base" "$cand" "$fifo" "$mem" "$tb"
vvp "$out/base.vvp" > "$out/positive.log" 2>&1
grep -q '^BANK128_PASS$' "$out/positive.log"
if vvp "$out/base.vvp" +STOP=1 > "$out/stopped_root.log" 2>&1;then exit 1;fi
grep -q 'BANK128_FAIL' "$out/stopped_root.log"
sed -e 's/module ot_fifo_sram_fwft #/module ot_fifo_sram_fwft_slice_mut #/' -e 's/inf_c <= rd_arr;/inf_c <= rd_arr ^ (s==3);/' "$fifo" > "$out/fifo_mut.sv"
sed 's/ot_fifo_sram_fwft #/ot_fifo_sram_fwft_slice_mut #/' "$cand" > "$out/cand_mut.sv"
iverilog -g2012 -s tb_s81_hc_bank128 -o "$out/slice.vvp" "$base" "$out/cand_mut.sv" "$fifo" "$out/fifo_mut.sv" "$mem" "$tb"
if vvp "$out/slice.vvp" > "$out/slice_mutant.log" 2>&1;then exit 1;fi
grep -q 'BANK128_FAIL' "$out/slice_mutant.log"
echo BANK128_COMPONENT_GATE_PASS
