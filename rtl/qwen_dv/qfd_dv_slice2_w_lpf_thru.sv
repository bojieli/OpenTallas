`timescale 1ns/1ps

// ---------------------------------------------------------------------------------------------------- qfd_dv_slice2_w_te: E face (master E = the dn face)
module qfd_dv_slice2_w_te (
    input  wire          ck,                       // region membership only (no state),
    input  wire          rst_n,
    input  wire [1087:0] st_dn_o,
    output wire [1087:0] st_wo,
    input  wire [47:0] sc_dn_o,
    output wire [47:0] sc_wo,
    input  wire [1094:0] ch_dn_o,
    output wire arv_wo,
    output wire [31:0] art_wo,
    output wire arm_wo,
    output wire arl_wo,
    output wire [511:0] ard_wo,
    output wire [547:0] dd_wo,
    input  wire [49:0] cc_o,
    output wire ccv_wo,
    output wire ccm_wo,
    output wire [15:0] ccw_wo,
    output wire [31:0] cct_wo
);
    assign st_wo = st_dn_o[1087:0];
    assign sc_wo = sc_dn_o[47:0];
    assign arv_wo = ch_dn_o[1094];
    assign art_wo = ch_dn_o[1093:1062];
    assign arm_wo = ch_dn_o[1061];
    assign arl_wo = ch_dn_o[1060];
    assign ard_wo = ch_dn_o[1059:548];
    assign dd_wo = ch_dn_o[547:0];
    assign ccv_wo = cc_o[49];
    assign ccm_wo = cc_o[48];
    assign ccw_wo = cc_o[47:32];
    assign cct_wo = cc_o[31:0];
endmodule

// ---------------------------------------------------------------------------------------------------- qfd_dv_slice2_w_tes: E face status outputs (own node: they follow the heads fault, the chains do not wait for it)
module qfd_dv_slice2_w_tes (
    input  wire          ck,                       // region membership only (no state),
    input  wire          rst_n,
    input  wire [9:0] ag_dn_o,
    output wire [9:0] ag_wo,
    input  wire [106:0] st,
    output wire [106:0] ss_wo
);
    assign ag_wo = ag_dn_o[9:0];
    assign ss_wo = st[106:0];
endmodule

// ---------------------------------------------------------------------------------------------------- qfd_dv_slice2_w_tw: W face (the up face)
module qfd_dv_slice2_w_tw (
    input  wire          ck,                       // region membership only (no state),
    input  wire          rst_n,
    input  wire [115:0] cmd_o,
    output wire [115:0] cmd_eo,
    input  wire [452:0] hr_o,
    output wire [452:0] hr_eo,
    input  wire [1087:0] st_up_o,
    output wire [1087:0] st_eo,
    input  wire [47:0] sc_up_o,
    output wire [47:0] sc_eo,
    input  wire [1037:0] ch_up_o,
    output wire rv_eo,
    output wire re_eo,
    output wire [2:0] rr_eo,
    output wire rl_eo,
    output wire [511:0] rd_eo,
    output wire [519:0] dr_eo,
    input  wire [513:0] l9_o,
    output wire [513:0] l9_eo
);
    assign cmd_eo = cmd_o[115:0];
    assign hr_eo = hr_o[452:0];
    assign st_eo = st_up_o[1087:0];
    assign sc_eo = sc_up_o[47:0];
    assign rv_eo = ch_up_o[1037];
    assign re_eo = ch_up_o[1036];
    assign rr_eo = ch_up_o[1035:1033];
    assign rl_eo = ch_up_o[1032];
    assign rd_eo = ch_up_o[1031:520];
    assign dr_eo = ch_up_o[519:0];
    assign l9_eo = l9_o[513:0];
endmodule

// ---------------------------------------------------------------------------------------------------- qfd_dv_slice2_w_tnw: N face, W pin group (cw_n0)
module qfd_dv_slice2_w_tnw (
    input  wire          ck,                       // region membership only (no state),
    input  wire          rst_n,
    input  wire [515:0] cw_n0_i,
    output wire [515:0] cw_n0
);
    assign cw_n0 = cw_n0_i[515:0];
endmodule

// ---------------------------------------------------------------------------------------------------- qfd_dv_slice2_w_tnc: N face, centre pin groups (cw_n1, cw_n2)
module qfd_dv_slice2_w_tnc (
    input  wire          ck,                       // region membership only (no state),
    input  wire          rst_n,
    input  wire [515:0] cw_n1_i,
    output wire [515:0] cw_n1,
    input  wire [515:0] cw_n2_i,
    output wire [515:0] cw_n2
);
    assign cw_n1 = cw_n1_i[515:0];
    assign cw_n2 = cw_n2_i[515:0];
endmodule

// ---------------------------------------------------------------------------------------------------- qfd_dv_slice2_w_tne: N face, E pin group (cw_n3)
module qfd_dv_slice2_w_tne (
    input  wire          ck,                       // region membership only (no state),
    input  wire          rst_n,
    input  wire [515:0] cw_n3_i,
    output wire [515:0] cw_n3
);
    assign cw_n3 = cw_n3_i[515:0];
endmodule

// ---------------------------------------------------------------------------------------------------- qfd_dv_slice2_w_tsw: S face, W pin group (cw_s0)
module qfd_dv_slice2_w_tsw (
    input  wire          ck,                       // region membership only (no state),
    input  wire          rst_n,
    input  wire [515:0] cw_s0_i,
    output wire [515:0] cw_s0
);
    assign cw_s0 = cw_s0_i[515:0];
endmodule

// ---------------------------------------------------------------------------------------------------- qfd_dv_slice2_w_tsc: S face, centre pin groups (cw_s1, cw_s2)
module qfd_dv_slice2_w_tsc (
    input  wire          ck,                       // region membership only (no state),
    input  wire          rst_n,
    input  wire [515:0] cw_s1_i,
    output wire [515:0] cw_s1,
    input  wire [515:0] cw_s2_i,
    output wire [515:0] cw_s2
);
    assign cw_s1 = cw_s1_i[515:0];
    assign cw_s2 = cw_s2_i[515:0];
endmodule

// ---------------------------------------------------------------------------------------------------- qfd_dv_slice2_w_tse: S face, E pin group (cw_s3)
module qfd_dv_slice2_w_tse (
    input  wire          ck,                       // region membership only (no state),
    input  wire          rst_n,
    input  wire [515:0] cw_s3_i,
    output wire [515:0] cw_s3
);
    assign cw_s3 = cw_s3_i[515:0];
endmodule
