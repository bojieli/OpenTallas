`timescale 1ns/1ps
// HBM3E PHY + controller abstract, controller-side boundary timing only (assumed); functional model: rtl/hdc/kv/ot_hdc_hbm_model.sv (NPC=32)
// Blackbox view for synthesis and place-and-route (the hard macro).
(* blackbox *)
module ot_hbm3e_phy (
    input wire clk,
    input wire rst_n,
    input wire req_v,
    output wire req_rdy,
    input wire req_we,
    input wire [30:0] req_addr,
    input wire [4:0] req_len,
    input wire [15:0] req_tag,
    input wire [255:0] req_wdata,
    output wire [31:0] rsp_v,
    input wire [31:0] rsp_rdy,
    output wire [511:0] rsp_tag,
    output wire [127:0] rsp_beat,
    output wire [8191:0] rsp_data
);
endmodule
