`timescale 1ns/1ps
// Shared 32-byte HBM port for the KV fetch/flush sector bridge (A) and the
// vector V-sector writer/RMW engine (B). One request is outstanding, so read
// responses cannot be misrouted and every accepted write precedes the next
// accepted read. The core must drain B before announcing a dependent KV op.
module ot_hdc_qwen_kv_phys_arbiter #(
    parameter integer AW=24, NPC=4, TAGW=16, LBK=4
) (
    input wire clk, rst_n,
    input wire a_req_v, output wire a_req_ready,
    input wire a_req_we, input wire [AW-1:0] a_req_sector,
    input wire [LBK:0] a_req_len, input wire [TAGW-1:0] a_req_tag,
    input wire [255:0] a_req_data,
    output wire [NPC-1:0] a_rsp_v, input wire [NPC-1:0] a_rsp_ready,
    output wire [NPC*TAGW-1:0] a_rsp_tag,
    output wire [NPC*LBK-1:0] a_rsp_beat,
    output wire [NPC*256-1:0] a_rsp_data,
    input wire b_r_v, output wire b_r_ready, input wire [AW-1:0] b_r_sector,
    output wire b_r_resp_v, output wire [255:0] b_r_resp_data,
    input wire b_w_v, output wire b_w_ready, input wire [AW-1:0] b_w_sector,
    input wire [255:0] b_w_data,
    output wire h_req_v, input wire h_req_ready, output wire h_req_we,
    output wire [AW-1:0] h_req_sector, output wire [LBK:0] h_req_len,
    output wire [TAGW-1:0] h_req_tag, output wire [255:0] h_req_data,
    input wire [NPC-1:0] h_rsp_v, output wire [NPC-1:0] h_rsp_ready,
    input wire [NPC*TAGW-1:0] h_rsp_tag,
    input wire [NPC*LBK-1:0] h_rsp_beat,
    input wire [NPC*256-1:0] h_rsp_data,
    output reg fault
);
    localparam [1:0] IDLE=0, REQ=1, RSP=2;
    reg [1:0] state;
    reg owner_b, is_write;
    reg [AW-1:0] sector;
    reg [TAGW-1:0] tag;
    reg [255:0] data;
    integer p;
    reg [255:0] b_selected_data;
    reg b_response;
    always @* begin
        b_selected_data=0; b_response=0;
        for (integer i=0;i<NPC;i=i+1) if (h_rsp_v[i]) begin
            b_selected_data=h_rsp_data[i*256 +: 256];
            b_response=1;
        end
    end
    assign h_req_v = state==REQ;
    assign h_req_we = is_write;
    assign h_req_sector = sector;
    assign h_req_len = 1;
    assign h_req_tag = tag;
    assign h_req_data = data;
    assign a_req_ready = state==REQ && !owner_b && h_req_ready;
    assign b_r_ready = state==REQ && owner_b && !is_write && h_req_ready;
    assign b_w_ready = state==REQ && owner_b && is_write && h_req_ready;
    assign a_rsp_v = (state==RSP && !owner_b) ? h_rsp_v : '0;
    assign a_rsp_tag = h_rsp_tag;
    assign a_rsp_beat = h_rsp_beat;
    assign a_rsp_data = h_rsp_data;
    assign b_r_resp_v = state==RSP && owner_b && b_response;
    assign b_r_resp_data = b_selected_data;
    assign h_rsp_ready = (state==RSP) ? (owner_b ? {NPC{1'b1}} : a_rsp_ready) : '0;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state<=IDLE; owner_b<=0; is_write<=0; sector<=0; tag<=0; data<=0; fault<=0;
        end else case (state)
            IDLE: begin
                if (b_r_v && b_w_v) fault<=1;
                if (b_w_v || b_r_v) begin
                    owner_b<=1; is_write<=b_w_v;
                    sector<=b_w_v ? b_w_sector : b_r_sector;
                    data<=b_w_data; tag<=0; state<=REQ;
                end else if (a_req_v) begin
                    if (a_req_len != 1) fault<=1;
                    owner_b<=0; is_write<=a_req_we; sector<=a_req_sector;
                    data<=a_req_data; tag<=a_req_tag; state<=REQ;
                end
            end
            REQ: if (h_req_ready) state<=is_write ? IDLE : RSP;
            RSP: if (|(h_rsp_v & h_rsp_ready)) begin
                if ((h_rsp_v & (h_rsp_v-1'b1)) != 0) fault<=1;
                state<=IDLE;
            end
            default: state<=IDLE;
        endcase
    end
endmodule
