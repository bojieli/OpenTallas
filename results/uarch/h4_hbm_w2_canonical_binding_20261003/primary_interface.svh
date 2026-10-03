`timescale 1ps/1ps
// WIP actual primary enrollment. No runtime/build/bridge admission.
// All current-word status is wired from the actual frozen sealed decoders.
module ot_w2_nc6_protected_completion #(
 parameter integer OPT_EXACT=0, NC=6, MAX_OUT=16, AW=34,
 parameter integer CTAGW=32, GENW=4, SIDW=3, PTAGW=35,
 parameter logic [6:0] PC_ID=0
)(
 input wire clk,rst_n,admission_stop,rearm_v,provider_fenced,reset_fenced,
 output wire rearm_rdy,idle,
 input wire [NC-1:0] c_req_v,c_req_we,
 output reg [NC-1:0] c_req_rdy,
 input wire [NC*AW-1:0] c_req_addr,
 input wire [NC*CTAGW-1:0] c_req_tag,
 input wire [NC*GENW-1:0] c_req_gen,
 input wire [NC*256-1:0] c_req_data,
 output reg [NC-1:0] c_rsp_v,c_wr_done_v,
 input wire [NC-1:0] c_rsp_rdy,c_wr_done_rdy,
 output reg [NC*CTAGW-1:0] c_rsp_tag,c_wr_done_tag,
 output reg [NC*GENW-1:0] c_rsp_gen,c_wr_done_gen,
 output reg [NC*256-1:0] c_rsp_data,
 output reg p_req_v,p_req_we,
 input wire p_req_rdy,
 output reg [AW-1:0] p_req_addr,
 output reg [PTAGW-1:0] p_req_tag,
 output reg [GENW-1:0] p_req_gen,
 output reg [255:0] p_req_data,
 input wire p_rsp_v,p_wr_done_v,
 output reg p_rsp_rdy,p_wr_done_ready,
 input wire [PTAGW-1:0] p_rsp_tag,p_wr_done_tag,
 input wire [GENW-1:0] p_rsp_gen,p_wr_done_gen,
 input wire [255:0] p_rsp_data,
 output wire fault,repair_busy,
 input wire reverse_fenced
);
