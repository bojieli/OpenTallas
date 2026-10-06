// Blackbox of the hardened quad (rtl/hdc/v41x/ot_hdc_v41x_attn_tile_m6h1r.sv ot_attn_tile_m6h1q) for the H16 parent
// route; its views: physical/hbm_attn_tile_r/quad/ot_attn_tile_m6h1q.
(* blackbox *)
module ot_attn_tile_m6h1q (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [7:0]    qgid,
    input  wire          ld_v,
    input  wire          ld_mode,
    input  wire [2:0]    ld_bank,
    input  wire [7:0]    ld_grp,
    input  wire [1023:0] ld_w,
    input  wire          ld_w2v,
    input  wire          iv,
    input  wire [2:0]    ibank,
    input  wire [575:0]  ib,
    output wire [3:0]    gov,
    output wire [127:0]  oy,
    output wire [3:0]    oflt
);
endmodule
