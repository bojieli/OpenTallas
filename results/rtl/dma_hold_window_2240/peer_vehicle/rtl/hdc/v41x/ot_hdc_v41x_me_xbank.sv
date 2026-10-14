`timescale 1ns/1ps
// Banked activation store for the V4.1 BF16/FP32 weight tile.  This is a
// standalone macro boundary; the adapter's protocol is unchanged.  Bank b
// holds element indices b + 8*MG*r for each position.  One read per bank and
// position is enough because lanes with the same active segment index
// request the same (q, c) element.  The shallow segment broadcast replaces
// the original KMAX-deep variable-index mux on every MAC lane.
module ot_hdc_v41x_me_xbank #(
    parameter integer MG = 8,
    parameter integer MP = 2,
    parameter integer G = 4,
    parameter integer KMAX = 5120,
    parameter integer NBW = 14,
    parameter integer EW = 13
) (
    input  wire                         clk,
    input  wire                         wr_v,
    input  wire [$clog2(MP+1)-1:0]      wr_p,
    input  wire [EW-1:0]                wr_e,
    input  wire [G*16-1:0]              wr_d,
    // Optional 64-element BF16 ingress from four 512-bit VM banks.  pre_e
    // is a group-relative multiple of LANES; the producer performs BF16 RNE.
    // pre_v and wr_v are mutually exclusive phases.
    input  wire                         pre_v,
    input  wire [$clog2(MP+1)-1:0]      pre_p,
    input  wire [EW-1:0]                pre_e,
    input  wire [8*MG*16-1:0]           pre_d,
    // When the wide input is kept in physical VM-bank order, rotate each
    // logical 16-element quarter on read.  No 2048-bit ingress crossbar.
    input  wire [1:0]                   rd_rot,
    input  wire [7:0]                   rq_v,
    input  wire [8*NBW-1:0]            rq_q,
    input  wire [8*4-1:0]              rq_plg,
    output wire [8*MG*MP*16-1:0]       rd_x
);
    localparam integer LANES = 8*MG;
    localparam integer ROWS = (KMAX+LANES-1)/LANES;
    localparam integer RAW = (ROWS*MP > 1) ? $clog2(ROWS*MP) : 1;
    localparam integer LG = $clog2(LANES);
    wire [LANES*MP*16-1:0] bank_q;
    genvar b, p;
    generate for (b=0; b<LANES; b=b+1) begin : g_bank
        reg [15:0] mem [0:MP*ROWS-1];
        reg [15:0] q [0:MP-1];
        reg wr_hit;
        reg [RAW-1:0] wr_row;
        reg [15:0] wr_data;
        integer w;
        always @* begin
            wr_hit=1'b0; wr_row='0; wr_data='0;
            for (w=0; w<G; w=w+1)
                if (wr_e+w < KMAX && ((wr_e+w)%LANES)==b) begin
                    wr_hit=1'b1;
                    wr_row=(wr_e+w)/LANES;
                    wr_data=wr_d[w*16 +:16];
                end
        end
        wire [3:0] plg = rq_plg[(b%8)*4 +: 4];
        wire [NBW-1:0] beat = rq_q[(b%8)*NBW +: NBW];
        wire [LG-1:0] logical_b = ((((b/16) - rd_rot) & 3) << 4) | (b%16);
        wire [EW+4:0] term = ({{(EW+5-NBW){1'b0}},beat} << (3+plg)) +
                             (logical_b & ((8 << plg)-1));
        wire [RAW-1:0] r = term >> LG;
        wire active = (logical_b >> (3+plg)) == (beat & ((MG >> plg)-1));
        for (p=0; p<MP; p=p+1) begin : g_pos
            always @(posedge clk) begin
                if (pre_v && pre_p == p && pre_e < KMAX)
                    mem[p*ROWS + (pre_e >> LG)] <= pre_d[b*16 +:16];
                else if (wr_v && wr_p == p && wr_hit)
                    mem[p*ROWS + wr_row] <= wr_data;
                if (rq_v[b%8] && active && r < ROWS)
                    q[p] <= mem[p*ROWS+r];
            end
            assign bank_q[(b*MP+p)*16 +: 16] = q[p];
        end
    end endgenerate
    generate for (b=0; b<LANES; b=b+1) begin : g_broadcast
        wire [3:0] plg = rq_plg[(b%8)*4 +: 4];
        wire [NBW-1:0] beat = rq_q[(b%8)*NBW +: NBW];
        wire [LG-1:0] logical_src = ((beat << (3+plg)) + (b & ((8 << plg)-1))) & (LANES-1);
        wire [LG-1:0] src = ((((logical_src >> 4) + rd_rot) & 3) << 4) | (logical_src & 15);
        reg [LG-1:0] src_q;
        always @(posedge clk) src_q <= src;
        for (p=0; p<MP; p=p+1) begin : g_pos
            assign rd_x[(b*MP+p)*16 +:16] = bank_q[(src_q*MP+p)*16 +:16];
        end
    end endgenerate
endmodule
