`timescale 1ns/1ps
// Exact existing regional wrapper; actual selected5de leaf bodies, no old view binding.
module tb_selected_tail_station #(
    parameter integer MUT = 0,
    parameter integer PIN_IN = 1,
    parameter integer BT_LAT = PIN_IN
) (
    input  wire [7:0]      ck_r,
    input  wire [7:0]      rst_n_r,
    input  wire [8*29-1:0] cfg_r,          // per region {v, mode[1:0], wsrc, nwords[7:0], sbase[8:0], kcm1[7:0]}
    input  wire [511:0]    rs_s_lo, rs_s_hi, rs_n_lo, rs_n_hi,
    input  wire [8*4-1:0]  rs_s_c, rs_n_c,
    input  wire [511:0]    nb_d,
    input  wire [8*2-1:0]  nb_c,
    output wire [511:0]    nb_od,
    output wire [1:0]      nb_oc,
    output wire            bt_re,
    output wire [8:0]      bt_word,
    input  wire [255:0]    bt_q,
    output wire            r_v,
    output wire [7:0]      r_idx,
    output wire            r_last,
    output wire [511:0]    r_d,
    output wire            fault
);
    // Folded ring order 0,2,4,6,7,5,3,1 (physical neighbours); UP[r] = region whose writer region r reads.
    function automatic integer up_of(input integer r);
        case (r) 0: up_of = 2; 2: up_of = 4; 4: up_of = 6; 6: up_of = 7; 7: up_of = 5; 5: up_of = 3; 3: up_of = 1; default: up_of = 0; endcase
    endfunction
    wire [3:0] fb [0:7]; wire [3:0] fv [0:7];
    wire [1:0] oc [0:7]; wire bre [0:7]; wire [8:0] bw [0:7]; wire rv [0:7]; wire [7:0] ri [0:7]; wire rl [0:7]; wire fl [0:7];
    for (genvar r = 0; r < 8; r = r + 1) begin : g_r
        localparam integer U = up_of(r);
        wire [28:0] c = cfg_r[29*r +: 29];
        (* keep_hierarchy = "yes" *) qfd_dv_s8_station_tail1 #(.MUT(MUT),.PIN_IN(PIN_IN),.BT_LAT(BT_LAT)) u_rg (.ck(ck_r[r]), .rst_n(rst_n_r[r]),
            .cfg_v_p(c[28]), .cfg_mode_p(c[27:26]), .cfg_wsrc_p(c[25]), .cfg_nwords_p(c[24:17]), .cfg_sbase_p(c[16:8]), .cfg_kcm1_p(c[7:0]),
            .rs_s_lo_p(rs_s_lo[64*r +: 64]), .rs_s_hi_p(rs_s_hi[64*r +: 64]), .rs_n_lo_p(rs_n_lo[64*r +: 64]), .rs_n_hi_p(rs_n_hi[64*r +: 64]),
            .rs_s_c_p(rs_s_c[4*r +: 4]), .rs_n_c_p(rs_n_c[4*r +: 4]), .nb_d_p(nb_d[64*r +: 64]), .nb_c_p(nb_c[2*r +: 2]),
            .nb_od(nb_od[64*r +: 64]), .nb_oc(oc[r]), .bt_re(bre[r]), .bt_word(bw[r]), .bt_q_p(bt_q[32*r +: 32]),
            .r_v(rv[r]), .r_idx(ri[r]), .r_last(rl[r]), .r_d(r_d[64*r +: 64]),
            .flt_bank_i(fb[U]), .flt_vld_i(fv[U]), .flt_bank_o(fb[r]), .flt_vld_o(fv[r]), .fault(fl[r]));
    end
    assign nb_oc = oc[0]; assign bt_re = bre[0]; assign bt_word = bw[0];
    assign r_v = rv[0]; assign r_idx = ri[0]; assign r_last = rl[0]; assign fault = fl[0];
endmodule
