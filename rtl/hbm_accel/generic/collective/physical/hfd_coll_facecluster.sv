// Physical extraction of existing five-cycle face registers. Each 512-bit bank owns its hard clock root.
// Core body flops and actual die faces still require independent hardened children before qualification.
// hfd_coll: thin registered die wrapper (tools/hbm_die_wrap.py, CLAUDE HBM-ABSTRACTS spine).
// Die ports exactly as the r16g generator master (tools/hbm_die_views.py ports); default-off: nothing
// instantiates it except the die view route.  [link] 2026-10-10 R25GQ hfd_coll (one regeneration, lead): ot_hfd_coll_r25gq = ot_hgi_coll_ep NPT 9 (one port per hfd_lk_ep on llk_S0..S4, N0..N3: [0] tx_v [545:1] tx_flit [546] rx_credit out, [547] rx_v [1092:548] rx_flit [1093] sw_cr in, [1117:1094] session out, [1118] fault [1119] locked in, [1121:1120] chain fclk), SWCRED 32 (= lk_ep TXQ), RXAW 8 (slice 256-flit SRAM rb), PIPE 1, RGXHW 1, RFMT 0 + ot_hgi_coll_rgx_hbm / ot_hgi_coll_rgx_snk (hgi-1010/c, LQ 32) + LINK_SESSION cfg word 47.  vmw2 up {c_req [8960], c_q [8959:0]}, down {c_gnt [64], c_cr [63:32], c_rsp [31:0]} (hgi_die_dispatch: {c_req, lanes}, {c_gnt, credits, dones}).
module hfd_coll_facecluster (
    input wire face_ck0,
    input wire face_ck1,
    input wire face_ck2,
    input wire face_ck3,
    input wire face_ck4,
    input wire face_ck5,
    input wire face_ck6,
    input wire face_ck7,
    input wire face_ck8,
    input wire face_ck9,
    input wire face_ck10,
    input wire face_ck11,
    input wire face_ck12,
    input wire face_ck13,
    input wire face_ck14,
    input wire face_ck15,
    input wire face_ck16,
    input wire face_ck17,
    input wire face_ck18,
    input wire face_ck19,
    input wire face_ck20,
    input wire face_ck21,
    input wire face_ck22,
    input wire face_ck23,
    input wire face_ck24,
    input wire face_ck25,
    input wire face_ck26,
    input wire face_ck27,
    input wire face_ck28,
    input wire face_ck29,
    input wire face_ck30,
    input wire face_ck31,
    input wire face_ck32,
    input wire face_ck33,
    input wire face_ck34,
    input wire face_ck35,
    input wire face_ck36,
    input wire face_ck37,
    input wire face_ck38,
    input wire face_ck39,
    input wire face_ck40,
    input wire face_ck41,
    input wire face_ck42,
    input wire face_ck43,
    input wire face_ck44,
    input wire face_ck45,
    input wire face_ck46,
    input wire face_ck47,
    input wire face_ck48,
    input wire face_ck49,
    input wire face_ck50,
    input wire face_ck51,
    input wire face_ck52,
    input wire face_ck53,
    input wire face_ck54,
    input wire face_ck55,
    input wire face_ck56,
    input wire face_ck57,
    input wire face_ck58,
    input wire face_ck59,
    input wire face_ck60,
    input wire face_ck61,
    input wire face_ck62,
    input wire face_ck63,
    input wire face_ck64,
    input wire face_ck65,
    input wire face_ck66,
    input wire face_ck67,
    input wire face_ck68,
    input wire face_ck69,
    input wire face_ck70,
    input wire face_ck71,
    input wire face_ck72,
    input wire face_ck73,
    input wire face_ck74,
    input wire face_ck75,
    input wire face_ck76,
    input wire face_ck77,
    input wire face_ck78,
    input wire face_ck79,
    input wire face_ck80,
    input wire face_ck81,
    input wire face_ck82,
    input wire face_ck83,
    input wire face_ck84,
    input wire face_ck85,
    input wire face_ck86,
    input wire face_ck87,
    input wire face_ck88,
    input wire face_ck89,
    input wire face_ck90,
    input wire face_ck91,
    input wire face_ck92,
    input wire face_ck93,
    input wire face_ck94,
    input wire face_ck95,
    input wire face_ck96,
    input wire face_ck97,
    input wire face_ck98,
    input wire face_ck99,
    input wire face_ck100,
    input wire face_ck101,
    input wire face_ck102,
    input wire face_ck103,
    input wire face_ck104,
    input wire face_ck105,
    input wire face_ck106,
    input wire face_ck107,
    input wire face_ck108,
    input wire face_ck109,
    input wire face_ck110,
    input wire face_ck111,
    input wire face_ck112,
    input wire face_ck113,
    input wire face_ck114,
    input wire face_ck115,
    input wire face_ck116,
    input wire face_ck117,
    input wire face_ck118,
    input wire[15:0]reduce_ck,
    input wire column_ck0,column_ck1,column_ck2,column_ck3,column_ck4,column_ck5,column_ck6,column_ck7,
    input wire port_ck0,port_ck1,port_ck2,port_ck3,port_ck4,port_ck5,port_ck6,port_ck7,port_ck8,
    input wire park_ck0,park_ck1,park_ck2,park_ck3,park_fault_ck,
    input wire body_ck0,
    input wire body_ck1,
    input wire body_ck2,
    input wire body_ck3,
    input wire monitor_clk,
    input wire reset_clk,
    input wire [24:0] f_cmdproc,
    input wire [39:0] f_hgi_cfg,
    input wire [967:0] f_hgi_cmdproc,
    input wire [0:0] f_hgi_rgxa0,
    input wire [0:0] f_hgi_rgxa1,
    input wire [256:0] f_hgi_rgxr0,
    input wire [256:0] f_hgi_rgxr1,
    input wire [273:0] f_hgi_vmr,
    input wire [64:0] f_hgi_vmw2,
    input wire [18:0] f_mtp,
    input wire [1023:0] f_su_NE,
    input wire [1023:0] f_su_NW,
    input wire [1023:0] f_su_SE,
    input wire [1023:0] f_su_SW,
    inout wire [1121:0] llk_N0,
    inout wire [1121:0] llk_N1,
    inout wire [1121:0] llk_N2,
    inout wire [1121:0] llk_N3,
    inout wire [1121:0] llk_S0,
    inout wire [1121:0] llk_S1,
    inout wire [1121:0] llk_S2,
    inout wire [1121:0] llk_S3,
    inout wire [1121:0] llk_S4,
    output wire [0:0] pll_hbm,
    output wire [0:0] pll_link,
    output wire [0:0] pll_serial,
    output wire [0:0] pll_stream,
    output wire [0:0] por_hbm,
    output wire [0:0] por_link,
    output wire [0:0] por_serial,
    output wire [0:0] por_stream,
    output wire [32:0] t_cmdproc,
    output wire [2:0] t_hgi_cmdproc,
    output wire [37:0] t_hgi_rgxq0,
    output wire [37:0] t_hgi_rgxq1,
    output wire [325:0] t_hgi_rgxw0,
    output wire [325:0] t_hgi_rgxw1,
    output wire [79:0] t_hgi_vmaddr_NE,
    output wire [79:0] t_hgi_vmaddr_NW,
    output wire [79:0] t_hgi_vmaddr_SE,
    output wire [79:0] t_hgi_vmaddr_SW,
    output wire [337:0] t_hgi_vmq,
    output wire [8960:0] t_hgi_vmw2,
    output wire [0:0] t_mtp,
    output wire [619:0] t_su_NE,
    output wire [619:0] t_su_NW,
    output wire [619:0] t_su_SE,
    output wire [619:0] t_su_SW,
    /* NOT A GENERATOR PORT (generator-side defect, see note) */ input wire refclk,
    /* NOT A GENERATOR PORT (generator-side defect, see note) */ input wire por
);
    wire[118:0]face_clk={face_ck118,face_ck117,face_ck116,face_ck115,face_ck114,face_ck113,face_ck112,face_ck111,face_ck110,face_ck109,face_ck108,face_ck107,face_ck106,face_ck105,face_ck104,face_ck103,face_ck102,face_ck101,face_ck100,face_ck99,face_ck98,face_ck97,face_ck96,face_ck95,face_ck94,face_ck93,face_ck92,face_ck91,face_ck90,face_ck89,face_ck88,face_ck87,face_ck86,face_ck85,face_ck84,face_ck83,face_ck82,face_ck81,face_ck80,face_ck79,face_ck78,face_ck77,face_ck76,face_ck75,face_ck74,face_ck73,face_ck72,face_ck71,face_ck70,face_ck69,face_ck68,face_ck67,face_ck66,face_ck65,face_ck64,face_ck63,face_ck62,face_ck61,face_ck60,face_ck59,face_ck58,face_ck57,face_ck56,face_ck55,face_ck54,face_ck53,face_ck52,face_ck51,face_ck50,face_ck49,face_ck48,face_ck47,face_ck46,face_ck45,face_ck44,face_ck43,face_ck42,face_ck41,face_ck40,face_ck39,face_ck38,face_ck37,face_ck36,face_ck35,face_ck34,face_ck33,face_ck32,face_ck31,face_ck30,face_ck29,face_ck28,face_ck27,face_ck26,face_ck25,face_ck24,face_ck23,face_ck22,face_ck21,face_ck20,face_ck19,face_ck18,face_ck17,face_ck16,face_ck15,face_ck14,face_ck13,face_ck12,face_ck11,face_ck10,face_ck9,face_ck8,face_ck7,face_ck6,face_ck5,face_ck4,face_ck3,face_ck2,face_ck1,face_ck0};
    wire[3:0]body_clk={body_ck3,body_ck2,body_ck1,body_ck0};
    wire clk = refclk;
    wire rst_n;
    ot_hfd_coll_reset_leaf u_reset (.clk(reset_clk),.por(por),.rst_n(rst_n));
    wire [24:0] i_f_cmdproc;
    ot_hbm_coll_face_pipe512 u_face_0 (.clk(face_clk[0]), .d(512'(f_cmdproc[0 +: 25])), .q(face_q_0));
    wire [511:0] face_q_0;
    assign i_f_cmdproc[0 +: 25] = face_q_0[24:0];
    wire [39:0] i_f_hgi_cfg;
    ot_hbm_coll_face_pipe512 u_face_1 (.clk(face_clk[1]), .d(512'(f_hgi_cfg[0 +: 40])), .q(face_q_1));
    wire [511:0] face_q_1;
    assign i_f_hgi_cfg[0 +: 40] = face_q_1[39:0];
    wire [967:0] i_f_hgi_cmdproc;
    ot_hbm_coll_face_pipe512 u_face_2 (.clk(face_clk[2]), .d(512'(f_hgi_cmdproc[0 +: 512])), .q(face_q_2));
    wire [511:0] face_q_2;
    assign i_f_hgi_cmdproc[0 +: 512] = face_q_2[511:0];
    ot_hbm_coll_face_pipe512 u_face_3 (.clk(face_clk[3]), .d(512'(f_hgi_cmdproc[512 +: 456])), .q(face_q_3));
    wire [511:0] face_q_3;
    assign i_f_hgi_cmdproc[512 +: 456] = face_q_3[455:0];
    wire [0:0] i_f_hgi_rgxa0;
    ot_hbm_coll_face_pipe512 u_face_4 (.clk(face_clk[4]), .d(512'(f_hgi_rgxa0[0 +: 1])), .q(face_q_4));
    wire [511:0] face_q_4;
    assign i_f_hgi_rgxa0[0 +: 1] = face_q_4[0:0];
    wire [0:0] i_f_hgi_rgxa1;
    ot_hbm_coll_face_pipe512 u_face_5 (.clk(face_clk[5]), .d(512'(f_hgi_rgxa1[0 +: 1])), .q(face_q_5));
    wire [511:0] face_q_5;
    assign i_f_hgi_rgxa1[0 +: 1] = face_q_5[0:0];
    wire [256:0] i_f_hgi_rgxr0;
    ot_hbm_coll_face_pipe512 u_face_6 (.clk(face_clk[6]), .d(512'(f_hgi_rgxr0[0 +: 257])), .q(face_q_6));
    wire [511:0] face_q_6;
    assign i_f_hgi_rgxr0[0 +: 257] = face_q_6[256:0];
    wire [256:0] i_f_hgi_rgxr1;
    ot_hbm_coll_face_pipe512 u_face_7 (.clk(face_clk[7]), .d(512'(f_hgi_rgxr1[0 +: 257])), .q(face_q_7));
    wire [511:0] face_q_7;
    assign i_f_hgi_rgxr1[0 +: 257] = face_q_7[256:0];
    wire [273:0] i_f_hgi_vmr;
    ot_hbm_coll_face_pipe512 u_face_8 (.clk(face_clk[8]), .d(512'(f_hgi_vmr[0 +: 274])), .q(face_q_8));
    wire [511:0] face_q_8;
    assign i_f_hgi_vmr[0 +: 274] = face_q_8[273:0];
    wire [64:0] i_f_hgi_vmw2;
    ot_hbm_coll_face_pipe512 u_face_9 (.clk(face_clk[9]), .d(512'(f_hgi_vmw2[0 +: 65])), .q(face_q_9));
    wire [511:0] face_q_9;
    assign i_f_hgi_vmw2[0 +: 65] = face_q_9[64:0];
    wire [18:0] i_f_mtp;
    ot_hbm_coll_face_pipe512 u_face_10 (.clk(face_clk[10]), .d(512'(f_mtp[0 +: 19])), .q(face_q_10));
    wire [511:0] face_q_10;
    assign i_f_mtp[0 +: 19] = face_q_10[18:0];
    wire [1023:0] i_f_su_NE;
    ot_hbm_coll_face_pipe512 u_face_11 (.clk(face_clk[11]), .d(512'(f_su_NE[0 +: 512])), .q(face_q_11));
    wire [511:0] face_q_11;
    assign i_f_su_NE[0 +: 512] = face_q_11[511:0];
    ot_hbm_coll_face_pipe512 u_face_12 (.clk(face_clk[12]), .d(512'(f_su_NE[512 +: 512])), .q(face_q_12));
    wire [511:0] face_q_12;
    assign i_f_su_NE[512 +: 512] = face_q_12[511:0];
    wire [1023:0] i_f_su_NW;
    ot_hbm_coll_face_pipe512 u_face_13 (.clk(face_clk[13]), .d(512'(f_su_NW[0 +: 512])), .q(face_q_13));
    wire [511:0] face_q_13;
    assign i_f_su_NW[0 +: 512] = face_q_13[511:0];
    ot_hbm_coll_face_pipe512 u_face_14 (.clk(face_clk[14]), .d(512'(f_su_NW[512 +: 512])), .q(face_q_14));
    wire [511:0] face_q_14;
    assign i_f_su_NW[512 +: 512] = face_q_14[511:0];
    wire [1023:0] i_f_su_SE;
    ot_hbm_coll_face_pipe512 u_face_15 (.clk(face_clk[15]), .d(512'(f_su_SE[0 +: 512])), .q(face_q_15));
    wire [511:0] face_q_15;
    assign i_f_su_SE[0 +: 512] = face_q_15[511:0];
    ot_hbm_coll_face_pipe512 u_face_16 (.clk(face_clk[16]), .d(512'(f_su_SE[512 +: 512])), .q(face_q_16));
    wire [511:0] face_q_16;
    assign i_f_su_SE[512 +: 512] = face_q_16[511:0];
    wire [1023:0] i_f_su_SW;
    ot_hbm_coll_face_pipe512 u_face_17 (.clk(face_clk[17]), .d(512'(f_su_SW[0 +: 512])), .q(face_q_17));
    wire [511:0] face_q_17;
    assign i_f_su_SW[0 +: 512] = face_q_17[511:0];
    ot_hbm_coll_face_pipe512 u_face_18 (.clk(face_clk[18]), .d(512'(f_su_SW[512 +: 512])), .q(face_q_18));
    wire [511:0] face_q_18;
    assign i_f_su_SW[512 +: 512] = face_q_18[511:0];
    wire [1121:0] i_llk_N0;
    ot_hbm_coll_face_pipe512 u_face_19 (.clk(face_clk[19]), .d(512'(llk_N0[0 +: 512])), .q(face_q_19));
    wire [511:0] face_q_19;
    assign i_llk_N0[0 +: 512] = face_q_19[511:0];
    ot_hbm_coll_face_pipe512 u_face_20 (.clk(face_clk[20]), .d(512'(llk_N0[512 +: 512])), .q(face_q_20));
    wire [511:0] face_q_20;
    assign i_llk_N0[512 +: 512] = face_q_20[511:0];
    ot_hbm_coll_face_pipe512 u_face_21 (.clk(face_clk[21]), .d(512'(llk_N0[1024 +: 98])), .q(face_q_21));
    wire [511:0] face_q_21;
    assign i_llk_N0[1024 +: 98] = face_q_21[97:0];
    wire [1121:0] i_llk_N1;
    ot_hbm_coll_face_pipe512 u_face_22 (.clk(face_clk[22]), .d(512'(llk_N1[0 +: 512])), .q(face_q_22));
    wire [511:0] face_q_22;
    assign i_llk_N1[0 +: 512] = face_q_22[511:0];
    ot_hbm_coll_face_pipe512 u_face_23 (.clk(face_clk[23]), .d(512'(llk_N1[512 +: 512])), .q(face_q_23));
    wire [511:0] face_q_23;
    assign i_llk_N1[512 +: 512] = face_q_23[511:0];
    ot_hbm_coll_face_pipe512 u_face_24 (.clk(face_clk[24]), .d(512'(llk_N1[1024 +: 98])), .q(face_q_24));
    wire [511:0] face_q_24;
    assign i_llk_N1[1024 +: 98] = face_q_24[97:0];
    wire [1121:0] i_llk_N2;
    ot_hbm_coll_face_pipe512 u_face_25 (.clk(face_clk[25]), .d(512'(llk_N2[0 +: 512])), .q(face_q_25));
    wire [511:0] face_q_25;
    assign i_llk_N2[0 +: 512] = face_q_25[511:0];
    ot_hbm_coll_face_pipe512 u_face_26 (.clk(face_clk[26]), .d(512'(llk_N2[512 +: 512])), .q(face_q_26));
    wire [511:0] face_q_26;
    assign i_llk_N2[512 +: 512] = face_q_26[511:0];
    ot_hbm_coll_face_pipe512 u_face_27 (.clk(face_clk[27]), .d(512'(llk_N2[1024 +: 98])), .q(face_q_27));
    wire [511:0] face_q_27;
    assign i_llk_N2[1024 +: 98] = face_q_27[97:0];
    wire [1121:0] i_llk_N3;
    ot_hbm_coll_face_pipe512 u_face_28 (.clk(face_clk[28]), .d(512'(llk_N3[0 +: 512])), .q(face_q_28));
    wire [511:0] face_q_28;
    assign i_llk_N3[0 +: 512] = face_q_28[511:0];
    ot_hbm_coll_face_pipe512 u_face_29 (.clk(face_clk[29]), .d(512'(llk_N3[512 +: 512])), .q(face_q_29));
    wire [511:0] face_q_29;
    assign i_llk_N3[512 +: 512] = face_q_29[511:0];
    ot_hbm_coll_face_pipe512 u_face_30 (.clk(face_clk[30]), .d(512'(llk_N3[1024 +: 98])), .q(face_q_30));
    wire [511:0] face_q_30;
    assign i_llk_N3[1024 +: 98] = face_q_30[97:0];
    wire [1121:0] i_llk_S0;
    ot_hbm_coll_face_pipe512 u_face_31 (.clk(face_clk[31]), .d(512'(llk_S0[0 +: 512])), .q(face_q_31));
    wire [511:0] face_q_31;
    assign i_llk_S0[0 +: 512] = face_q_31[511:0];
    ot_hbm_coll_face_pipe512 u_face_32 (.clk(face_clk[32]), .d(512'(llk_S0[512 +: 512])), .q(face_q_32));
    wire [511:0] face_q_32;
    assign i_llk_S0[512 +: 512] = face_q_32[511:0];
    ot_hbm_coll_face_pipe512 u_face_33 (.clk(face_clk[33]), .d(512'(llk_S0[1024 +: 98])), .q(face_q_33));
    wire [511:0] face_q_33;
    assign i_llk_S0[1024 +: 98] = face_q_33[97:0];
    wire [1121:0] i_llk_S1;
    ot_hbm_coll_face_pipe512 u_face_34 (.clk(face_clk[34]), .d(512'(llk_S1[0 +: 512])), .q(face_q_34));
    wire [511:0] face_q_34;
    assign i_llk_S1[0 +: 512] = face_q_34[511:0];
    ot_hbm_coll_face_pipe512 u_face_35 (.clk(face_clk[35]), .d(512'(llk_S1[512 +: 512])), .q(face_q_35));
    wire [511:0] face_q_35;
    assign i_llk_S1[512 +: 512] = face_q_35[511:0];
    ot_hbm_coll_face_pipe512 u_face_36 (.clk(face_clk[36]), .d(512'(llk_S1[1024 +: 98])), .q(face_q_36));
    wire [511:0] face_q_36;
    assign i_llk_S1[1024 +: 98] = face_q_36[97:0];
    wire [1121:0] i_llk_S2;
    ot_hbm_coll_face_pipe512 u_face_37 (.clk(face_clk[37]), .d(512'(llk_S2[0 +: 512])), .q(face_q_37));
    wire [511:0] face_q_37;
    assign i_llk_S2[0 +: 512] = face_q_37[511:0];
    ot_hbm_coll_face_pipe512 u_face_38 (.clk(face_clk[38]), .d(512'(llk_S2[512 +: 512])), .q(face_q_38));
    wire [511:0] face_q_38;
    assign i_llk_S2[512 +: 512] = face_q_38[511:0];
    ot_hbm_coll_face_pipe512 u_face_39 (.clk(face_clk[39]), .d(512'(llk_S2[1024 +: 98])), .q(face_q_39));
    wire [511:0] face_q_39;
    assign i_llk_S2[1024 +: 98] = face_q_39[97:0];
    wire [1121:0] i_llk_S3;
    ot_hbm_coll_face_pipe512 u_face_40 (.clk(face_clk[40]), .d(512'(llk_S3[0 +: 512])), .q(face_q_40));
    wire [511:0] face_q_40;
    assign i_llk_S3[0 +: 512] = face_q_40[511:0];
    ot_hbm_coll_face_pipe512 u_face_41 (.clk(face_clk[41]), .d(512'(llk_S3[512 +: 512])), .q(face_q_41));
    wire [511:0] face_q_41;
    assign i_llk_S3[512 +: 512] = face_q_41[511:0];
    ot_hbm_coll_face_pipe512 u_face_42 (.clk(face_clk[42]), .d(512'(llk_S3[1024 +: 98])), .q(face_q_42));
    wire [511:0] face_q_42;
    assign i_llk_S3[1024 +: 98] = face_q_42[97:0];
    wire [1121:0] i_llk_S4;
    ot_hbm_coll_face_pipe512 u_face_43 (.clk(face_clk[43]), .d(512'(llk_S4[0 +: 512])), .q(face_q_43));
    wire [511:0] face_q_43;
    assign i_llk_S4[0 +: 512] = face_q_43[511:0];
    ot_hbm_coll_face_pipe512 u_face_44 (.clk(face_clk[44]), .d(512'(llk_S4[512 +: 512])), .q(face_q_44));
    wire [511:0] face_q_44;
    assign i_llk_S4[512 +: 512] = face_q_44[511:0];
    ot_hbm_coll_face_pipe512 u_face_45 (.clk(face_clk[45]), .d(512'(llk_S4[1024 +: 98])), .q(face_q_45));
    wire [511:0] face_q_45;
    assign i_llk_S4[1024 +: 98] = face_q_45[97:0];
    wire [0:0] w_co_clk;
    wire [0:0] w_co_rst_n;
    wire [7:0] w_co_rank;
    wire [15:0] w_co_pf;
    wire [0:0] w_co_go;
    wire [31:0] w_co_inj_idx;
    wire [1:0] w_co_inj_rd;
    wire [4095:0] w_co_inj_q;
    wire [3:0] w_co_del_valid;
    wire [2179:0] w_co_del_flit;
    wire [0:0] w_co_fault;
    wire [31:0] w_co_stat_credit_stall;
    wire [967:0] w_co_hgi_rec;
    wire [2:0] w_co_hgi_ret;
    wire [39:0] w_co_hgi_cfg;
    wire [93:0] w_co_hgi_rowfmt_o;
    wire [2:0] w_co_hgi_rowfmt_i;
    wire [79:0] w_co_hgi_vmaddr;
    wire [159:0] w_co_hgi_del_obase;
    wire [8:0] w_co_lk_tx_v;
    wire [4904:0] w_co_lk_tx_flit;
    wire [8:0] w_co_lk_rx_credit;
    wire [8:0] w_co_lk_rx_v;
    wire [4904:0] w_co_lk_rx_flit;
    wire [8:0] w_co_lk_sw_cr;
    wire [215:0] w_co_lk_session;
    wire [8:0] w_co_lk_fault;
    wire [8:0] w_co_lk_locked;
    wire [17:0] w_co_lk_status;
    wire [75:0] w_co_rgx_xq;
    wire [513:0] w_co_rgx_xr;
    wire [337:0] w_co_rgx_vmq;
    wire [273:0] w_co_rgx_vmr;
    wire [0:0] w_co_rgx_c_req;
    wire [0:0] w_co_rgx_c_gnt;
    wire [8959:0] w_co_rgx_c_q;
    wire [31:0] w_co_rgx_c_cr;
    wire [31:0] w_co_rgx_c_rsp;
    wire [651:0] w_co_rgx_xw;
    wire [1:0] w_co_rgx_xwa;
    assign w_co_clk = {1{clk}};
    assign w_co_rst_n = {1{rst_n}};
    assign w_co_rank = {i_f_cmdproc[7:0]};
    assign w_co_pf = {i_f_cmdproc[23:8]};
    assign w_co_go = {i_f_cmdproc[24:24]};
    assign w_co_inj_q = {i_f_su_NE[1023:0], i_f_su_SE[1023:0], i_f_su_NW[1023:0], i_f_su_SW[1023:0]};
    assign w_co_hgi_rec = {i_f_hgi_cmdproc[967:0]};
    assign w_co_hgi_cfg = {i_f_hgi_cfg[39:0]};
    assign w_co_hgi_rowfmt_i = 3'd0;
    assign w_co_lk_rx_v = {i_llk_N3[547:547], i_llk_N2[547:547], i_llk_N1[547:547], i_llk_N0[547:547], i_llk_S4[547:547], i_llk_S3[547:547], i_llk_S2[547:547], i_llk_S1[547:547], i_llk_S0[547:547]};
    assign w_co_lk_rx_flit = {i_llk_N3[1092:548], i_llk_N2[1092:548], i_llk_N1[1092:548], i_llk_N0[1092:548], i_llk_S4[1092:548], i_llk_S3[1092:548], i_llk_S2[1092:548], i_llk_S1[1092:548], i_llk_S0[1092:548]};
    assign w_co_lk_sw_cr = {i_llk_N3[1093:1093], i_llk_N2[1093:1093], i_llk_N1[1093:1093], i_llk_N0[1093:1093], i_llk_S4[1093:1093], i_llk_S3[1093:1093], i_llk_S2[1093:1093], i_llk_S1[1093:1093], i_llk_S0[1093:1093]};
    assign w_co_lk_fault = {i_llk_N3[1118:1118], i_llk_N2[1118:1118], i_llk_N1[1118:1118], i_llk_N0[1118:1118], i_llk_S4[1118:1118], i_llk_S3[1118:1118], i_llk_S2[1118:1118], i_llk_S1[1118:1118], i_llk_S0[1118:1118]};
    assign w_co_lk_locked = {i_llk_N3[1119:1119], i_llk_N2[1119:1119], i_llk_N1[1119:1119], i_llk_N0[1119:1119], i_llk_S4[1119:1119], i_llk_S3[1119:1119], i_llk_S2[1119:1119], i_llk_S1[1119:1119], i_llk_S0[1119:1119]};
    assign w_co_rgx_xr = {i_f_hgi_rgxr1[256:0], i_f_hgi_rgxr0[256:0]};
    assign w_co_rgx_vmr = {i_f_hgi_vmr[273:0]};
    assign w_co_rgx_c_gnt = {i_f_hgi_vmw2[64:64]};
    assign w_co_rgx_c_cr = {i_f_hgi_vmw2[63:32]};
    assign w_co_rgx_c_rsp = {i_f_hgi_vmw2[31:0]};
    assign w_co_rgx_xwa = {i_f_hgi_rgxa1[0:0], i_f_hgi_rgxa0[0:0]};
    ot_hfd_coll_body_cluster u_co (.reduce_clk(reduce_ck),.column_clk({column_ck7,column_ck6,column_ck5,column_ck4,column_ck3,column_ck2,column_ck1,column_ck0}),.port_clk({port_ck8,port_ck7,port_ck6,port_ck5,port_ck4,port_ck3,port_ck2,port_ck1,port_ck0}),.park_clk_q({park_ck3,park_ck2,park_ck1,park_ck0}),.park_fault_clk(park_fault_ck),.child_clk(body_clk), .clk(w_co_clk), .rst_n(w_co_rst_n), .rank(w_co_rank), .pf(w_co_pf), .go(w_co_go), .inj_idx(w_co_inj_idx), .inj_rd(w_co_inj_rd), .inj_q(w_co_inj_q), .del_valid(w_co_del_valid), .del_flit(w_co_del_flit), .fault(w_co_fault), .stat_credit_stall(w_co_stat_credit_stall), .hgi_rec(w_co_hgi_rec), .hgi_ret(w_co_hgi_ret), .hgi_cfg(w_co_hgi_cfg), .hgi_rowfmt_o(w_co_hgi_rowfmt_o), .hgi_rowfmt_i(w_co_hgi_rowfmt_i), .hgi_vmaddr(w_co_hgi_vmaddr), .hgi_del_obase(w_co_hgi_del_obase), .lk_tx_v(w_co_lk_tx_v), .lk_tx_flit(w_co_lk_tx_flit), .lk_rx_credit(w_co_lk_rx_credit), .lk_rx_v(w_co_lk_rx_v), .lk_rx_flit(w_co_lk_rx_flit), .lk_sw_cr(w_co_lk_sw_cr), .lk_session(w_co_lk_session), .lk_fault(w_co_lk_fault), .lk_locked(w_co_lk_locked), .lk_status(w_co_lk_status), .rgx_xq(w_co_rgx_xq), .rgx_xr(w_co_rgx_xr), .rgx_vmq(w_co_rgx_vmq), .rgx_vmr(w_co_rgx_vmr), .rgx_c_req(w_co_rgx_c_req), .rgx_c_gnt(w_co_rgx_c_gnt), .rgx_c_q(w_co_rgx_c_q), .rgx_c_cr(w_co_rgx_c_cr), .rgx_c_rsp(w_co_rgx_c_rsp), .rgx_xw(w_co_rgx_xw), .rgx_xwa(w_co_rgx_xwa));
    (* keep *)ot_hfd_coll_monitor_leaf u_monitor(.clk(monitor_clk),.d({w_co_hgi_rowfmt_o,w_co_lk_status}),.q());
    wire fclk_0; ot_fwd_clk_inv u_fclk_0 (.a(clk), .y(fclk_0));
    wire fclk_1; ot_fwd_clk_inv u_fclk_1 (.a(clk), .y(fclk_1));
    wire fclk_2; ot_fwd_clk_inv u_fclk_2 (.a(clk), .y(fclk_2));
    wire fclk_3; ot_fwd_clk_inv u_fclk_3 (.a(clk), .y(fclk_3));
    wire [1121:0] od_llk_N0 = {1'd0, clk, 2'd0, w_co_lk_session[143:120], 547'd0, w_co_lk_rx_credit[5:5], w_co_lk_tx_flit[3269:2725], w_co_lk_tx_v[5:5]};
    wire [1121:0] o_llk_N0;
    ot_hbm_coll_face_pipe512 u_face_46 (.clk(face_clk[46]), .d(512'(od_llk_N0[0 +: 512])), .q(face_q_46));
    wire [511:0] face_q_46;
    assign o_llk_N0[0 +: 512] = face_q_46[511:0];
    ot_hbm_coll_face_pipe512 u_face_47 (.clk(face_clk[47]), .d(512'(od_llk_N0[512 +: 512])), .q(face_q_47));
    wire [511:0] face_q_47;
    assign o_llk_N0[512 +: 512] = face_q_47[511:0];
    ot_hbm_coll_face_pipe512 u_face_48 (.clk(face_clk[48]), .d(512'(od_llk_N0[1024 +: 98])), .q(face_q_48));
    wire [511:0] face_q_48;
    assign o_llk_N0[1024 +: 98] = face_q_48[97:0];
    assign llk_N0[546:0] = o_llk_N0[546:0];
    assign llk_N0[1117:1094] = o_llk_N0[1117:1094];
    assign llk_N0[1120:1120] = o_llk_N0[1120:1120];
    wire [1121:0] od_llk_N1 = {1'd0, clk, 2'd0, w_co_lk_session[167:144], 547'd0, w_co_lk_rx_credit[6:6], w_co_lk_tx_flit[3814:3270], w_co_lk_tx_v[6:6]};
    wire [1121:0] o_llk_N1;
    ot_hbm_coll_face_pipe512 u_face_49 (.clk(face_clk[49]), .d(512'(od_llk_N1[0 +: 512])), .q(face_q_49));
    wire [511:0] face_q_49;
    assign o_llk_N1[0 +: 512] = face_q_49[511:0];
    ot_hbm_coll_face_pipe512 u_face_50 (.clk(face_clk[50]), .d(512'(od_llk_N1[512 +: 512])), .q(face_q_50));
    wire [511:0] face_q_50;
    assign o_llk_N1[512 +: 512] = face_q_50[511:0];
    ot_hbm_coll_face_pipe512 u_face_51 (.clk(face_clk[51]), .d(512'(od_llk_N1[1024 +: 98])), .q(face_q_51));
    wire [511:0] face_q_51;
    assign o_llk_N1[1024 +: 98] = face_q_51[97:0];
    assign llk_N1[546:0] = o_llk_N1[546:0];
    assign llk_N1[1117:1094] = o_llk_N1[1117:1094];
    assign llk_N1[1120:1120] = o_llk_N1[1120:1120];
    wire [1121:0] od_llk_N2 = {1'd0, clk, 2'd0, w_co_lk_session[191:168], 547'd0, w_co_lk_rx_credit[7:7], w_co_lk_tx_flit[4359:3815], w_co_lk_tx_v[7:7]};
    wire [1121:0] o_llk_N2;
    ot_hbm_coll_face_pipe512 u_face_52 (.clk(face_clk[52]), .d(512'(od_llk_N2[0 +: 512])), .q(face_q_52));
    wire [511:0] face_q_52;
    assign o_llk_N2[0 +: 512] = face_q_52[511:0];
    ot_hbm_coll_face_pipe512 u_face_53 (.clk(face_clk[53]), .d(512'(od_llk_N2[512 +: 512])), .q(face_q_53));
    wire [511:0] face_q_53;
    assign o_llk_N2[512 +: 512] = face_q_53[511:0];
    ot_hbm_coll_face_pipe512 u_face_54 (.clk(face_clk[54]), .d(512'(od_llk_N2[1024 +: 98])), .q(face_q_54));
    wire [511:0] face_q_54;
    assign o_llk_N2[1024 +: 98] = face_q_54[97:0];
    assign llk_N2[546:0] = o_llk_N2[546:0];
    assign llk_N2[1117:1094] = o_llk_N2[1117:1094];
    assign llk_N2[1120:1120] = o_llk_N2[1120:1120];
    wire [1121:0] od_llk_N3 = {1'd0, clk, 2'd0, w_co_lk_session[215:192], 547'd0, w_co_lk_rx_credit[8:8], w_co_lk_tx_flit[4904:4360], w_co_lk_tx_v[8:8]};
    wire [1121:0] o_llk_N3;
    ot_hbm_coll_face_pipe512 u_face_55 (.clk(face_clk[55]), .d(512'(od_llk_N3[0 +: 512])), .q(face_q_55));
    wire [511:0] face_q_55;
    assign o_llk_N3[0 +: 512] = face_q_55[511:0];
    ot_hbm_coll_face_pipe512 u_face_56 (.clk(face_clk[56]), .d(512'(od_llk_N3[512 +: 512])), .q(face_q_56));
    wire [511:0] face_q_56;
    assign o_llk_N3[512 +: 512] = face_q_56[511:0];
    ot_hbm_coll_face_pipe512 u_face_57 (.clk(face_clk[57]), .d(512'(od_llk_N3[1024 +: 98])), .q(face_q_57));
    wire [511:0] face_q_57;
    assign o_llk_N3[1024 +: 98] = face_q_57[97:0];
    assign llk_N3[546:0] = o_llk_N3[546:0];
    assign llk_N3[1117:1094] = o_llk_N3[1117:1094];
    assign llk_N3[1120:1120] = o_llk_N3[1120:1120];
    wire [1121:0] od_llk_S0 = {1'd0, clk, 2'd0, w_co_lk_session[23:0], 547'd0, w_co_lk_rx_credit[0:0], w_co_lk_tx_flit[544:0], w_co_lk_tx_v[0:0]};
    wire [1121:0] o_llk_S0;
    ot_hbm_coll_face_pipe512 u_face_58 (.clk(face_clk[58]), .d(512'(od_llk_S0[0 +: 512])), .q(face_q_58));
    wire [511:0] face_q_58;
    assign o_llk_S0[0 +: 512] = face_q_58[511:0];
    ot_hbm_coll_face_pipe512 u_face_59 (.clk(face_clk[59]), .d(512'(od_llk_S0[512 +: 512])), .q(face_q_59));
    wire [511:0] face_q_59;
    assign o_llk_S0[512 +: 512] = face_q_59[511:0];
    ot_hbm_coll_face_pipe512 u_face_60 (.clk(face_clk[60]), .d(512'(od_llk_S0[1024 +: 98])), .q(face_q_60));
    wire [511:0] face_q_60;
    assign o_llk_S0[1024 +: 98] = face_q_60[97:0];
    assign llk_S0[546:0] = o_llk_S0[546:0];
    assign llk_S0[1117:1094] = o_llk_S0[1117:1094];
    assign llk_S0[1120:1120] = o_llk_S0[1120:1120];
    wire [1121:0] od_llk_S1 = {1'd0, clk, 2'd0, w_co_lk_session[47:24], 547'd0, w_co_lk_rx_credit[1:1], w_co_lk_tx_flit[1089:545], w_co_lk_tx_v[1:1]};
    wire [1121:0] o_llk_S1;
    ot_hbm_coll_face_pipe512 u_face_61 (.clk(face_clk[61]), .d(512'(od_llk_S1[0 +: 512])), .q(face_q_61));
    wire [511:0] face_q_61;
    assign o_llk_S1[0 +: 512] = face_q_61[511:0];
    ot_hbm_coll_face_pipe512 u_face_62 (.clk(face_clk[62]), .d(512'(od_llk_S1[512 +: 512])), .q(face_q_62));
    wire [511:0] face_q_62;
    assign o_llk_S1[512 +: 512] = face_q_62[511:0];
    ot_hbm_coll_face_pipe512 u_face_63 (.clk(face_clk[63]), .d(512'(od_llk_S1[1024 +: 98])), .q(face_q_63));
    wire [511:0] face_q_63;
    assign o_llk_S1[1024 +: 98] = face_q_63[97:0];
    assign llk_S1[546:0] = o_llk_S1[546:0];
    assign llk_S1[1117:1094] = o_llk_S1[1117:1094];
    assign llk_S1[1120:1120] = o_llk_S1[1120:1120];
    wire [1121:0] od_llk_S2 = {1'd0, clk, 2'd0, w_co_lk_session[71:48], 547'd0, w_co_lk_rx_credit[2:2], w_co_lk_tx_flit[1634:1090], w_co_lk_tx_v[2:2]};
    wire [1121:0] o_llk_S2;
    ot_hbm_coll_face_pipe512 u_face_64 (.clk(face_clk[64]), .d(512'(od_llk_S2[0 +: 512])), .q(face_q_64));
    wire [511:0] face_q_64;
    assign o_llk_S2[0 +: 512] = face_q_64[511:0];
    ot_hbm_coll_face_pipe512 u_face_65 (.clk(face_clk[65]), .d(512'(od_llk_S2[512 +: 512])), .q(face_q_65));
    wire [511:0] face_q_65;
    assign o_llk_S2[512 +: 512] = face_q_65[511:0];
    ot_hbm_coll_face_pipe512 u_face_66 (.clk(face_clk[66]), .d(512'(od_llk_S2[1024 +: 98])), .q(face_q_66));
    wire [511:0] face_q_66;
    assign o_llk_S2[1024 +: 98] = face_q_66[97:0];
    assign llk_S2[546:0] = o_llk_S2[546:0];
    assign llk_S2[1117:1094] = o_llk_S2[1117:1094];
    assign llk_S2[1120:1120] = o_llk_S2[1120:1120];
    wire [1121:0] od_llk_S3 = {1'd0, clk, 2'd0, w_co_lk_session[95:72], 547'd0, w_co_lk_rx_credit[3:3], w_co_lk_tx_flit[2179:1635], w_co_lk_tx_v[3:3]};
    wire [1121:0] o_llk_S3;
    ot_hbm_coll_face_pipe512 u_face_67 (.clk(face_clk[67]), .d(512'(od_llk_S3[0 +: 512])), .q(face_q_67));
    wire [511:0] face_q_67;
    assign o_llk_S3[0 +: 512] = face_q_67[511:0];
    ot_hbm_coll_face_pipe512 u_face_68 (.clk(face_clk[68]), .d(512'(od_llk_S3[512 +: 512])), .q(face_q_68));
    wire [511:0] face_q_68;
    assign o_llk_S3[512 +: 512] = face_q_68[511:0];
    ot_hbm_coll_face_pipe512 u_face_69 (.clk(face_clk[69]), .d(512'(od_llk_S3[1024 +: 98])), .q(face_q_69));
    wire [511:0] face_q_69;
    assign o_llk_S3[1024 +: 98] = face_q_69[97:0];
    assign llk_S3[546:0] = o_llk_S3[546:0];
    assign llk_S3[1117:1094] = o_llk_S3[1117:1094];
    assign llk_S3[1120:1120] = o_llk_S3[1120:1120];
    wire [1121:0] od_llk_S4 = {1'd0, clk, 2'd0, w_co_lk_session[119:96], 547'd0, w_co_lk_rx_credit[4:4], w_co_lk_tx_flit[2724:2180], w_co_lk_tx_v[4:4]};
    wire [1121:0] o_llk_S4;
    ot_hbm_coll_face_pipe512 u_face_70 (.clk(face_clk[70]), .d(512'(od_llk_S4[0 +: 512])), .q(face_q_70));
    wire [511:0] face_q_70;
    assign o_llk_S4[0 +: 512] = face_q_70[511:0];
    ot_hbm_coll_face_pipe512 u_face_71 (.clk(face_clk[71]), .d(512'(od_llk_S4[512 +: 512])), .q(face_q_71));
    wire [511:0] face_q_71;
    assign o_llk_S4[512 +: 512] = face_q_71[511:0];
    ot_hbm_coll_face_pipe512 u_face_72 (.clk(face_clk[72]), .d(512'(od_llk_S4[1024 +: 98])), .q(face_q_72));
    wire [511:0] face_q_72;
    assign o_llk_S4[1024 +: 98] = face_q_72[97:0];
    assign llk_S4[546:0] = o_llk_S4[546:0];
    assign llk_S4[1117:1094] = o_llk_S4[1117:1094];
    assign llk_S4[1120:1120] = o_llk_S4[1120:1120];
    wire [0:0] od_pll_hbm = {1'd0};
    wire [0:0] o_pll_hbm;
    ot_hbm_coll_face_pipe512 u_face_73 (.clk(face_clk[73]), .d(512'(od_pll_hbm[0 +: 1])), .q(face_q_73));
    wire [511:0] face_q_73;
    assign o_pll_hbm[0 +: 1] = face_q_73[0:0];
    assign pll_hbm[0] = fclk_0;
    wire [0:0] od_pll_link = {1'd0};
    wire [0:0] o_pll_link;
    ot_hbm_coll_face_pipe512 u_face_74 (.clk(face_clk[74]), .d(512'(od_pll_link[0 +: 1])), .q(face_q_74));
    wire [511:0] face_q_74;
    assign o_pll_link[0 +: 1] = face_q_74[0:0];
    assign pll_link[0] = fclk_1;
    wire [0:0] od_pll_serial = {1'd0};
    wire [0:0] o_pll_serial;
    ot_hbm_coll_face_pipe512 u_face_75 (.clk(face_clk[75]), .d(512'(od_pll_serial[0 +: 1])), .q(face_q_75));
    wire [511:0] face_q_75;
    assign o_pll_serial[0 +: 1] = face_q_75[0:0];
    assign pll_serial[0] = fclk_2;
    wire [0:0] od_pll_stream = {1'd0};
    wire [0:0] o_pll_stream;
    ot_hbm_coll_face_pipe512 u_face_76 (.clk(face_clk[76]), .d(512'(od_pll_stream[0 +: 1])), .q(face_q_76));
    wire [511:0] face_q_76;
    assign o_pll_stream[0 +: 1] = face_q_76[0:0];
    assign pll_stream[0] = fclk_3;
    wire [0:0] od_por_hbm = {rst_s[1]};
    wire [0:0] o_por_hbm;
    ot_hbm_coll_face_pipe512 u_face_77 (.clk(face_clk[77]), .d(512'(od_por_hbm[0 +: 1])), .q(face_q_77));
    wire [511:0] face_q_77;
    assign o_por_hbm[0 +: 1] = face_q_77[0:0];
    assign por_hbm[0:0] = o_por_hbm[0:0];
    wire [0:0] od_por_link = {rst_s[1]};
    wire [0:0] o_por_link;
    ot_hbm_coll_face_pipe512 u_face_78 (.clk(face_clk[78]), .d(512'(od_por_link[0 +: 1])), .q(face_q_78));
    wire [511:0] face_q_78;
    assign o_por_link[0 +: 1] = face_q_78[0:0];
    assign por_link[0:0] = o_por_link[0:0];
    wire [0:0] od_por_serial = {rst_s[1]};
    wire [0:0] o_por_serial;
    ot_hbm_coll_face_pipe512 u_face_79 (.clk(face_clk[79]), .d(512'(od_por_serial[0 +: 1])), .q(face_q_79));
    wire [511:0] face_q_79;
    assign o_por_serial[0 +: 1] = face_q_79[0:0];
    assign por_serial[0:0] = o_por_serial[0:0];
    wire [0:0] od_por_stream = {rst_s[1]};
    wire [0:0] o_por_stream;
    ot_hbm_coll_face_pipe512 u_face_80 (.clk(face_clk[80]), .d(512'(od_por_stream[0 +: 1])), .q(face_q_80));
    wire [511:0] face_q_80;
    assign o_por_stream[0 +: 1] = face_q_80[0:0];
    assign por_stream[0:0] = o_por_stream[0:0];
    wire [32:0] od_t_cmdproc = {w_co_stat_credit_stall[31:0], w_co_fault[0:0]};
    wire [32:0] o_t_cmdproc;
    ot_hbm_coll_face_pipe512 u_face_81 (.clk(face_clk[81]), .d(512'(od_t_cmdproc[0 +: 33])), .q(face_q_81));
    wire [511:0] face_q_81;
    assign o_t_cmdproc[0 +: 33] = face_q_81[32:0];
    assign t_cmdproc[32:0] = o_t_cmdproc[32:0];
    wire [2:0] od_t_hgi_cmdproc = {w_co_hgi_ret[2:0]};
    wire [2:0] o_t_hgi_cmdproc;
    ot_hbm_coll_face_pipe512 u_face_82 (.clk(face_clk[82]), .d(512'(od_t_hgi_cmdproc[0 +: 3])), .q(face_q_82));
    wire [511:0] face_q_82;
    assign o_t_hgi_cmdproc[0 +: 3] = face_q_82[2:0];
    assign t_hgi_cmdproc[2:0] = o_t_hgi_cmdproc[2:0];
    wire [37:0] od_t_hgi_rgxq0 = {w_co_rgx_xq[37:0]};
    wire [37:0] o_t_hgi_rgxq0;
    ot_hbm_coll_face_pipe512 u_face_83 (.clk(face_clk[83]), .d(512'(od_t_hgi_rgxq0[0 +: 38])), .q(face_q_83));
    wire [511:0] face_q_83;
    assign o_t_hgi_rgxq0[0 +: 38] = face_q_83[37:0];
    assign t_hgi_rgxq0[37:0] = o_t_hgi_rgxq0[37:0];
    wire [37:0] od_t_hgi_rgxq1 = {w_co_rgx_xq[75:38]};
    wire [37:0] o_t_hgi_rgxq1;
    ot_hbm_coll_face_pipe512 u_face_84 (.clk(face_clk[84]), .d(512'(od_t_hgi_rgxq1[0 +: 38])), .q(face_q_84));
    wire [511:0] face_q_84;
    assign o_t_hgi_rgxq1[0 +: 38] = face_q_84[37:0];
    assign t_hgi_rgxq1[37:0] = o_t_hgi_rgxq1[37:0];
    wire [325:0] od_t_hgi_rgxw0 = {w_co_rgx_xw[325:0]};
    wire [325:0] o_t_hgi_rgxw0;
    ot_hbm_coll_face_pipe512 u_face_85 (.clk(face_clk[85]), .d(512'(od_t_hgi_rgxw0[0 +: 326])), .q(face_q_85));
    wire [511:0] face_q_85;
    assign o_t_hgi_rgxw0[0 +: 326] = face_q_85[325:0];
    assign t_hgi_rgxw0[325:0] = o_t_hgi_rgxw0[325:0];
    wire [325:0] od_t_hgi_rgxw1 = {w_co_rgx_xw[651:326]};
    wire [325:0] o_t_hgi_rgxw1;
    ot_hbm_coll_face_pipe512 u_face_86 (.clk(face_clk[86]), .d(512'(od_t_hgi_rgxw1[0 +: 326])), .q(face_q_86));
    wire [511:0] face_q_86;
    assign o_t_hgi_rgxw1[0 +: 326] = face_q_86[325:0];
    assign t_hgi_rgxw1[325:0] = o_t_hgi_rgxw1[325:0];
    wire [79:0] od_t_hgi_vmaddr_NE = {w_co_hgi_vmaddr[79:0]};
    wire [79:0] o_t_hgi_vmaddr_NE;
    ot_hbm_coll_face_pipe512 u_face_87 (.clk(face_clk[87]), .d(512'(od_t_hgi_vmaddr_NE[0 +: 80])), .q(face_q_87));
    wire [511:0] face_q_87;
    assign o_t_hgi_vmaddr_NE[0 +: 80] = face_q_87[79:0];
    assign t_hgi_vmaddr_NE[79:0] = o_t_hgi_vmaddr_NE[79:0];
    wire [79:0] od_t_hgi_vmaddr_NW = {w_co_hgi_vmaddr[79:0]};
    wire [79:0] o_t_hgi_vmaddr_NW;
    ot_hbm_coll_face_pipe512 u_face_88 (.clk(face_clk[88]), .d(512'(od_t_hgi_vmaddr_NW[0 +: 80])), .q(face_q_88));
    wire [511:0] face_q_88;
    assign o_t_hgi_vmaddr_NW[0 +: 80] = face_q_88[79:0];
    assign t_hgi_vmaddr_NW[79:0] = o_t_hgi_vmaddr_NW[79:0];
    wire [79:0] od_t_hgi_vmaddr_SE = {w_co_hgi_vmaddr[79:0]};
    wire [79:0] o_t_hgi_vmaddr_SE;
    ot_hbm_coll_face_pipe512 u_face_89 (.clk(face_clk[89]), .d(512'(od_t_hgi_vmaddr_SE[0 +: 80])), .q(face_q_89));
    wire [511:0] face_q_89;
    assign o_t_hgi_vmaddr_SE[0 +: 80] = face_q_89[79:0];
    assign t_hgi_vmaddr_SE[79:0] = o_t_hgi_vmaddr_SE[79:0];
    wire [79:0] od_t_hgi_vmaddr_SW = {w_co_hgi_vmaddr[79:0]};
    wire [79:0] o_t_hgi_vmaddr_SW;
    ot_hbm_coll_face_pipe512 u_face_90 (.clk(face_clk[90]), .d(512'(od_t_hgi_vmaddr_SW[0 +: 80])), .q(face_q_90));
    wire [511:0] face_q_90;
    assign o_t_hgi_vmaddr_SW[0 +: 80] = face_q_90[79:0];
    assign t_hgi_vmaddr_SW[79:0] = o_t_hgi_vmaddr_SW[79:0];
    wire [337:0] od_t_hgi_vmq = {w_co_rgx_vmq[337:0]};
    wire [337:0] o_t_hgi_vmq;
    ot_hbm_coll_face_pipe512 u_face_91 (.clk(face_clk[91]), .d(512'(od_t_hgi_vmq[0 +: 338])), .q(face_q_91));
    wire [511:0] face_q_91;
    assign o_t_hgi_vmq[0 +: 338] = face_q_91[337:0];
    assign t_hgi_vmq[337:0] = o_t_hgi_vmq[337:0];
    wire [8960:0] od_t_hgi_vmw2 = {w_co_rgx_c_req[0:0], w_co_rgx_c_q[8959:0]};
    wire [8960:0] o_t_hgi_vmw2;
    ot_hbm_coll_face_pipe512 u_face_92 (.clk(face_clk[92]), .d(512'(od_t_hgi_vmw2[0 +: 512])), .q(face_q_92));
    wire [511:0] face_q_92;
    assign o_t_hgi_vmw2[0 +: 512] = face_q_92[511:0];
    ot_hbm_coll_face_pipe512 u_face_93 (.clk(face_clk[93]), .d(512'(od_t_hgi_vmw2[512 +: 512])), .q(face_q_93));
    wire [511:0] face_q_93;
    assign o_t_hgi_vmw2[512 +: 512] = face_q_93[511:0];
    ot_hbm_coll_face_pipe512 u_face_94 (.clk(face_clk[94]), .d(512'(od_t_hgi_vmw2[1024 +: 512])), .q(face_q_94));
    wire [511:0] face_q_94;
    assign o_t_hgi_vmw2[1024 +: 512] = face_q_94[511:0];
    ot_hbm_coll_face_pipe512 u_face_95 (.clk(face_clk[95]), .d(512'(od_t_hgi_vmw2[1536 +: 512])), .q(face_q_95));
    wire [511:0] face_q_95;
    assign o_t_hgi_vmw2[1536 +: 512] = face_q_95[511:0];
    ot_hbm_coll_face_pipe512 u_face_96 (.clk(face_clk[96]), .d(512'(od_t_hgi_vmw2[2048 +: 512])), .q(face_q_96));
    wire [511:0] face_q_96;
    assign o_t_hgi_vmw2[2048 +: 512] = face_q_96[511:0];
    ot_hbm_coll_face_pipe512 u_face_97 (.clk(face_clk[97]), .d(512'(od_t_hgi_vmw2[2560 +: 512])), .q(face_q_97));
    wire [511:0] face_q_97;
    assign o_t_hgi_vmw2[2560 +: 512] = face_q_97[511:0];
    ot_hbm_coll_face_pipe512 u_face_98 (.clk(face_clk[98]), .d(512'(od_t_hgi_vmw2[3072 +: 512])), .q(face_q_98));
    wire [511:0] face_q_98;
    assign o_t_hgi_vmw2[3072 +: 512] = face_q_98[511:0];
    ot_hbm_coll_face_pipe512 u_face_99 (.clk(face_clk[99]), .d(512'(od_t_hgi_vmw2[3584 +: 512])), .q(face_q_99));
    wire [511:0] face_q_99;
    assign o_t_hgi_vmw2[3584 +: 512] = face_q_99[511:0];
    ot_hbm_coll_face_pipe512 u_face_100 (.clk(face_clk[100]), .d(512'(od_t_hgi_vmw2[4096 +: 512])), .q(face_q_100));
    wire [511:0] face_q_100;
    assign o_t_hgi_vmw2[4096 +: 512] = face_q_100[511:0];
    ot_hbm_coll_face_pipe512 u_face_101 (.clk(face_clk[101]), .d(512'(od_t_hgi_vmw2[4608 +: 512])), .q(face_q_101));
    wire [511:0] face_q_101;
    assign o_t_hgi_vmw2[4608 +: 512] = face_q_101[511:0];
    ot_hbm_coll_face_pipe512 u_face_102 (.clk(face_clk[102]), .d(512'(od_t_hgi_vmw2[5120 +: 512])), .q(face_q_102));
    wire [511:0] face_q_102;
    assign o_t_hgi_vmw2[5120 +: 512] = face_q_102[511:0];
    ot_hbm_coll_face_pipe512 u_face_103 (.clk(face_clk[103]), .d(512'(od_t_hgi_vmw2[5632 +: 512])), .q(face_q_103));
    wire [511:0] face_q_103;
    assign o_t_hgi_vmw2[5632 +: 512] = face_q_103[511:0];
    ot_hbm_coll_face_pipe512 u_face_104 (.clk(face_clk[104]), .d(512'(od_t_hgi_vmw2[6144 +: 512])), .q(face_q_104));
    wire [511:0] face_q_104;
    assign o_t_hgi_vmw2[6144 +: 512] = face_q_104[511:0];
    ot_hbm_coll_face_pipe512 u_face_105 (.clk(face_clk[105]), .d(512'(od_t_hgi_vmw2[6656 +: 512])), .q(face_q_105));
    wire [511:0] face_q_105;
    assign o_t_hgi_vmw2[6656 +: 512] = face_q_105[511:0];
    ot_hbm_coll_face_pipe512 u_face_106 (.clk(face_clk[106]), .d(512'(od_t_hgi_vmw2[7168 +: 512])), .q(face_q_106));
    wire [511:0] face_q_106;
    assign o_t_hgi_vmw2[7168 +: 512] = face_q_106[511:0];
    ot_hbm_coll_face_pipe512 u_face_107 (.clk(face_clk[107]), .d(512'(od_t_hgi_vmw2[7680 +: 512])), .q(face_q_107));
    wire [511:0] face_q_107;
    assign o_t_hgi_vmw2[7680 +: 512] = face_q_107[511:0];
    ot_hbm_coll_face_pipe512 u_face_108 (.clk(face_clk[108]), .d(512'(od_t_hgi_vmw2[8192 +: 512])), .q(face_q_108));
    wire [511:0] face_q_108;
    assign o_t_hgi_vmw2[8192 +: 512] = face_q_108[511:0];
    ot_hbm_coll_face_pipe512 u_face_109 (.clk(face_clk[109]), .d(512'(od_t_hgi_vmw2[8704 +: 257])), .q(face_q_109));
    wire [511:0] face_q_109;
    assign o_t_hgi_vmw2[8704 +: 257] = face_q_109[256:0];
    assign t_hgi_vmw2[8960:0] = o_t_hgi_vmw2[8960:0];
    wire [0:0] od_t_mtp = {1'b1};
    wire [0:0] o_t_mtp;
    ot_hbm_coll_face_pipe512 u_face_110 (.clk(face_clk[110]), .d(512'(od_t_mtp[0 +: 1])), .q(face_q_110));
    wire [511:0] face_q_110;
    assign o_t_mtp[0 +: 1] = face_q_110[0:0];
    assign t_mtp[0:0] = o_t_mtp[0:0];
    wire [619:0] od_t_su_NE = {w_co_hgi_del_obase[159:120], w_co_inj_rd[1:0], w_co_inj_idx[31:0], w_co_del_valid[3:3], w_co_del_flit[2179:1635]};
    wire [619:0] o_t_su_NE;
    ot_hbm_coll_face_pipe512 u_face_111 (.clk(face_clk[111]), .d(512'(od_t_su_NE[0 +: 512])), .q(face_q_111));
    wire [511:0] face_q_111;
    assign o_t_su_NE[0 +: 512] = face_q_111[511:0];
    ot_hbm_coll_face_pipe512 u_face_112 (.clk(face_clk[112]), .d(512'(od_t_su_NE[512 +: 108])), .q(face_q_112));
    wire [511:0] face_q_112;
    assign o_t_su_NE[512 +: 108] = face_q_112[107:0];
    assign t_su_NE[619:0] = o_t_su_NE[619:0];
    wire [619:0] od_t_su_NW = {w_co_hgi_del_obase[79:40], w_co_inj_rd[1:0], w_co_inj_idx[31:0], w_co_del_valid[1:1], w_co_del_flit[1089:545]};
    wire [619:0] o_t_su_NW;
    ot_hbm_coll_face_pipe512 u_face_113 (.clk(face_clk[113]), .d(512'(od_t_su_NW[0 +: 512])), .q(face_q_113));
    wire [511:0] face_q_113;
    assign o_t_su_NW[0 +: 512] = face_q_113[511:0];
    ot_hbm_coll_face_pipe512 u_face_114 (.clk(face_clk[114]), .d(512'(od_t_su_NW[512 +: 108])), .q(face_q_114));
    wire [511:0] face_q_114;
    assign o_t_su_NW[512 +: 108] = face_q_114[107:0];
    assign t_su_NW[619:0] = o_t_su_NW[619:0];
    wire [619:0] od_t_su_SE = {w_co_hgi_del_obase[119:80], w_co_inj_rd[1:0], w_co_inj_idx[31:0], w_co_del_valid[2:2], w_co_del_flit[1634:1090]};
    wire [619:0] o_t_su_SE;
    ot_hbm_coll_face_pipe512 u_face_115 (.clk(face_clk[115]), .d(512'(od_t_su_SE[0 +: 512])), .q(face_q_115));
    wire [511:0] face_q_115;
    assign o_t_su_SE[0 +: 512] = face_q_115[511:0];
    ot_hbm_coll_face_pipe512 u_face_116 (.clk(face_clk[116]), .d(512'(od_t_su_SE[512 +: 108])), .q(face_q_116));
    wire [511:0] face_q_116;
    assign o_t_su_SE[512 +: 108] = face_q_116[107:0];
    assign t_su_SE[619:0] = o_t_su_SE[619:0];
    wire [619:0] od_t_su_SW = {w_co_hgi_del_obase[39:0], w_co_inj_rd[1:0], w_co_inj_idx[31:0], w_co_del_valid[0:0], w_co_del_flit[544:0]};
    wire [619:0] o_t_su_SW;
    ot_hbm_coll_face_pipe512 u_face_117 (.clk(face_clk[117]), .d(512'(od_t_su_SW[0 +: 512])), .q(face_q_117));
    wire [511:0] face_q_117;
    assign o_t_su_SW[0 +: 512] = face_q_117[511:0];
    ot_hbm_coll_face_pipe512 u_face_118 (.clk(face_clk[118]), .d(512'(od_t_su_SW[512 +: 108])), .q(face_q_118));
    wire [511:0] face_q_118;
    assign o_t_su_SW[512 +: 108] = face_q_118[107:0];
    assign t_su_SW[619:0] = o_t_su_SW[619:0];
endmodule
