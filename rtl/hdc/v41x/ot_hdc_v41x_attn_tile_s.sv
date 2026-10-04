`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// W11 streaming-domain (1.2 GHz at SS) attention TILE, physical successor of ot_hdc_v41x_attn_tile_l
// (rtl/hdc/v41x/ot_hdc_v41x_attn_tile_lat.sv): the same function and the same cycles (output for output, every
// cycle), organised as H/HG identical HEAD GROUPS so the tile hardens hierarchically.
//
// tile_l shares one input register, one dequantiser and one set of skew delay lines between all H heads: at
// H = 16 the skewed operand bus (TD x 18 bits) and the stationary-load decode fan out across ~0.9 mm of head
// datapaths, beyond the SS wire reach of one 0.833 ns cycle (~0.5 mm).  Here every head group carries its own copy
// of that front end (R0 boundary registers, dequantiser, D1 register, skew lines -- registers only, no added
// cycle), so the tile is H/HG copies of one hardened element (ot_hdc_v41x_attn_hgrp_s) and the tile level is wiring:
// each input port fans out to the H/HG group R0 registers, each output is a group register.  The group's head
// index base is the input port gid (tied off by the tile), so all groups are one macro.
//
// The stationary-load write enables are decoded from the R0 registers as in tile_l; the products, chunk chains
// and trees are ot_hdc_v41x_attn_hdp_l unchanged.  Exactness: lockstep against tile_l (tools/hbm_fmax_attn_gate.py
// tile), and the engine ot_hdc_v41x_attn_s with TILE_S = 1 on the full-geometry golden vectors.
// ---------------------------------------------------------------------------
module ot_hdc_v41x_attn_hgrp_s #(
    parameter integer H = 16,          // heads of the tile
    parameter integer HG = 4,          // heads of this group
    parameter integer TD = 64,
    parameter integer NBANK = 3,
    parameter integer BW = 2,
    parameter integer PWORDS = 1,
    parameter integer FPL = 3,
    parameter integer FML = 3
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [7:0]        gid,       // group index (static): heads gid*HG .. gid*HG+HG-1
    input  wire              ld_v,
    input  wire              ld_mode,
    input  wire [BW-1:0]     ld_bank,
    input  wire [7:0]        ld_grp,
    input  wire [PWORDS*TD*16-1:0] ld_w,
    input  wire              ld_w2v,
    input  wire              iv,
    input  wire [BW-1:0]     ibank,
    input  wire [TD*18-1:0]  ib,
    output reg               ov,
    output reg  [HG*32-1:0]  oy,
    output reg  [HG-1:0]     oflt
);
    localparam integer NC = TD / 8;
    localparam integer LV = $clog2(NC);
    localparam integer R = TD / H;
    localparam integer LAT_CORE = FML + 7 * FPL + FPL * LV;

    // -- R0: boundary registers (this group's copy)
    reg              r_ld_v, r_ld_mode;
    reg [BW-1:0]     r_ld_bank;
    reg [7:0]        r_ld_grp;
    reg [PWORDS*TD*16-1:0] r_ld_w;
    reg              r_ld_w2v;
    reg              r_iv;
    reg [BW-1:0]     r_ibank;
    reg [TD*18-1:0]  r_ib;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin r_ld_v <= 1'b0; r_iv <= 1'b0; end
        else begin r_ld_v <= ld_v; r_iv <= iv; end
    end
    always @(posedge clk) begin
        r_ld_mode <= ld_mode; r_ld_bank <= ld_bank; r_ld_grp <= ld_grp; r_ld_w <= ld_w; r_ld_w2v <= ld_w2v;
        r_ibank <= ibank; r_ib <= ib;
    end

    genvar gh, gk;
    // -- D1: dequantise
    reg [TD*18-1:0] d1_b;
    reg [BW-1:0]    d1_bank;
    reg             d1_v;
    generate
        for (gk = 0; gk < TD; gk = gk + 1) begin : g_dq
            wire [15:0] y;
            wire f;
            ot_hdc_v41x_attn_deq u_dq (.e(r_ib[gk*18 +: 18]), .y(y), .flt(f));
            always @(posedge clk) d1_b[gk*18 +: 18] <= {r_ib[gk*18 + 17], f, y};
        end
    endgenerate
    always @(posedge clk) d1_bank <= r_ibank;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) d1_v <= 1'b0;
        else d1_v <= r_iv;
    end

    // -- skew: chunk position i issues FPL*(i-1) cycles after position 0
    wire [TD*18-1:0] sk_b;
    wire [8*BW-1:0]  sk_bank;
    generate
        for (gk = 0; gk < 8; gk = gk + 1) begin : g_skb
            localparam integer DS = (gk == 0) ? 0 : FPL * (gk - 1);
            ot_hdc_v41x_dly #(.W(BW), .D(DS)) u_d (.clk(clk), .d(d1_bank), .q(sk_bank[gk*BW +: BW]));
        end
        for (gk = 0; gk < TD; gk = gk + 1) begin : g_ske
            localparam integer DS = ((gk % 8) == 0) ? 0 : FPL * ((gk % 8) - 1);
            ot_hdc_v41x_dly #(.W(18), .D(DS)) u_d (.clk(clk), .d(d1_b[gk*18 +: 18]), .q(sk_b[gk*18 +: 18]));
        end
    endgenerate

    // -- per head of the group (tile head index hh = gid*HG + gh)
    generate
        for (gh = 0; gh < HG; gh = gh + 1) begin : g_h
            wire [7:0] hh = gid * HG + gh;
            // this head's columns of a p-mode word: word j*H + hh, j = 0 .. R-1 (gid selects them)
            wire [R*16-1:0] pcol, pcol2;
            genvar gj;
            for (gj = 0; gj < R; gj = gj + 1) begin : g_pc
                assign pcol[gj*16 +: 16] = r_ld_w[(gj * H + hh) * 16 +: 16];
                if (PWORDS > 1) begin : g_p2
                    assign pcol2[gj*16 +: 16] = r_ld_w[TD * 16 + (gj * H + hh) * 16 +: 16];
                end else begin : g_p1
                    assign pcol2[gj*16 +: 16] = 16'd0;
                end
            end
            wire [TD-1:0]    we;
            wire [TD*16-1:0] wd;
            for (gk = 0; gk < TD; gk = gk + 1) begin : g_w
                if (PWORDS == 1) begin : g_w1
                    assign wd[gk*16 +: 16] = r_ld_mode ? pcol[(gk % R) * 16 +: 16] : r_ld_w[gk * 16 +: 16];
                    assign we[gk] = r_ld_v && (r_ld_mode ? (r_ld_grp == (gk / R)) : (r_ld_grp == hh));
                end else begin : g_w2
                    wire lo = (r_ld_grp == (gk / R));
                    wire hi = r_ld_w2v && ((r_ld_grp + 8'd1) == (gk / R));
                    assign wd[gk*16 +: 16] = !r_ld_mode ? r_ld_w[gk * 16 +: 16] :
                                             hi ? pcol2[(gk % R) * 16 +: 16] : pcol[(gk % R) * 16 +: 16];
                    assign we[gk] = r_ld_v && (r_ld_mode ? (lo || hi) : (r_ld_grp == hh));
                end
            end
            wire [31:0] y;
            wire f;
            ot_hdc_v41x_attn_hdp_l #(.TD(TD), .NBANK(NBANK), .BW(BW), .FPL(FPL), .FML(FML)) u_hdp (
                .clk(clk), .rst_n(rst_n), .we(we), .wbank(r_ld_bank), .wd(wd), .sk_bank(sk_bank), .sk_b(sk_b),
                .y(y), .f(f));
            always @(posedge clk) begin
                oy[gh*32 +: 32] <= y;
                oflt[gh] <= f;
            end
        end
    endgenerate

    wire v_core;
    ot_hdc_v41x_vdly #(.D(LAT_CORE)) u_v (.clk(clk), .rst_n(rst_n), .d(d1_v), .q(v_core));
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) ov <= 1'b0;
        else ov <= v_core;
    end
endmodule

// The tile: H/HG head groups; the same ports and cycles as ot_hdc_v41x_attn_tile_l.
module ot_hdc_v41x_attn_tile_s #(
    parameter integer H = 16,
    parameter integer TD = 64,
    parameter integer NBANK = 3,
    parameter integer BW = 2,
    parameter integer PWORDS = 1,
    parameter integer FPL = 3,
    parameter integer FML = 3,
    parameter integer HG = 4           // heads per hardened group (H % HG == 0)
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              ld_v,
    input  wire              ld_mode,
    input  wire [BW-1:0]     ld_bank,
    input  wire [7:0]        ld_grp,
    input  wire [PWORDS*TD*16-1:0] ld_w,
    input  wire              ld_w2v,
    input  wire              iv,
    input  wire [BW-1:0]     ibank,
    input  wire [TD*18-1:0]  ib,
    output wire              ov,
    output wire [H*32-1:0]   oy,
    output wire [H-1:0]      oflt
);
    localparam integer NG = H / HG;
    wire [NG-1:0] gov;
    genvar g;
    generate
        if (H % HG != 0) begin : g_bad
            initial $error("ot_hdc_v41x_attn_tile_s: H must be a multiple of HG");
        end
        for (g = 0; g < NG; g = g + 1) begin : g_g
            ot_hdc_v41x_attn_hgrp_s #(.H(H), .HG(HG), .TD(TD), .NBANK(NBANK), .BW(BW), .PWORDS(PWORDS), .FPL(FPL),
                                      .FML(FML)) u_g (
                .clk(clk), .rst_n(rst_n), .gid(g[7:0]), .ld_v(ld_v), .ld_mode(ld_mode), .ld_bank(ld_bank),
                .ld_grp(ld_grp), .ld_w(ld_w), .ld_w2v(ld_w2v), .iv(iv), .ibank(ibank), .ib(ib), .ov(gov[g]),
                .oy(oy[g*HG*32 +: HG*32]), .oflt(oflt[g*HG +: HG]));
        end
    endgenerate
    assign ov = gov[0];
endmodule
