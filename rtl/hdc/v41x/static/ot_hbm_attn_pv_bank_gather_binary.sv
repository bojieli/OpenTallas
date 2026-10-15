`timescale 1ns/1ps
`default_nettype none
// Opt-in pin-boundary repair: capture the literal selector at the input face.
// Decode is between the two existing register stages. No cycle is added.
module ot_hbm_attn_pv_bank_gather_binary(
 input wire clk,rst_n,capture_v,
 input wire[2047:0]tile_data,input wire[63:0]tile_flags,
 input wire[2:0]block_select,
 output reg[255:0]bank_data,output reg[7:0]bank_flags,
 output reg output_v
);
 reg[2047:0]data_q;reg[63:0]flags_q;reg[2:0]select_q;reg valid_q;
 always @(posedge clk)begin
  data_q<=tile_data;flags_q<=tile_flags;
`ifdef ATT_GATHER_BINARY_MUTANT
  select_q<=block_select+3'd1;
`else
  select_q<=block_select;
`endif
  if(valid_q)begin
   bank_data<=data_q[select_q*256+:256];
   bank_flags<=flags_q[select_q*8+:8];
  end
 end
 always @(posedge clk or negedge rst_n)if(!rst_n)begin valid_q<=0;output_v<=0;end
 else begin valid_q<=capture_v;output_v<=valid_q;end
endmodule
`default_nettype wire
