`timescale 1ns/1ps
// Private opt-in mechanism vehicle, not a production module or physical N.
// All 250 input payload bits move together. Reset asserts immediately and
// releases D edges later; the existing leaf/reset relay is unchanged.
module codex_obs_delay_candidate #(
 parameter integer D=20, MUT=0,
 parameter [511:0] SYNC_MASK=512'h3ffff0000000000000000000000000000
)(
 input wire clk,rst_n,input wire[208:0] obs,
 input wire q_v,input wire[7:0] q_idx,input wire[31:0] q_d,
 output wire r_v,output wire[7:0] r_idx,output wire[31:0] r_d
);
 wire [249:0] incoming={obs,q_v,q_idx,q_d};
 wire [249:0] delayed;
 wire leaf_rst_n;
 generate if(D==0)begin:g_bypass
  assign delayed=incoming;assign leaf_rst_n=rst_n;
 end else begin:g_delay
  (* keep="true" *) reg [249:0] payload[0:D-1];
  (* keep="true" *) reg [D-1:0] release_pipe;
  always @(posedge clk or negedge rst_n)
   if(!rst_n)release_pipe<='0;
   else release_pipe<=(release_pipe<<1)|1'b1;
  always @(posedge clk)begin
   payload[0]<=incoming;
   for(integer j=1;j<D;j=j+1)payload[j]<=payload[j-1];
  end
  localparam integer OD=(MUT==1 && D>1)?D-2:D-1;
  localparam integer QD=(MUT==2 && D>1)?D-2:D-1;
  localparam integer RD=(MUT==4 && D>1)?D-2:D-1;
  wire [208:0] obs_delayed=payload[OD][249:41];
  assign delayed={(MUT==3)?{1'b0,obs_delayed[207:0]}:obs_delayed,payload[QD][40:0]};
  assign leaf_rst_n=release_pipe[RD];
 end endgenerate
 ot_hbm_obs_leaf #(.N(209),.LID(4),.SYNC_MASK(SYNC_MASK)) u_actual(
  .clk(clk),.rst_n(leaf_rst_n),.obs(delayed[249:41]),
  .q_v(delayed[40]),.q_idx(delayed[39:32]),.q_d(delayed[31:0]),
  .r_v(r_v),.r_idx(r_idx),.r_d(r_d));
endmodule
