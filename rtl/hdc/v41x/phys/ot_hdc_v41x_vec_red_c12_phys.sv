`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// PHYSICAL VEHICLES (HBM SU 1.2 GHz): the hardened pieces of the N = 1,024 stream-unit reducer
// (rtl/hdc/v41x/ot_hdc_v41x_vec_red_c12.sv) at the 1.2 GHz build (MLAT 6 / ALAT 6, RPAD 1, RSL 2, RTAP 1, ROUT 1).
// ot_hdc_v41x_vec_red #(.N(1024), .SL(64)) IS sixteen ot_hdc_v41x_vred_slice and one ot_hdc_v41x_vred_top, so
// these two fixed-parameter tops are the reducer's only distinct pieces:
//   ot_hdc_v41x_vred_slice64_c12  64 lanes: IN, square, padding (+ RPAD register), the 7-add chunk chains of
//                                 8 chunks and tree levels 1..3; every port register-direct (IN registers in,
//                                 the RSL slice-boundary registers out)
//   ot_hdc_v41x_vred_top1024_c12  the tag / valid pipeline, tree levels 4..7 on the slices' registered words,
//                                 the level taps (+ RTAP register), TIME (LV 6) and OUT (+ ROUT register); RSL 2: the slices' words
//                                 are registered again on entry, busy is one register, so every port is
//                                 register-direct (the slice keeps its single RSL register)
// Sources: this file, ot_hdc_v41x_vec_red_c12.sv, ot_hdc_fastfp_lat_c12.sv, ot_hdc_fp32_f12.sv,
// v41x/ot_dsrom_su_add6.sv, ot_hdc_fastfp.sv, ot_hdc_fp32_mul_lat.sv, ot_hdc_fp32_add_lat.sv, ot_hdc_prefix.sv,
// ot_hdc_delay.sv, ot_hdc_sfu.sv (ot_hdc_vline).
// ---------------------------------------------------------------------------
module ot_hdc_v41x_vred_slice64_c12 (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          v_in,
    input  wire [2047:0] x_in,
    input  wire [63:0]   live_in,
    input  wire          mx_in,
    input  wire          sq_in,
    output wire [479:0]  lv_o,
    output wire          fault_o
);
    ot_hdc_v41x_vred_slice #(.SL(64), .MLAT(6), .ALAT(6), .RPAD(1), .RSL(1)) u (.*);
endmodule

module ot_hdc_v41x_vred_top1024_c12 (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          v_in,
    input  wire          mx_in,
    input  wire [3:0]    lt_in,
    input  wire          span_in,
    input  wire [2:0]    l_in,
    input  wire          last_in,
    input  wire [7:0]    nres_in,
    input  wire          rnd_in,
    input  wire [23:0]   rbase_in,
    input  wire [4:0]    rsh_in,
    input  wire [8:0]    meta_in,
    input  wire [7679:0] lv_in,
    input  wire [15:0]   sfault_in,
    output wire [127:0]  o_we,
    output wire [3071:0] o_addr,
    output wire [4095:0] o_data,
    output wire [8:0]    o_meta,
    output wire          o_ev,
    output wire          busy,
    output wire          fault
);
    ot_hdc_v41x_vred_top #(.N(1024), .LV(6), .AW(24), .MW(9), .MLAT(6), .ALAT(6), .RPAD(1), .RSL(2), .RTAP(1),
                           .ROUT(1), .SL(64)) u (.*);
endmodule

// the same top with one ROUT bundle copy per 2 slot(s) (ROGS 2): the OUT select fanout of each copy is 2/4 of the above
module ot_hdc_v41x_vred_top1024_c12_g2 (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          v_in,
    input  wire          mx_in,
    input  wire [3:0]    lt_in,
    input  wire          span_in,
    input  wire [2:0]    l_in,
    input  wire          last_in,
    input  wire [7:0]    nres_in,
    input  wire          rnd_in,
    input  wire [23:0]   rbase_in,
    input  wire [4:0]    rsh_in,
    input  wire [8:0]    meta_in,
    input  wire [7679:0] lv_in,
    input  wire [15:0]   sfault_in,
    output wire [127:0]  o_we,
    output wire [3071:0] o_addr,
    output wire [4095:0] o_data,
    output wire [8:0]    o_meta,
    output wire          o_ev,
    output wire          busy,
    output wire          fault
);
    ot_hdc_v41x_vred_top #(.N(1024), .LV(6), .AW(24), .MW(9), .MLAT(6), .ALAT(6), .RPAD(1), .RSL(2), .RTAP(1),
                           .ROUT(1), .ROGS(2), .SL(64)) u (.*);
endmodule

// the same top with one ROUT bundle copy per 1 slot(s) (ROGS 1): the OUT select fanout of each copy is 1/4 of the above
module ot_hdc_v41x_vred_top1024_c12_g1 (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          v_in,
    input  wire          mx_in,
    input  wire [3:0]    lt_in,
    input  wire          span_in,
    input  wire [2:0]    l_in,
    input  wire          last_in,
    input  wire [7:0]    nres_in,
    input  wire          rnd_in,
    input  wire [23:0]   rbase_in,
    input  wire [4:0]    rsh_in,
    input  wire [8:0]    meta_in,
    input  wire [7679:0] lv_in,
    input  wire [15:0]   sfault_in,
    output wire [127:0]  o_we,
    output wire [3071:0] o_addr,
    output wire [4095:0] o_data,
    output wire [8:0]    o_meta,
    output wire          o_ev,
    output wire          busy,
    output wire          fault
);
    ot_hdc_v41x_vred_top #(.N(1024), .LV(6), .AW(24), .MW(9), .MLAT(6), .ALAT(6), .RPAD(1), .RSL(2), .RTAP(1),
                           .ROUT(1), .ROGS(1), .SL(64)) u (.*);
endmodule
