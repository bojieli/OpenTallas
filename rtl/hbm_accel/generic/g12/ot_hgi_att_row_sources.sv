`timescale 1ns/1ps
// HGI-1 G12: ordered row references only. Existing gather readers/ATT arithmetic
// retain byte layout and chunk/tree order. No KV payload buffering or arithmetic.
module ot_hgi_att_row_sources #(
    parameter integer ENABLE_G12=0,
    parameter integer MUT_RING_ZERO=0,
    parameter integer MUT_DROP_C=0,
    parameter integer MUT_C_REVERSE=0,
    parameter integer MUT_C_ORDER=0
)(
    input wire clk, rst_n,
    input wire cmd_v, output wire cmd_r,
    input wire ring,
    input wire [20:0] pos1, b_n, b_m, c_n,
    input wire c_id_v, output wire c_id_r, input wire [31:0] c_id,
    input wire legacy_v, output wire legacy_r,
    input wire legacy_source, legacy_last,
    input wire [19:0] legacy_row,
    input wire [20:0] legacy_ordinal,
    output wire row_v, input wire row_r,
    output wire row_source, row_last,
    output wire [19:0] row_index,
    output wire [20:0] row_ordinal,
    output wire busy, done, fault
);
    generate if (!ENABLE_G12) begin : g_legacy
        assign cmd_r=1'b0;
        assign c_id_r=1'b0;
        assign legacy_r=row_r;
        assign row_v=legacy_v;
        assign row_source=legacy_source;
        assign row_last=legacy_last;
        assign row_index=legacy_row;
        assign row_ordinal=legacy_ordinal;
        assign busy=legacy_v;
        assign done=legacy_v && row_r && legacy_last;
        assign fault=1'b0;
    end else begin : g_g12
        reg active, valid_q, source_q, last_q, done_q, fault_q;
        reg [20:0] b_left, c_left;
        reg [19:0] next_b, mask_q, index_q;
        reg [20:0] ordinal, ordinal_q;
        wire room=!valid_q || row_r;
        wire c_phase=(b_left==0) && (c_left!=0);
        wire bad_count=(pos1>21'h100000) || (b_n>21'h100000) || (c_n>21'h100000);
        wire bad_ring=ring && ((b_m==0) || (b_m>21'h100000) || ((b_m & (b_m-1'b1))!=0) || (b_n>b_m) || (b_n>pos1));
        assign cmd_r=!active && !valid_q;
        assign c_id_r=active && c_phase && room;
        assign legacy_r=1'b0;
        assign row_v=valid_q;
        assign row_source=source_q;
        assign row_last=last_q;
        assign row_index=index_q;
        assign row_ordinal=ordinal_q;
        assign busy=active || valid_q;
        assign done=done_q;
        assign fault=fault_q;
        always @(posedge clk) begin
            if (!rst_n) begin
                active<=0; valid_q<=0; source_q<=0; last_q<=0;
                done_q<=0; fault_q<=0; b_left<=0; c_left<=0;
                next_b<=0; mask_q<=0; index_q<=0; ordinal<=0; ordinal_q<=0;
            end else begin
                done_q<=0; fault_q<=0;
                if (valid_q && row_r) begin
                    valid_q<=0;
                    if (last_q) begin active<=0; done_q<=1; end
                end
                if (cmd_v && cmd_r) begin
                    if (bad_ring || bad_count) begin fault_q<=1; done_q<=1; end
                    else if ((b_n==0) && ((c_n==0) || MUT_DROP_C)) done_q<=1;
                    else begin
                        active<=1; b_left<=b_n;
                        c_left<=MUT_DROP_C ? 21'b0 : c_n;
                        next_b<=ring ? (MUT_RING_ZERO ? 20'b0 : ((pos1-b_n)&(b_m-1'b1))) : 20'b0;
                        mask_q<=ring ? (b_m-1'b1) : 20'hfffff;
                        ordinal<=0;
                    end
                end else if (active && room) begin
                    if (b_left!=0) begin
                        valid_q<=1; source_q<=0; index_q<=next_b;
                        ordinal_q<=ordinal; last_q<=(b_left==1 && c_left==0);
                        next_b<=(next_b+1'b1)&mask_q;
                        b_left<=b_left-1'b1; ordinal<=ordinal+1'b1;
                    end else if (c_left!=0 && c_id_v) begin
                        if (c_id[31:20]!=0) begin
                            active<=0; valid_q<=0; fault_q<=1; done_q<=1;
                        end else begin
                            valid_q<=1; source_q<=1;
                            index_q<=MUT_C_REVERSE ? ~c_id[19:0] : c_id[19:0];
                            ordinal_q<=MUT_C_ORDER ? (ordinal^21'b1) : ordinal; last_q<=(c_left==1);
                            c_left<=c_left-1'b1; ordinal<=ordinal+1'b1;
                        end
                    end
                end
            end
        end
    end endgenerate
endmodule
