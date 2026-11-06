`timescale 1ns/1ps
`default_nettype none
// Optional WBQ per-lane store; canonical source/recipes unchanged.
module ot_wbq_root_store #(parameter integer LANE=0)(
 input wire fifo_clk,hbm_clk,srst,hrst,
 input wire [1:0]root_id,input wire [31:0]base,
 input wire [11:0]total,committed,ordinal,
 input wire filling,fill_bank,copy_q,copy_bank,copy_start,s_stop,
 input wire [255:0]wd,input wire wd_v,fifo_re,
 output wire [287:0]fifo_head,output wire fifo_empty
);
 reg [6:0]copy_row;reg [5:0]pending_row;reg read_pending;
 wire [4:0]lane={root_id,3'(LANE)};
 wire [31:0]sector=base+{pending_row,5'b0}+lane;
 wire fifo_full;
 wire fifo_we=copy_q&&read_pending&&!fifo_full&&!s_stop;
 wire mem_read=copy_q&&(!read_pending||fifo_we)&&copy_row*32+int'(lane)<committed&&!s_stop;
 wire [255:0]mem_data;
 ot_hbm_accel_cdc_fifo #(.W(288),.AW(2)) u_fifo(
  .wclk(fifo_clk),.wrst_n(srst),.we(fifo_we),.wdata({sector,mem_data}),.full(fifo_full),.rd_freed(),
  .rclk(hbm_clk),.rrst_n(hrst),.re(fifo_re),.rdata(fifo_head),.empty(fifo_empty));
 ot_sram_1r1w_128x256_m1_r2c2 u_payload(
  .clk(fifo_clk),.r_ce_in(mem_read),.r_addr_in({copy_bank,copy_row[5:0]}),.rd_out(mem_data),
  .w_ce_in(filling&&!s_stop&&ordinal+LANE<total&&ordinal[4:3]==root_id&&wd_v),
  .w_addr_in({fill_bank,ordinal[10:5]}),.wd_in(wd),.w_mask_in({256{1'b1}}),
  .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
 always @(posedge fifo_clk or negedge srst)begin
  if(!srst)begin copy_row<=0;pending_row<=0;read_pending<=0;end
  else if(copy_start)begin copy_row<=0;pending_row<=0;read_pending<=0;end
  else begin
   if(fifo_we)read_pending<=0;
   if(mem_read)begin read_pending<=1;pending_row<=copy_row[5:0];copy_row<=copy_row+1'b1;end
  end
 end
endmodule

// Optional four-lane hierarchy cut. No new state, reset, clock or edge.
// FACES=1 preserves each existing 256-bit fifo_clk WD capture exactly once.
// Packed lane j occupies [256*j+:256] and [288*j+:288]; LANE_BASE is 0 or 4.
// Every FIFO retains its own fifo_clk write side and hbm_clk read side.
module ot_wbq_root_store_group4 #(
 parameter integer LANE_BASE=0, parameter integer FACES=1
)(
 input wire fifo_clk,hbm_clk,srst,hrst,
 input wire [1:0]root_id,input wire [31:0]base,
 input wire [11:0]total,committed,ordinal,
 input wire filling,fill_bank,copy_q,copy_bank,copy_start,s_stop,
 input wire [1023:0]wd,input wire [3:0]wd_v,fifo_re,
 output wire [1151:0]fifo_head,output wire [3:0]fifo_empty
);
 genvar lane;
 generate for(lane=0;lane<4;lane=lane+1)begin:g_lane
  if(FACES!=0)begin:g_face
   ot_wbq_root_store_face #(.LANE(LANE_BASE+lane)) u_store(
    .fifo_clk(fifo_clk),.hbm_clk(hbm_clk),.srst(srst),.hrst(hrst),
    .root_id(root_id),.base(base),.total(total),.committed(committed),.ordinal(ordinal),
    .filling(filling),.fill_bank(fill_bank),.copy_q(copy_q),.copy_bank(copy_bank),
    .copy_start(copy_start),.s_stop(s_stop),.wd(wd[256*lane+:256]),.wd_v(wd_v[lane]),
    .fifo_re(fifo_re[lane]),.fifo_head(fifo_head[288*lane+:288]),.fifo_empty(fifo_empty[lane]));
  end else begin:g_raw
   ot_wbq_root_store #(.LANE(LANE_BASE+lane)) u_store(
    .fifo_clk(fifo_clk),.hbm_clk(hbm_clk),.srst(srst),.hrst(hrst),
    .root_id(root_id),.base(base),.total(total),.committed(committed),.ordinal(ordinal),
    .filling(filling),.fill_bank(fill_bank),.copy_q(copy_q),.copy_bank(copy_bank),
    .copy_start(copy_start),.s_stop(s_stop),.wd(wd[256*lane+:256]),.wd_v(wd_v[lane]),
    .fifo_re(fifo_re[lane]),.fifo_head(fifo_head[288*lane+:288]),.fifo_empty(fifo_empty[lane]));
  end
 end endgenerate
endmodule
