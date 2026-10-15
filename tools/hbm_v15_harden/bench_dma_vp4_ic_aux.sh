#!/bin/bash
set -euo pipefail
out=${1:?};mkdir -p "$out"
d=rtl/hbm_accel/generic/peers/static
m=physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
sed 's/ot_hgi_dma_back_static_vp4_controller dut/ot_hgi_dma_back_static_vp4_controller_ic dut/' "$d/tb_dma_vp4_native_fault.sv" > "$out/fault.sv"
iverilog -g2012 -s tb_dma_vp4_native_fault -o "$out/fault.vvp" "$d/ot_hgi_dma_back_static_vp4_ic.sv" "$out/fault.sv"
vvp "$out/fault.vvp"
sed 's/ot_hgi_dma_back_static_vp4_banks dut/ot_hgi_dma_back_static_vp4_banks_ic dut/' "$d/tb_dma_vp4_banks_clock.sv" > "$out/clock.sv"
for mode in positive collapsed swapped;do
 cp "$d/ot_hgi_dma_back_static_vp4_ic.sv" "$out/$mode.sv"
 case "$mode" in
 collapsed) sed -i 's/\.clk(clk_bank\[b\])/\.clk(clk)/' "$out/$mode.sv";;
 swapped) sed -i 's/\.clk(clk_bank\[b\])/\.clk(clk_bank[(b+1)%8])/' "$out/$mode.sv";;
 esac
 if [ "$mode" != positive ];then ! cmp -s "$out/$mode.sv" "$d/ot_hgi_dma_back_static_vp4_ic.sv";fi
 iverilog -g2012 -s tb_dma_vp4_banks_clock -o "$out/$mode.vvp" "$m" "$out/$mode.sv" "$out/clock.sv"
 if [ "$mode" = positive ];then
  vvp "$out/$mode.vvp" > "$out/$mode.log" 2>&1
  cat "$out/$mode.log"
 else
  set +e
  vvp "$out/$mode.vvp" > "$out/$mode.log" 2>&1
  rc=$?
  set -e
  test "$rc" = 1
  grep -q 'clock ownership' "$out/$mode.log"
  cat "$out/$mode.log"
 fi
done
echo DMA_IC_AUX_PASS checks=26 clock_checks=64 clock_mutants=2
