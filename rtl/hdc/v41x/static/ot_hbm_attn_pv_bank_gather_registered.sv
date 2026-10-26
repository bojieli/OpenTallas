`timescale 1ns/1ps
`default_nettype none
// Source-compatible +2edge successor: payload capture is unconditional;
// valid_q alone controls observation. Registered onehot selection bounds fanout.
module ot_hbm_attn_pv_bank_gather_registered(
 input wire clk,rst_n,capture_v,
 input wire[2047:0]tile_data,input wire[63:0]tile_flags,
 input wire[2:0]block_select,
 output reg[255:0]bank_data,output reg[7:0]bank_flags,
 output reg output_v
);
 reg[2047:0]data_q;reg[63:0]flags_q;reg[7:0]select_q;reg valid_q;
 wire[263:0]selection[0:7];wire[263:0]selected;
 genvar k;
 generate for(k=0;k<8;k=k+1)begin:g_select
  always @(posedge clk) select_q[k] <= block_select==3'(k);
  assign selection[k]={264{select_q[k]}} & {flags_q[k*8+:8],data_q[k*256+:256]};
 end endgenerate
 assign selected=selection[0]|selection[1]|selection[2]|selection[3]|selection[4]|selection[5]|selection[6]|selection[7];
 always @(posedge clk)begin
  data_q<=tile_data;flags_q<=tile_flags;
  if(valid_q)begin bank_data<=selected[255:0];bank_flags<=selected[263:256];end
 end
 always @(posedge clk or negedge rst_n)if(!rst_n)begin valid_q<=0;output_v<=0;end
 else begin valid_q<=capture_v;output_v<=valid_q;end
endmodule
`default_nettype wire
