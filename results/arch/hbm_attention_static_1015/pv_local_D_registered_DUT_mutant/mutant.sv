`timescale 1ns/1ps
`default_nettype none
// Physical successor: pin-local capture of all eight528b source bundles and
// blockselect, followed by registered528b output. Two explicit extra edges.
module ot_hbm_attn_pv_group_gather_registered(
 input wire clk,rst_n,capture_v,
 input wire[4095:0]tile_data,input wire[127:0]tile_flags,
 input wire[2:0]block_select,
 output reg[511:0]bankpair_data,output reg[15:0]bankpair_flags,
 output reg output_v
);
 reg[4095:0]data_q;reg[127:0]flags_q;reg[2:0]select_q;reg valid_q;
 always @(posedge clk)begin
  if(capture_v)begin data_q<=tile_data;flags_q<=tile_flags;select_q<=block_select^3'b001;end
  if(valid_q)begin
   bankpair_data<=data_q[int'(select_q)*512+:512];
   bankpair_flags<=flags_q[int'(select_q)*16+:16];
  end
 end
 always @(posedge clk or negedge rst_n)if(!rst_n)begin valid_q<=0;output_v<=0;end
 else begin valid_q<=capture_v;output_v<=valid_q;end
endmodule
`default_nettype wire
