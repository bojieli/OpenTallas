#!/usr/bin/env bash
# ot_hgi_dma_back_static_vp (pipelined descriptor validator, HBM-V15-HARDEN 10-15):
#  (1) lockstep vs ot_hgi_dma_back_static_cursor fed the same command 2 cycles later (valid shapes + 10 invalid
#      descriptors: every control output, request and write beat, cycle for cycle);
#  (2) the unchanged four-quadrant VM/SRAM production bench with vp as the back engine (wrapper keeps the port names).
#  MUT=1 drain row stride off by one chunk; MUT=2 product operand truncated one bit too far (rows-1 6 bits).
set -euo pipefail
out=${1:?output};mut=${2:-0};mkdir -p "$out"
d=rtl/hbm_accel/generic/peers/static
m=physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
cp "$d/ot_hgi_dma_back_static_vp4_banks.sv" "$out/vp.sv"
case "$mut" in
 1) sed -i "s/drain_row_hbm+37'(hbm_stride)/drain_row_hbm+37'(hbm_stride)+37'd256/g" "$out/vp.sv";;
 2) sed -i "s/wire \[6:0\] a_rows_m1=7'(a_mv\[192:186\]-7'd1);/wire [6:0] a_rows_m1=7'(6'(a_mv[191:186]-6'd1));/" "$out/vp.sv";;
esac
if [ "$mut" != 0 ];then ! cmp -s "$out/vp.sv" "$d/ot_hgi_dma_back_static_vp4_banks.sv";fi
iverilog -g2012 -s tb_dma_back_vp4_banks_equiv -o "$out/eq.vvp" "$m" "$d/ot_hgi_dma_back_static_cursor.sv" "$d/ot_hgi_dma_back_static_vp_banks.sv" "$out/vp.sv" "$d/tb_dma_back_vp4_banks_equiv.sv"
vvp "$out/eq.vvp" > "$out/eq.log" 2>&1 || { cat "$out/eq.log";exit 1; };cat "$out/eq.log";grep -q 'DMA_VP_EQUIV PASS' "$out/eq.log"
cat > "$out/as_back.sv" <<'SV'
module ot_hgi_dma_back_static #(parameter integer STK=0, parameter integer QID=STK, parameter [35:0] STACK_BYTES=36'd22500000000, parameter integer MUT=0)(
 input wire clk,rst_n,input wire [31:0] cycle,input wire mv_v,input wire [226:0] mv,input wire [31:0] issue_at,drain_at,
 input wire mv_wb_bank,input wire [15:0] mv_wb_epoch,output wire mv_src,mv_done,mv_fault,output wire quiet,busy,
 output wire [8*17-1:0] rq,input wire [8*257-1:0] rr,output wire wb_reserve_v,wb_reserve_bank,wb_fill_bank,
 output wire [15:0] wb_reserve_epoch,wb_fill_epoch,output wire [11:0] wb_reserve_sectors,output wire [31:0] wb_reserve_base,
 output wire wb_fill_start,input wire wb_ready,output wire [8*289-1:0] wd,input wire [11:0] wa);
 ot_hgi_dma_back_static_vp4_banks #(.STK(STK),.QID(QID),.STACK_BYTES(STACK_BYTES),.MUT(MUT)) u(.clk(clk),.clk_bank({8{clk}}),.rst_n(rst_n),.cycle(cycle),
  .mv_v(mv_v),.mv(mv),.issue_at(issue_at),.drain_at(drain_at),.mv_wb_bank(mv_wb_bank),.mv_wb_epoch(mv_wb_epoch),
  .mv_src(mv_src),.mv_done(mv_done),.mv_fault(mv_fault),.quiet(quiet),.busy(busy),.rq(rq),.rr(rr),.wb_reserve_v(wb_reserve_v),
  .wb_reserve_bank(wb_reserve_bank),.wb_fill_bank(wb_fill_bank),.wb_reserve_epoch(wb_reserve_epoch),.wb_fill_epoch(wb_fill_epoch),
  .wb_reserve_sectors(wb_reserve_sectors),.wb_reserve_base(wb_reserve_base),.wb_fill_start(wb_fill_start),.wb_ready(wb_ready),.wd(wd),.wa(wa));
endmodule
SV
# DESC_LAT4: the actual dispatcher takes two front-end edges before the
# engine command. Queue the late PRE descriptor two edges earlier, preserving
# its absolute issue/drain cycles, every data beat and the original fence price.
python3 - "$d/tb_dma_back_static.sv" "$out/production_tb.sv" <<'PYCODE'
import pathlib,sys
s=pathlib.Path(sys.argv[1]).read_text()
a='while(cycle<drain_at+84)';b='while(cycle<drain_at+82)'
assert s.count(a)==1
pathlib.Path(sys.argv[2]).write_text(s.replace(a,b))
PYCODE
echo STATIC_DESC_LAT4_PRE_COMMAND_ADVANCE_2_DATA_CALENDAR_UNCHANGED
mr=physical/asap7_memory_macros
iverilog -g2012 -s tb_dma_back_static -o "$out/production.vvp" "$d/ot_hgi_dma_back_static_vp_banks.sv" "$out/vp.sv" "$out/as_back.sv" "$d/ot_hgi_b2_swap_disp_static.sv" "$d/ot_hgi_b2_swap_grp_static.sv" rtl/hbm_accel/generic/vm/static/ot_vms_bank_static.sv "$mr/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v" "$mr/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v" "$out/production_tb.sv"
vvp "$out/production.vvp" > "$out/production.log" 2>&1 || { cat "$out/production.log";exit 1; };cat "$out/production.log";grep -q 'PASS DMA static actual production' "$out/production.log"
echo DMA_VP4_BANKS_BENCH_PASS
