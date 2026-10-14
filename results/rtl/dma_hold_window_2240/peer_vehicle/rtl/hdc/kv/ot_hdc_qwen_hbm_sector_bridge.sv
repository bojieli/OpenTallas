`timescale 1ns/1ps
// Correctness-first 16-byte logical FP8 word to 32-byte physical HBM sector
// bridge. One logical request is outstanding. Each physical sector is fetched
// once, then its requested low/high halves are returned in logical beat order.
// A logical half-word write explicitly reads, merges and writes its sector.
// This conservative scheduler preserves read-after-write order; throughput is
// deliberately below the multi-channel target until the production scheduler
// and its bounded reorder buffer are integrated.
module ot_hdc_qwen_hbm_sector_bridge #(
    parameter integer AW = 24,
    parameter integer NPC = 4,
    parameter integer TAGW = 16,
    parameter integer LBK = 3
) (
    input  wire clk, rst_n,
    input  wire log_req_v,
    output wire log_req_ready,
    input  wire log_req_we,
    input  wire [AW-1:0] log_req_addr,
    input  wire [LBK:0] log_req_len,
    input  wire [TAGW-1:0] log_req_tag,
    input  wire [127:0] log_req_data,
    output wire [NPC-1:0] log_rsp_v,
    input  wire [NPC-1:0] log_rsp_ready,
    output wire [NPC*TAGW-1:0] log_rsp_tag,
    output wire [NPC*LBK-1:0] log_rsp_beat,
    output wire [NPC*128-1:0] log_rsp_data,
    output wire phys_req_v,
    input  wire phys_req_ready,
    output wire phys_req_we,
    output wire [AW-1:0] phys_req_sector,
    output wire [LBK:0] phys_req_len,
    output wire [TAGW-1:0] phys_req_tag,
    output wire [255:0] phys_req_data,
    input  wire [NPC-1:0] phys_rsp_v,
    output wire [NPC-1:0] phys_rsp_ready,
    input  wire [NPC*TAGW-1:0] phys_rsp_tag,
    input  wire [NPC*LBK-1:0] phys_rsp_beat,
    input  wire [NPC*256-1:0] phys_rsp_data,
    output reg fault
);
    localparam [2:0] IDLE=0, READ_REQ=1, READ_WAIT=2, SEND=3, WRITE_REQ=4;
    reg [2:0] state;
    reg write_op;
    reg [AW-1:0] addr;
    reg [LBK:0] remaining;
    reg [LBK-1:0] beat;
    reg [TAGW-1:0] tag;
    reg [127:0] write_data;
    reg [255:0] sector_data;
    wire [NPC-1:0] accepted_rsp = phys_rsp_v & phys_rsp_ready;
    integer p;
    reg [255:0] selected_data;
    reg any_rsp;
    always @* begin
        selected_data=0; any_rsp=0;
        for (integer j=0;j<NPC;j=j+1) if (accepted_rsp[j]) begin
            selected_data=phys_rsp_data[j*256 +: 256];
            any_rsp=1'b1;
        end
    end
    assign log_req_ready = state == IDLE;
    assign log_rsp_v = {{(NPC-1){1'b0}}, (state == SEND)};
    assign log_rsp_tag = {{((NPC-1)*TAGW){1'b0}}, tag};
    assign log_rsp_beat = {{((NPC-1)*LBK){1'b0}}, beat};
    assign log_rsp_data = {{((NPC-1)*128){1'b0}}, sector_data[addr[0]*128 +: 128]};
    assign phys_req_v = state == READ_REQ || state == WRITE_REQ;
    assign phys_req_we = state == WRITE_REQ;
    assign phys_req_sector = addr >> 1;
    assign phys_req_len = 1;
    assign phys_req_tag = 0;
    assign phys_req_data = sector_data;
    assign phys_rsp_ready = {NPC{state == READ_WAIT}};
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE; write_op <= 0; addr <= 0; remaining <= 0;
            beat <= 0; tag <= 0; write_data <= 0; sector_data <= 0; fault <= 0;
        end else case (state)
            IDLE: if (log_req_v) begin
                if (log_req_len == 0 || (log_req_we && log_req_len != 1)) fault <= 1'b1;
                write_op <= log_req_we;
                addr <= log_req_addr;
                remaining <= log_req_len;
                beat <= 0;
                tag <= log_req_tag;
                write_data <= log_req_data;
                state <= READ_REQ;
            end
            READ_REQ: if (phys_req_ready) state <= READ_WAIT;
            READ_WAIT: if (any_rsp) begin
                if ((accepted_rsp & (accepted_rsp-1'b1)) != 0) fault <= 1'b1;
                sector_data <= selected_data;
                if (write_op) begin
                    sector_data[addr[0]*128 +: 128] <= write_data;
                    state <= WRITE_REQ;
                end else state <= SEND;
            end
            SEND: if (log_rsp_ready[0]) begin
                if (remaining == 1) state <= IDLE;
                else begin
                    remaining <= remaining-1'b1;
                    beat <= beat+1'b1;
                    addr <= addr+1'b1;
                    if (addr[0]) state <= READ_REQ;
                end
            end
            WRITE_REQ: if (phys_req_ready) state <= IDLE;
            default: state <= IDLE;
        endcase
    end
endmodule
