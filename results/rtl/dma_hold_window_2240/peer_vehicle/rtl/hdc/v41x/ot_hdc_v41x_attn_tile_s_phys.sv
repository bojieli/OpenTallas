`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Hierarchical hardening tops of the streaming attention tile (rtl/hdc/v41x/ot_hdc_v41x_attn_tile_s.sv) at the
// DS HBM-accelerator verify/physical controller configuration: H16 TD32, PWORDS 2, NBANK 5 (BW 3), FPL 7, FML 6.
//   ot_attn_hgrp_m  the hardened element: one head group (HG 4), routed flat, exported as LEF + SS/FF ETM
//   ot_attn_tile_m  the tile: 4 x ot_attn_hgrp_m (black boxes = the element's abstract) + port fan-out wiring
// Fixed-parameter wrappers so the macro and its instances share one cell name.  Used by no simulation (the
// function is ot_hdc_v41x_attn_tile_s, proven in lockstep against ot_hdc_v41x_attn_tile_l).
// ---------------------------------------------------------------------------
module ot_attn_hgrp_m (
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
    output wire [127:0]  oy,
    output wire [3:0]    oflt
);
    ot_hdc_v41x_attn_hgrp_s #(.H(16), .HG(4), .TD(32), .NBANK(5), .BW(3), .PWORDS(2), .FPL(7), .FML(6)) u (
        .clk(clk), .rst_n(rst_n), .gid(gid), .ld_v(ld_v), .ld_mode(ld_mode), .ld_bank(ld_bank), .ld_grp(ld_grp),
        .ld_w(ld_w), .ld_w2v(ld_w2v), .iv(iv), .ibank(ibank), .ib(ib), .ov(ov), .oy(oy), .oflt(oflt));
endmodule

// The same element with the 1.2 GHz f12 adds (FPL 4: ot_hdc_fp32_add_f12_l4 in the chunk chains and trees).
module ot_attn_hgrp_m4 (
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
    output wire [127:0]  oy,
    output wire [3:0]    oflt
);
    ot_hdc_v41x_attn_hgrp_s #(.H(16), .HG(4), .TD(32), .NBANK(5), .BW(3), .PWORDS(2), .FPL(4), .FML(6), .F12(1)) u (
        .clk(clk), .rst_n(rst_n), .gid(gid), .ld_v(ld_v), .ld_mode(ld_mode), .ld_bank(ld_bank), .ld_grp(ld_grp),
        .ld_w(ld_w), .ld_w2v(ld_w2v), .iv(iv), .ibank(ibank), .ib(ib), .ov(ov), .oy(oy), .oflt(oflt));
endmodule

module ot_attn_tile_m (
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
    wire [3:0] gov;
    genvar g;
    generate
        for (g = 0; g < 4; g = g + 1) begin : g_g
            ot_attn_hgrp_m u_g (
                .clk(clk), .rst_n(rst_n), .gid(g[7:0]), .ld_v(ld_v), .ld_mode(ld_mode), .ld_bank(ld_bank),
                .ld_grp(ld_grp), .ld_w(ld_w), .ld_w2v(ld_w2v), .iv(iv), .ibank(ibank), .ib(ib), .ov(gov[g]),
                .oy(oy[g*128 +: 128]), .oflt(oflt[g*4 +: 4]));
        end
    endgenerate
    assign ov = gov[0];
endmodule
