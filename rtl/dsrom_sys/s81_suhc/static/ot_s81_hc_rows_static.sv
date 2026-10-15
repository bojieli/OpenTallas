`timescale 1ns/1ps
`default_nettype none
// Compiler-addressed collective rows. No FIFO, credit, ready or retry state.
// Each declared write/read pulse keeps its cycle even when identity checks fail.
// All payload storage is the actual mapped 128x256 SRAM macro.
module ot_s81_hc_rows_static #(
 parameter integer W=8192,ROWS=20,SLOTS=2,TAG_W=32
)(
 input wire clk,rst_n,
 input wire wr_v,wr_slot,
 input wire [4:0] wr_row,
 input wire [TAG_W-1:0] wr_tag,
 input wire [W-1:0] wr_data,
 input wire reserve_v,reserve_slot,
 input wire [TAG_W-1:0] reserve_tag,
 input wire rd_v,rd_slot,
 input wire [4:0] rd_row,
 input wire [TAG_W-1:0] rd_tag,
 output reg out_v,
 output reg [W-1:0] out_data,
 output reg [TAG_W-1:0] out_tag,
 output reg [4:0] out_row,
 output reg out_slot,
 output reg fault
);
 localparam integer NM=(W+255)/256;
 reg wv,ws,rv,rs,bv,bs;
 reg [4:0] wi,ri;
 reg [TAG_W-1:0] wt,rt,bt;
 reg [W-1:0] wd;
 always @(posedge clk)begin
  ws<=wr_slot;wi<=wr_row;wt<=wr_tag;wd<=wr_data;
  rs<=rd_slot;ri<=rd_row;rt<=rd_tag;bs<=reserve_slot;bt<=reserve_tag;
 end
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin wv<=0;rv<=0;bv<=0;end
  else begin wv<=wr_v;rv<=rd_v;bv<=reserve_v;end
 reg [SLOTS*ROWS-1:0] written;
 reg [TAG_W-1:0] owner[0:SLOTS-1];
 reg [SLOTS-1:0] owned;
 wire [6:0] wa=7'(ws*ROWS+wi),ra=7'(rs*ROWS+ri);
 wire [NM*256-1:0] memory_q;
 wire [NM*256-1:0] padded={{(NM*256-W){1'b0}},wd};
 for(genvar m=0;m<NM;m=m+1)begin:g_memory
  ot_sram_1r1w_128x256_m1_r2c2 ram(.clk(clk),.r_ce_in(rv),.r_addr_in(ra),.rd_out(memory_q[m*256+:256]),
   .w_ce_in(wv),.w_addr_in(wa),.wd_in(padded[m*256+:256]),.w_mask_in({256{1'b1}}),
   .rr_en(2'b00),.rr_addr(14'd0),.cr_en(2'b00),.cr_sel(16'd0));
 end
 reg read_q;
 reg [TAG_W-1:0] read_tag_q;
 reg [4:0] read_row_q;
 reg read_slot_q;
 always @(posedge clk)begin
  read_tag_q<=rt;read_row_q<=ri;read_slot_q<=rs;
  out_data<=memory_q[W-1:0];out_tag<=read_tag_q;out_row<=read_row_q;out_slot<=read_slot_q;
 end
 integer k;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin written<=0;owned<=0;read_q<=0;out_v<=0;fault<=0;end
  else begin
   read_q<=rv;out_v<=read_q;
   if(bv)begin
    if(bs>=SLOTS)fault<=1;
    else begin
     owned[bs]<=1;owner[bs]<=bt;
     for(k=0;k<ROWS;k=k+1)written[bs*ROWS+k]<=0;
    end
   end
   if(wv)begin
    if(ws>=SLOTS||wi>=ROWS||!owned[ws]||owner[ws]!=wt||written[ws*ROWS+wi]||(bv&&bs==ws))fault<=1;
    else written[ws*ROWS+wi]<=1;
   end
   if(rv)begin
    // SRAM is read-before-write. Same-edge first write is not visible.
    if(rs>=SLOTS||ri>=ROWS||!owned[rs]||owner[rs]!=rt||!written[rs*ROWS+ri]||(bv&&bs==rs))fault<=1;
   end
  end
 end
`ifndef SYNTHESIS
 initial begin
  if(SLOTS!=2||ROWS>32||ROWS*SLOTS>128||W<1)$fatal(1,"HC static SRAM shape");
 end
`endif
endmodule
`default_nettype wire
