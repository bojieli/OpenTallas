`timescale 1ns/1ps
// Exactly3 releaseedges, including the pin landing. Only2 direct asynchronous portloads.
// Each middle pair drives at most32 data /32 reset pins, respectively.
module ot_s81eng_reset3n32 #(parameter integer LEAVES=62)(
 input wire clk,rst_n_in,output wire[LEAVES-1:0] rst_n,output wire early_n);
 localparam integer GROUPS=(LEAVES+31)/32;
 generate if(LEAVES<1 || LEAVES>256)begin:g_bad ot_s81eng_reset3n32_bad_leaf_count trap();end endgenerate
`ifdef OT_S81ENG_RST_TIMED
 // R13: this core input is already die-synchronous. Private delivery is three
 // ordinary clocked edges for assertion and release; no second CDC root.
 (* keep=1 *)reg root_d;
 always@(posedge clk)root_d<=rst_n_in;
 assign early_n=root_d;
 wire[GROUPS-1:0]mid;
 for(genvar g=0;g<GROUPS;g=g+1)begin:g_tmid
  (* keep=1 *)reg q;
  always@(posedge clk)q<=root_d;
  assign mid[g]=q;
 end
 for(genvar l=0;l<LEAVES;l=l+1)begin:g_tleaf
  (* keep=1 *)reg q;
  always@(posedge clk)q<=mid[l/32];
  assign rst_n[l]=q;
 end
`else
 (* keep=1,async_reg=1 *)reg root_d,root_r;
 always @(posedge clk or negedge rst_n_in)if(!rst_n_in)begin root_d<=0;root_r<=0;end else begin root_d<=1;root_r<=1;end
 assign early_n=root_d;
 wire[GROUPS-1:0] mid_d,mid_r;
 for(genvar g=0;g<GROUPS;g=g+1)begin:g_mid
  (* keep=1,async_reg=1 *)reg d,r;
  always @(posedge clk or negedge root_r)if(!root_r)begin d<=0;r<=0;end else begin d<=root_d;r<=root_d;end
  assign mid_d[g]=d;assign mid_r[g]=r;
 end
 for(genvar l=0;l<LEAVES;l=l+1)begin:g_leaf
  (* keep=1,async_reg=1 *)reg q;
  always @(posedge clk or negedge mid_r[l/32])if(!mid_r[l/32])q<=0;else q<=mid_d[l/32];
  assign rst_n[l]=q;
 end
`endif
endmodule
