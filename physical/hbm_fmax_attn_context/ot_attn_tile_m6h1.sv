// Exact H16 wrapper from preserved b32d59700; hardened leaf uses its pinned LEF/SS/FF views.
(* blackbox *)
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
endmodule

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
