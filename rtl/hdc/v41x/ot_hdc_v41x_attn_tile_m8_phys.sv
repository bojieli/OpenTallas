`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Opt-in 1.2 GHz hardening tops of the streaming attention tile (rtl/hdc/v41x/ot_hdc_v41x_attn_tile_s.sv), successor
// of ot_attn_hgrp_m4 / ot_attn_tile_m4 (unchanged; names ot_attn_hgrp_m<FPL>h<HG>).  The routed m4 leaf (4 heads, ~81k um2 of cells) failed two ways
// (results/rtl/hbm_accel_fmax_inventory_20261004/attn/routes/noether_hgrp4b_u35_terminal_20261005):
//   * SS: -172 ps at GRT on the f12 LAT-4 adder's first stage (decode, magnitude compare, alignment sticky, swap)
//     fed straight by the previous chain adder's output register;
//   * routability: 117k detailed-route violations and a crashed DRT after ~4 h.
// Every failing endpoint class of that route (GRT, all 10.6k endpoints grouped) is fixed here:
//   * f12 adder decode/compare/align (-172 ps, 3.4k endpoints), sum+LZC (-64), shift+round (-38): FPL 6 selects the
//     six-cut adder ot_hdc_fp32_add_f12_l6x (DS ROM kit), FPL 7 the seven-cut set 7'b1101111 (+ sum | LZC);
//   * product stage 1 (-119 / -95 ps), product rounding increment (-98), dequantiser (-78 / -72), stationary-load
//     write path (-84, 3.6k endpoints): FML 8 (ot_hdc_v41x_attn_tile_s: deq_b split over a D2 register with the load
//     write registered alike, the seven-stage product ot_hdc_v41x_attn_bmul_s7 with keep-prefix sum/increment);
//   * routability (117k DRT violations on the 4-head element): the hardened element is HG = 2 or 1 heads,
//     replicated H/HG times in the tile.
// Same function as ot_hdc_v41x_attn_tile_l at FPL 6/7, FML 6, two cycles later (lockstep:
// tb_hdc_v41x_attn_tile_s_lockstep -GFPL=6|7 -GFML=8 -GF12=1 -GHG=2|1).  Fixed-parameter wrappers so the macro and its instances share one cell name; used by no
// simulation.
// Sources: this file, ot_hdc_v41x_kreg.sv, ot_hdc_v41x_attn_tile_s.sv, ot_hdc_v41x_attn_tile_lat.sv,
// ot_hdc_v41x_attn_tile.sv, ot_hdc_fastfp.sv, ot_hdc_fp32_add_lat.sv, ot_hdc_prefix.sv, ot_hdc_fp32_f12.sv,
// v41x/ot_dsrom_su_add6.sv.
// ---------------------------------------------------------------------------
module ot_attn_hgrp_m6h2 (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [7:0]    gid,
    input  wire          ld_v,
    input  wire          ld_mode,
    input  wire [2:0]    ld_bank,
    input  wire [7:0]    ld_grp,
    input  wire [1023:0] ld_w,
    input  wire          ld_w2v,
    input  wire          iv,
    input  wire [2:0]    ibank,
    input  wire [575:0]  ib,
    output wire          ov,
    output wire [63:0]   oy,
    output wire [1:0]    oflt
);
    ot_hdc_v41x_attn_hgrp_s #(.H(16), .HG(2), .TD(32), .NBANK(5), .BW(3), .PWORDS(2), .FPL(6), .FML(8), .F12(1)) u (
        .clk(clk), .rst_n(rst_n), .gid(gid), .ld_v(ld_v), .ld_mode(ld_mode), .ld_bank(ld_bank), .ld_grp(ld_grp),
        .ld_w(ld_w), .ld_w2v(ld_w2v), .iv(iv), .ibank(ibank), .ib(ib), .ov(ov), .oy(oy), .oflt(oflt));
endmodule

module ot_attn_hgrp_m6h1 (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [7:0]    gid,
    input  wire          ld_v,
    input  wire          ld_mode,
    input  wire [2:0]    ld_bank,
    input  wire [7:0]    ld_grp,
    input  wire [1023:0] ld_w,
    input  wire          ld_w2v,
    input  wire          iv,
    input  wire [2:0]    ibank,
    input  wire [575:0]  ib,
    output wire          ov,
    output wire [31:0]   oy,
    output wire [0:0]    oflt
);
    ot_hdc_v41x_attn_hgrp_s #(.H(16), .HG(1), .TD(32), .NBANK(5), .BW(3), .PWORDS(2), .FPL(6), .FML(8), .F12(1)) u (
        .clk(clk), .rst_n(rst_n), .gid(gid), .ld_v(ld_v), .ld_mode(ld_mode), .ld_bank(ld_bank), .ld_grp(ld_grp),
        .ld_w(ld_w), .ld_w2v(ld_w2v), .iv(iv), .ibank(ibank), .ib(ib), .ov(ov), .oy(oy), .oflt(oflt));
endmodule

module ot_attn_hgrp_m7h2 (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [7:0]    gid,
    input  wire          ld_v,
    input  wire          ld_mode,
    input  wire [2:0]    ld_bank,
    input  wire [7:0]    ld_grp,
    input  wire [1023:0] ld_w,
    input  wire          ld_w2v,
    input  wire          iv,
    input  wire [2:0]    ibank,
    input  wire [575:0]  ib,
    output wire          ov,
    output wire [63:0]   oy,
    output wire [1:0]    oflt
);
    ot_hdc_v41x_attn_hgrp_s #(.H(16), .HG(2), .TD(32), .NBANK(5), .BW(3), .PWORDS(2), .FPL(7), .FML(8), .F12(1)) u (
        .clk(clk), .rst_n(rst_n), .gid(gid), .ld_v(ld_v), .ld_mode(ld_mode), .ld_bank(ld_bank), .ld_grp(ld_grp),
        .ld_w(ld_w), .ld_w2v(ld_w2v), .iv(iv), .ibank(ibank), .ib(ib), .ov(ov), .oy(oy), .oflt(oflt));
endmodule

module ot_attn_hgrp_m7h1 (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [7:0]    gid,
    input  wire          ld_v,
    input  wire          ld_mode,
    input  wire [2:0]    ld_bank,
    input  wire [7:0]    ld_grp,
    input  wire [1023:0] ld_w,
    input  wire          ld_w2v,
    input  wire          iv,
    input  wire [2:0]    ibank,
    input  wire [575:0]  ib,
    output wire          ov,
    output wire [31:0]   oy,
    output wire [0:0]    oflt
);
    ot_hdc_v41x_attn_hgrp_s #(.H(16), .HG(1), .TD(32), .NBANK(5), .BW(3), .PWORDS(2), .FPL(7), .FML(8), .F12(1)) u (
        .clk(clk), .rst_n(rst_n), .gid(gid), .ld_v(ld_v), .ld_mode(ld_mode), .ld_bank(ld_bank), .ld_grp(ld_grp),
        .ld_w(ld_w), .ld_w2v(ld_w2v), .iv(iv), .ibank(ibank), .ib(ib), .ov(ov), .oy(oy), .oflt(oflt));
endmodule

// The tile: 8 x ot_attn_hgrp_m6h2 (the same ports as ot_hdc_v41x_attn_tile_s at H 16 FPL 6 FML 8 F12 1).
module ot_attn_tile_m6h2 (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          ld_v,
    input  wire          ld_mode,
    input  wire [2:0]    ld_bank,
    input  wire [7:0]    ld_grp,
    input  wire [1023:0] ld_w,
    input  wire          ld_w2v,
    input  wire          iv,
    input  wire [2:0]    ibank,
    input  wire [575:0]  ib,
    output wire          ov,
    output wire [511:0]  oy,
    output wire [15:0]   oflt
);
    wire [7:0] gov;
    genvar g;
    generate
        for (g = 0; g < 8; g = g + 1) begin : g_g
            ot_attn_hgrp_m6h2 u_g (
                .clk(clk), .rst_n(rst_n), .gid(g[7:0]), .ld_v(ld_v), .ld_mode(ld_mode), .ld_bank(ld_bank),
                .ld_grp(ld_grp), .ld_w(ld_w), .ld_w2v(ld_w2v), .iv(iv), .ibank(ibank), .ib(ib), .ov(gov[g]),
                .oy(oy[g*64 +: 64]), .oflt(oflt[g*2 +: 2]));
        end
    endgenerate
    assign ov = gov[0];
endmodule

// The tile: 16 x ot_attn_hgrp_m6h1 (the same ports as ot_hdc_v41x_attn_tile_s at H 16 FPL 6 FML 8 F12 1).
module ot_attn_tile_m6h1 (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          ld_v,
    input  wire          ld_mode,
    input  wire [2:0]    ld_bank,
    input  wire [7:0]    ld_grp,
    input  wire [1023:0] ld_w,
    input  wire          ld_w2v,
    input  wire          iv,
    input  wire [2:0]    ibank,
    input  wire [575:0]  ib,
    output wire          ov,
    output wire [511:0]  oy,
    output wire [15:0]   oflt
);
    wire [15:0] gov;
    genvar g;
    generate
        for (g = 0; g < 16; g = g + 1) begin : g_g
            ot_attn_hgrp_m6h1 u_g (
                .clk(clk), .rst_n(rst_n), .gid(g[7:0]), .ld_v(ld_v), .ld_mode(ld_mode), .ld_bank(ld_bank),
                .ld_grp(ld_grp), .ld_w(ld_w), .ld_w2v(ld_w2v), .iv(iv), .ibank(ibank), .ib(ib), .ov(gov[g]),
                .oy(oy[g*32 +: 32]), .oflt(oflt[g*1 +: 1]));
        end
    endgenerate
    assign ov = gov[0];
endmodule

// The tile: 8 x ot_attn_hgrp_m7h2 (the same ports as ot_hdc_v41x_attn_tile_s at H 16 FPL 7 FML 8 F12 1).
module ot_attn_tile_m7h2 (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          ld_v,
    input  wire          ld_mode,
    input  wire [2:0]    ld_bank,
    input  wire [7:0]    ld_grp,
    input  wire [1023:0] ld_w,
    input  wire          ld_w2v,
    input  wire          iv,
    input  wire [2:0]    ibank,
    input  wire [575:0]  ib,
    output wire          ov,
    output wire [511:0]  oy,
    output wire [15:0]   oflt
);
    wire [7:0] gov;
    genvar g;
    generate
        for (g = 0; g < 8; g = g + 1) begin : g_g
            ot_attn_hgrp_m7h2 u_g (
                .clk(clk), .rst_n(rst_n), .gid(g[7:0]), .ld_v(ld_v), .ld_mode(ld_mode), .ld_bank(ld_bank),
                .ld_grp(ld_grp), .ld_w(ld_w), .ld_w2v(ld_w2v), .iv(iv), .ibank(ibank), .ib(ib), .ov(gov[g]),
                .oy(oy[g*64 +: 64]), .oflt(oflt[g*2 +: 2]));
        end
    endgenerate
    assign ov = gov[0];
endmodule

// The tile: 16 x ot_attn_hgrp_m7h1 (the same ports as ot_hdc_v41x_attn_tile_s at H 16 FPL 7 FML 8 F12 1).
module ot_attn_tile_m7h1 (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          ld_v,
    input  wire          ld_mode,
    input  wire [2:0]    ld_bank,
    input  wire [7:0]    ld_grp,
    input  wire [1023:0] ld_w,
    input  wire          ld_w2v,
    input  wire          iv,
    input  wire [2:0]    ibank,
    input  wire [575:0]  ib,
    output wire          ov,
    output wire [511:0]  oy,
    output wire [15:0]   oflt
);
    wire [15:0] gov;
    genvar g;
    generate
        for (g = 0; g < 16; g = g + 1) begin : g_g
            ot_attn_hgrp_m7h1 u_g (
                .clk(clk), .rst_n(rst_n), .gid(g[7:0]), .ld_v(ld_v), .ld_mode(ld_mode), .ld_bank(ld_bank),
                .ld_grp(ld_grp), .ld_w(ld_w), .ld_w2v(ld_w2v), .iv(iv), .ibank(ibank), .ib(ib), .ov(gov[g]),
                .oy(oy[g*32 +: 32]), .oflt(oflt[g*1 +: 1]));
        end
    endgenerate
    assign ov = gov[0];
endmodule
