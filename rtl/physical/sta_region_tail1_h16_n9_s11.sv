// Unused exact-parameter candidate for current J tail1. No extra register or arithmetic edge.
`default_nettype none
module sta_region_tail1_h16_n9_s11 (

    input  wire          ck,
    input  wire          rst_n,
    input  wire          cfg_v_p,
    input  wire [1:0]    cfg_mode_p,
    input  wire          cfg_wsrc_p,
    input  wire [7:0]    cfg_nwords_p,
    input  wire [8:0]    cfg_sbase_p,
    input  wire [7:0]    cfg_kcm1_p,
    input  wire [63:0]   rs_s_lo_p, rs_s_hi_p, rs_n_lo_p, rs_n_hi_p,   // rs_x[64r +: 64], rs_x[514 + 64r +: 64]
    input  wire [3:0]    rs_s_c_p, rs_n_c_p,                       // {rs_x[1027], rs_x[1026], rs_x[513], rs_x[512]}
    input  wire [63:0]   nb_d_p,                                 // nb_i[64r +: 64]
    input  wire [1:0]    nb_c_p,                                 // nb_i[513:512]
    output wire [63:0]   nb_od,
    output wire [1:0]    nb_oc,
    output wire           bt_re,
    output wire  [8:0]    bt_word,
    input  wire [31:0]   bt_q_p,                                 // bt_q[32r +: 32]
    output wire           r_v,
    output wire  [7:0]    r_idx,
    output wire           r_last,
    output wire  [63:0]   r_d,
    input  wire [3:0]    flt_bank_i,                           // landed fault ring: upstream region's writer
    input  wire [3:0]    flt_vld_i,
    output wire [3:0]    flt_bank_o,
    output wire [3:0]    flt_vld_o,
    output wire           fault
);
    qfd_dv_s8_station_tail1 #(
        .ADD_LAT(7),
        .SKEW(14),
        .SCALE_LAT(7),
        .MUT(0),
        .JB(8),
        .PIN_IN(1),
        .BT_LAT(1),
        .SKEW_S(11),
        .SKEW_N(9),
        .HI_PAD(16),
        .NB_IN_PAD(0),
        .RD_PAD(0),
        .NB_PAD(0)
    ) u_body (
        .ck(ck),
        .rst_n(rst_n),
        .cfg_v_p(cfg_v_p),
        .cfg_mode_p(cfg_mode_p),
        .cfg_wsrc_p(cfg_wsrc_p),
        .cfg_nwords_p(cfg_nwords_p),
        .cfg_sbase_p(cfg_sbase_p),
        .cfg_kcm1_p(cfg_kcm1_p),
        .rs_s_lo_p(rs_s_lo_p),
        .rs_s_hi_p(rs_s_hi_p),
        .rs_n_lo_p(rs_n_lo_p),
        .rs_n_hi_p(rs_n_hi_p),
        .rs_s_c_p(rs_s_c_p),
        .rs_n_c_p(rs_n_c_p),
        .nb_d_p(nb_d_p),
        .nb_c_p(nb_c_p),
        .nb_od(nb_od),
        .nb_oc(nb_oc),
        .bt_re(bt_re),
        .bt_word(bt_word),
        .bt_q_p(bt_q_p),
        .r_v(r_v),
        .r_idx(r_idx),
        .r_last(r_last),
        .r_d(r_d),
        .flt_bank_i(flt_bank_i),
        .flt_vld_i(flt_vld_i),
        .flt_bank_o(flt_bank_o),
        .flt_vld_o(flt_vld_o),
        .fault(fault)
    );
endmodule
`default_nettype wire
