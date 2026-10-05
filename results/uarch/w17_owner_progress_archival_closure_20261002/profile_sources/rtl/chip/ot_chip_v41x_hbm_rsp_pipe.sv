`timescale 1ns/1ps
// Grouped, elastic K-response return for one V4.1 HBM stack.  Each local
// group takes at most one pseudo-channel beat per cycle into a one-entry
// register; the output drains one group per cycle.  Tags identify beats, so
// inter-channel order is immaterial, while each channel keeps FIFO order.
module ot_chip_v41x_hbm_rsp_pipe #(
    parameter integer NPC = 32,
    parameter integer TAGW = 16,
    parameter integer BEATW = 4,
    parameter integer DW = 256,
    parameter integer NG = (NPC >= 4) ? 4 : NPC
) (
    input  wire clk,
    input  wire rst_n,
    input  wire [NPC-1:0] r_v,
    output wire [NPC-1:0] r_rdy,
    input  wire [NPC*(TAGW+1)-1:0] r_tag,
    input  wire [NPC*BEATW-1:0] r_beat,
    input  wire [NPC*DW-1:0] r_data,
    input  wire [NPC-1:0] b_rsp_rdy,
    output wire k_rsp_v,
    input  wire k_rsp_rdy,
    output wire [TAGW-1:0] k_rsp_tag,
    output wire [BEATW-1:0] k_rsp_beat,
    output wire [DW-1:0] k_rsp_data
);
    localparam integer PPG = (NPC + NG - 1) / NG;
    localparam integer GPW = (NG > 1) ? $clog2(NG) : 1;
    localparam integer LPW = (PPG > 1) ? $clog2(PPG) : 1;
    wire [NG-1:0] gv;
    wire [NG*TAGW-1:0] gt;
    wire [NG*BEATW-1:0] gb;
    wire [NG*DW-1:0] gd;
    reg [GPW-1:0] gnext, gsel;
    reg gany;
    integer j, ix;
    always @(*) begin
        gany = 1'b0;
        gsel = '0;
        for (j = 0; j < NG; j = j + 1) begin
            ix = integer'(gnext) + j;
            if (ix >= NG) ix = ix - NG;
            if (!gany && gv[ix]) begin
                gany = 1'b1;
                gsel = GPW'(ix);
            end
        end
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) gnext <= '0;
        else if (gany && k_rsp_rdy) gnext <= (gsel == GPW'(NG-1)) ? '0 : gsel + 1'b1;
    assign k_rsp_v = gany;
    assign k_rsp_tag = gt[gsel*TAGW +: TAGW];
    assign k_rsp_beat = gb[gsel*BEATW +: BEATW];
    assign k_rsp_data = gd[gsel*DW +: DW];

    genvar g, p;
    generate for (g = 0; g < NG; g = g + 1) begin : g_group
        reg valid;
        reg [TAGW-1:0] tag;
        reg [BEATW-1:0] beat;
        reg [DW-1:0] data;
        reg [LPW-1:0] next_pc, sel_pc;
        reg any;
        integer n, pc;
        wire drain = valid && gany && gsel == g && k_rsp_rdy;
        wire room = !valid || drain;
        always @(*) begin
            any = 1'b0;
            sel_pc = '0;
            for (n = 0; n < PPG; n = n + 1) begin
                pc = integer'(next_pc) + n;
                if (pc >= PPG) pc = pc - PPG;
                if (!any && g*PPG+pc < NPC && r_v[g*PPG+pc] &&
                    r_tag[(g*PPG+pc)*(TAGW+1)+TAGW]) begin
                    any = 1'b1;
                    sel_pc = LPW'(pc);
                end
            end
        end
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin
                valid <= 1'b0;
                next_pc <= '0;
                tag <= '0; beat <= '0; data <= '0;
            end else if (room) begin
                valid <= any;
                if (any) begin
                    tag <= r_tag[(g*PPG+integer'(sel_pc))*(TAGW+1) +: TAGW];
                    beat <= r_beat[(g*PPG+integer'(sel_pc))*BEATW +: BEATW];
                    data <= r_data[(g*PPG+integer'(sel_pc))*DW +: DW];
                    next_pc <= (sel_pc == LPW'(PPG-1)) ? '0 : sel_pc + 1'b1;
                end
            end
        assign gv[g] = valid;
        assign gt[g*TAGW +: TAGW] = tag;
        assign gb[g*BEATW +: BEATW] = beat;
        assign gd[g*DW +: DW] = data;
        for (p = 0; p < PPG; p = p + 1) begin : g_pc
            if (g*PPG+p < NPC) begin : g_live
                wire mine_k = r_tag[(g*PPG+p)*(TAGW+1)+TAGW];
                assign r_rdy[g*PPG+p] = mine_k ?
                    (room && any && sel_pc == p) : b_rsp_rdy[g*PPG+p];
            end
        end
    end endgenerate
endmodule
