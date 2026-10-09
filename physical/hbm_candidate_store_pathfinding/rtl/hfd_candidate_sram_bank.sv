`timescale 1ps/1fs
`default_nettype none
module hfd_candidate_sram_bank(
 input wire clk,por_n,req_v,output wire req_r,input wire req_write,
 input wire[6:0] req_address,input wire[511:0] req_data,
 output wire rsp_v,input wire rsp_r,output wire[511:0] rsp_data,
 output wire rsp_write,rsp_ce,rsp_poison,output wire fault
);
 ot_hbm_candidate_sram_bank #(.ENABLE(1)) bank(.*);
endmodule
`default_nettype wire
