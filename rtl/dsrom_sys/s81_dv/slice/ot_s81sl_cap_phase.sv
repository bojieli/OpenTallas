`timescale 1ns/1ps
`default_nettype none
// PRIVATE: fixed source-owned lane phases BEFORE the unchanged CAP tree.
// Every word retains all 70 bits; no arbitration, credits, schedule inference or arithmetic.
// Source contract and measured fixture: results/rtl/takeover3_qf_structural_1019.
module ot_s81sl_cap_phase_ring #(parameter integer D=64, parameter integer MUT=0)(
 input wire clk,rst_n,input wire [69:0] i,output wire [69:0] o);
 wire [1:0] rs;
 ot_rst_relay #(.REGIONS(2),.SYNC_STAGES(2),.TREE_STAGES(1)) rr
  (.clk(clk),.rst_n_in(rst_n),.rst_n(rs));
 localparam integer CW=$clog2(D+1);
 // Separate registered address streams: read and write NEVER select the same row.
 reg [8:0] wp,rp;
 always @(posedge clk or negedge rs[0])
  if(!rs[0])begin wp<=0;rp<=9'(512-(D-3));end
  else begin wp<=wp+1'b1;rp<=rp+1'b1;end
 reg [69:0] pin;
 always @(posedge clk)begin pin[69:2]<=i[69:2];pin[0]<=i[0];end
 always @(posedge clk or negedge rs[0])if(!rs[0])pin[1]<=0;else pin[1]<=i[1];
 wire [127:0] mq;
 ot_sram_1r1w_512x128_m4_r2c2 mem(.clk(clk),.r_ce_in(1'b1),
  .r_addr_in((MUT==2)?rp+9'd1:rp),.rd_out(mq),.w_ce_in(1'b1),
  .w_addr_in(wp),.wd_in({58'd0,pin}),.w_mask_in({128{1'b1}}),
  .rr_en(2'd0),.rr_addr(14'd0),.cr_en(2'd0),.cr_sel(14'd0));
 reg [CW-1:0] age;reg primed;
 always @(posedge clk or negedge rs[1])
  if(!rs[1])begin age<=0;primed<=0;end
  else if(!primed)begin age<=age+1'b1;primed<=(age==D-3);end
 reg [69:0] pout;reg ov;
 always @(posedge clk)pout<=mq[69:0];
 always @(posedge clk or negedge rs[1])
  if(!rs[1])ov<=0;else ov<=mq[1]&&((MUT==1)?1'b1:primed);
 assign o={pout[69:2],ov,pout[0]};
`ifndef SYNTHESIS
 initial if(D<4||D>511)$fatal(1,"phase ring D must be 4..511");
 always @(posedge clk)if(rs[0] && wp==rp)$fatal(1,"same-row read/write forbidden");
`endif
endmodule

// All eight existing lanes retain their original tree positions. The selected
// fullsix vehicle uses lanes 0..5; eight-lane silicon would require seven rings.
module ot_s81sl_cap_phase #(parameter integer ENABLE=0)(
 input wire clk,rst_n,input wire [559:0] i,output wire [559:0] o);
 genvar l;
 generate for(l=0;l<8;l=l+1)begin:g
  if(ENABLE==0||l==0)assign o[70*l+:70]=i[70*l+:70];
  else ot_s81sl_cap_phase_ring #(.D(64*l)) ring
   (.clk(clk),.rst_n(rst_n),.i(i[70*l+:70]),.o(o[70*l+:70]));
 end endgenerate
endmodule
`default_nettype wire
