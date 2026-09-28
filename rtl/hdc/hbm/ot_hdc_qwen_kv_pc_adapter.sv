`timescale 1ns/1ps
// Translate the existing exact 16-byte logical FP8 KV sector bridge onto the
// shared four-stack 32-byte PC fabric. One logical request is outstanding in
// the bridge; the physical address adds the registered (user,layer) KV page.
// The bridge performs half-sector read/modify/write and exact FP8 arithmetic.
// This adapter changes neither byte order nor write ordering, and does not
// turn the bridge into a throughput-grade multi-outstanding scheduler.
module ot_hdc_qwen_kv_pc_adapter #(
    parameter integer PCS=128,
    parameter integer LAW=24,
    parameter integer HAW=32,
    parameter integer TAGW=25,
    parameter integer MTAGW=32
) (
    input wire clk, rst_n,
    input wire page_valid,
    input wire [HAW-1:0] kv_base_sector,
    input wire bridge_req_v,
    output wire bridge_req_rdy,
    input wire bridge_req_we,
    input wire [LAW-1:0] bridge_req_sector,
    input wire [TAGW-1:0] bridge_req_tag,
    input wire [255:0] bridge_req_data,
    output wire [PCS-1:0] bridge_rsp_v,
    input wire [PCS-1:0] bridge_rsp_rdy,
    output wire [PCS*TAGW-1:0] bridge_rsp_tag,
    output wire [PCS*256-1:0] bridge_rsp_data,
    output reg [PCS-1:0] pc_req_v,
    input wire [PCS-1:0] pc_req_rdy,
    output reg [PCS-1:0] pc_req_we,
    output reg [PCS*HAW-1:0] pc_req_addr,
    output reg [PCS*MTAGW-1:0] pc_req_tag,
    output reg [PCS*256-1:0] pc_req_data,
    input wire [PCS-1:0] pc_rsp_v,
    output wire [PCS-1:0] pc_rsp_rdy,
    input wire [PCS*MTAGW-1:0] pc_rsp_tag,
    input wire [PCS*256-1:0] pc_rsp_data,
    output reg fault
);
    localparam integer KV_SECTORS=262144;
    initial if (PCS!=128 || HAW<32 || TAGW<1+8+$clog2(6144)+3 ||
                MTAGW<TAGW+7)
        $fatal(1,"Qwen G6144 KV tag or sector address would truncate");
    wire [HAW-1:0] addr=kv_base_sector+HAW'(bridge_req_sector);
    wire [6:0] pc=addr[6:0];
    wire request_ok=page_valid && bridge_req_sector<KV_SECTORS &&
                    kv_base_sector[6:0]==0;
    assign bridge_req_rdy=request_ok && pc_req_rdy[pc];
    always @(*) begin
        pc_req_v=0; pc_req_we=0; pc_req_addr=0; pc_req_tag=0; pc_req_data=0;
        if (bridge_req_v && request_ok) begin
            pc_req_v[pc]=1;
            pc_req_we[pc]=bridge_req_we;
            pc_req_addr[pc*HAW +: HAW]=addr;
            pc_req_tag[pc*MTAGW +: MTAGW]={7'd0,bridge_req_tag};
            pc_req_data[pc*256 +: 256]=bridge_req_data;
        end
    end
    for (genvar q=0;q<PCS;q=q+1) begin : g_rsp
        assign bridge_rsp_v[q]=pc_rsp_v[q];
        assign bridge_rsp_tag[q*TAGW +: TAGW]=pc_rsp_tag[q*MTAGW +: TAGW];
        assign bridge_rsp_data[q*256 +: 256]=pc_rsp_data[q*256 +: 256];
        assign pc_rsp_rdy[q]=bridge_rsp_rdy[q];
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) fault<=0;
        else if (bridge_req_v && !request_ok) fault<=1;
    end
endmodule
