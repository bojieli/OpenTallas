// hfd_coll: thin registered die wrapper (tools/hbm_die_wrap.py, CLAUDE HBM-ABSTRACTS spine).
// Die ports exactly as the r16g generator master (tools/hbm_die_views.py ports); default-off: nothing
// instantiates it except the die view route.  [link] 2026-10-10 R25GQ hfd_coll (one regeneration, lead): ot_hfd_coll_r25gq = ot_hgi_coll_ep NPT 9 (one port per hfd_lk_ep on llk_S0..S4, N0..N3: [0] tx_v [545:1] tx_flit [546] rx_credit out, [547] rx_v [1092:548] rx_flit [1093] sw_cr in, [1117:1094] session out, [1118] fault [1119] locked in, [1121:1120] chain fclk), SWCRED 32 (= lk_ep TXQ), RXAW 8 (slice 256-flit SRAM rb), PIPE 1, RGXHW 1, RFMT 0 + ot_hgi_coll_rgx_hbm / ot_hgi_coll_rgx_snk (hgi-1010/c, LQ 32) + LINK_SESSION cfg word 47.  vmw2 up {c_req [8960], c_q [8959:0]}, down {c_gnt [64], c_cr [63:32], c_rsp [31:0]} (hgi_die_dispatch: {c_req, lanes}, {c_gnt, credits, dones}).
module hfd_coll (
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
    wire clk = refclk;
    reg [1:0] rst_s; always @(posedge clk) rst_s <= {rst_s[0], por};
    wire rst_n = ~rst_s[1];
    reg [24:0] i0_f_cmdproc; always @(posedge clk) i0_f_cmdproc <= f_cmdproc;
    reg [24:0] i1_f_cmdproc; always @(posedge clk) i1_f_cmdproc <= i0_f_cmdproc;
    reg [24:0] i2_f_cmdproc; always @(posedge clk) i2_f_cmdproc <= i1_f_cmdproc;
    reg [24:0] i3_f_cmdproc; always @(posedge clk) i3_f_cmdproc <= i2_f_cmdproc;
    reg [24:0] i_f_cmdproc; always @(posedge clk) i_f_cmdproc <= i3_f_cmdproc;
    reg [39:0] i0_f_hgi_cfg; always @(posedge clk) i0_f_hgi_cfg <= f_hgi_cfg;
    reg [39:0] i1_f_hgi_cfg; always @(posedge clk) i1_f_hgi_cfg <= i0_f_hgi_cfg;
    reg [39:0] i2_f_hgi_cfg; always @(posedge clk) i2_f_hgi_cfg <= i1_f_hgi_cfg;
    reg [39:0] i3_f_hgi_cfg; always @(posedge clk) i3_f_hgi_cfg <= i2_f_hgi_cfg;
    reg [39:0] i_f_hgi_cfg; always @(posedge clk) i_f_hgi_cfg <= i3_f_hgi_cfg;
    reg [967:0] i0_f_hgi_cmdproc; always @(posedge clk) i0_f_hgi_cmdproc <= f_hgi_cmdproc;
    reg [967:0] i1_f_hgi_cmdproc; always @(posedge clk) i1_f_hgi_cmdproc <= i0_f_hgi_cmdproc;
    reg [967:0] i2_f_hgi_cmdproc; always @(posedge clk) i2_f_hgi_cmdproc <= i1_f_hgi_cmdproc;
    reg [967:0] i3_f_hgi_cmdproc; always @(posedge clk) i3_f_hgi_cmdproc <= i2_f_hgi_cmdproc;
    reg [967:0] i_f_hgi_cmdproc; always @(posedge clk) i_f_hgi_cmdproc <= i3_f_hgi_cmdproc;
    reg [0:0] i0_f_hgi_rgxa0; always @(posedge clk) i0_f_hgi_rgxa0 <= f_hgi_rgxa0;
    reg [0:0] i1_f_hgi_rgxa0; always @(posedge clk) i1_f_hgi_rgxa0 <= i0_f_hgi_rgxa0;
    reg [0:0] i2_f_hgi_rgxa0; always @(posedge clk) i2_f_hgi_rgxa0 <= i1_f_hgi_rgxa0;
    reg [0:0] i3_f_hgi_rgxa0; always @(posedge clk) i3_f_hgi_rgxa0 <= i2_f_hgi_rgxa0;
    reg [0:0] i_f_hgi_rgxa0; always @(posedge clk) i_f_hgi_rgxa0 <= i3_f_hgi_rgxa0;
    reg [0:0] i0_f_hgi_rgxa1; always @(posedge clk) i0_f_hgi_rgxa1 <= f_hgi_rgxa1;
    reg [0:0] i1_f_hgi_rgxa1; always @(posedge clk) i1_f_hgi_rgxa1 <= i0_f_hgi_rgxa1;
    reg [0:0] i2_f_hgi_rgxa1; always @(posedge clk) i2_f_hgi_rgxa1 <= i1_f_hgi_rgxa1;
    reg [0:0] i3_f_hgi_rgxa1; always @(posedge clk) i3_f_hgi_rgxa1 <= i2_f_hgi_rgxa1;
    reg [0:0] i_f_hgi_rgxa1; always @(posedge clk) i_f_hgi_rgxa1 <= i3_f_hgi_rgxa1;
    reg [256:0] i0_f_hgi_rgxr0; always @(posedge clk) i0_f_hgi_rgxr0 <= f_hgi_rgxr0;
    reg [256:0] i1_f_hgi_rgxr0; always @(posedge clk) i1_f_hgi_rgxr0 <= i0_f_hgi_rgxr0;
    reg [256:0] i2_f_hgi_rgxr0; always @(posedge clk) i2_f_hgi_rgxr0 <= i1_f_hgi_rgxr0;
    reg [256:0] i3_f_hgi_rgxr0; always @(posedge clk) i3_f_hgi_rgxr0 <= i2_f_hgi_rgxr0;
    reg [256:0] i_f_hgi_rgxr0; always @(posedge clk) i_f_hgi_rgxr0 <= i3_f_hgi_rgxr0;
    reg [256:0] i0_f_hgi_rgxr1; always @(posedge clk) i0_f_hgi_rgxr1 <= f_hgi_rgxr1;
    reg [256:0] i1_f_hgi_rgxr1; always @(posedge clk) i1_f_hgi_rgxr1 <= i0_f_hgi_rgxr1;
    reg [256:0] i2_f_hgi_rgxr1; always @(posedge clk) i2_f_hgi_rgxr1 <= i1_f_hgi_rgxr1;
    reg [256:0] i3_f_hgi_rgxr1; always @(posedge clk) i3_f_hgi_rgxr1 <= i2_f_hgi_rgxr1;
    reg [256:0] i_f_hgi_rgxr1; always @(posedge clk) i_f_hgi_rgxr1 <= i3_f_hgi_rgxr1;
    reg [273:0] i0_f_hgi_vmr; always @(posedge clk) i0_f_hgi_vmr <= f_hgi_vmr;
    reg [273:0] i1_f_hgi_vmr; always @(posedge clk) i1_f_hgi_vmr <= i0_f_hgi_vmr;
    reg [273:0] i2_f_hgi_vmr; always @(posedge clk) i2_f_hgi_vmr <= i1_f_hgi_vmr;
    reg [273:0] i3_f_hgi_vmr; always @(posedge clk) i3_f_hgi_vmr <= i2_f_hgi_vmr;
    reg [273:0] i_f_hgi_vmr; always @(posedge clk) i_f_hgi_vmr <= i3_f_hgi_vmr;
    reg [64:0] i0_f_hgi_vmw2; always @(posedge clk) i0_f_hgi_vmw2 <= f_hgi_vmw2;
    reg [64:0] i1_f_hgi_vmw2; always @(posedge clk) i1_f_hgi_vmw2 <= i0_f_hgi_vmw2;
    reg [64:0] i2_f_hgi_vmw2; always @(posedge clk) i2_f_hgi_vmw2 <= i1_f_hgi_vmw2;
    reg [64:0] i3_f_hgi_vmw2; always @(posedge clk) i3_f_hgi_vmw2 <= i2_f_hgi_vmw2;
    reg [64:0] i_f_hgi_vmw2; always @(posedge clk) i_f_hgi_vmw2 <= i3_f_hgi_vmw2;
    reg [18:0] i0_f_mtp; always @(posedge clk) i0_f_mtp <= f_mtp;
    reg [18:0] i1_f_mtp; always @(posedge clk) i1_f_mtp <= i0_f_mtp;
    reg [18:0] i2_f_mtp; always @(posedge clk) i2_f_mtp <= i1_f_mtp;
    reg [18:0] i3_f_mtp; always @(posedge clk) i3_f_mtp <= i2_f_mtp;
    reg [18:0] i_f_mtp; always @(posedge clk) i_f_mtp <= i3_f_mtp;
    reg [1023:0] i0_f_su_NE; always @(posedge clk) i0_f_su_NE <= f_su_NE;
    reg [1023:0] i1_f_su_NE; always @(posedge clk) i1_f_su_NE <= i0_f_su_NE;
    reg [1023:0] i2_f_su_NE; always @(posedge clk) i2_f_su_NE <= i1_f_su_NE;
    reg [1023:0] i3_f_su_NE; always @(posedge clk) i3_f_su_NE <= i2_f_su_NE;
    reg [1023:0] i_f_su_NE; always @(posedge clk) i_f_su_NE <= i3_f_su_NE;
    reg [1023:0] i0_f_su_NW; always @(posedge clk) i0_f_su_NW <= f_su_NW;
    reg [1023:0] i1_f_su_NW; always @(posedge clk) i1_f_su_NW <= i0_f_su_NW;
    reg [1023:0] i2_f_su_NW; always @(posedge clk) i2_f_su_NW <= i1_f_su_NW;
    reg [1023:0] i3_f_su_NW; always @(posedge clk) i3_f_su_NW <= i2_f_su_NW;
    reg [1023:0] i_f_su_NW; always @(posedge clk) i_f_su_NW <= i3_f_su_NW;
    reg [1023:0] i0_f_su_SE; always @(posedge clk) i0_f_su_SE <= f_su_SE;
    reg [1023:0] i1_f_su_SE; always @(posedge clk) i1_f_su_SE <= i0_f_su_SE;
    reg [1023:0] i2_f_su_SE; always @(posedge clk) i2_f_su_SE <= i1_f_su_SE;
    reg [1023:0] i3_f_su_SE; always @(posedge clk) i3_f_su_SE <= i2_f_su_SE;
    reg [1023:0] i_f_su_SE; always @(posedge clk) i_f_su_SE <= i3_f_su_SE;
    reg [1023:0] i0_f_su_SW; always @(posedge clk) i0_f_su_SW <= f_su_SW;
    reg [1023:0] i1_f_su_SW; always @(posedge clk) i1_f_su_SW <= i0_f_su_SW;
    reg [1023:0] i2_f_su_SW; always @(posedge clk) i2_f_su_SW <= i1_f_su_SW;
    reg [1023:0] i3_f_su_SW; always @(posedge clk) i3_f_su_SW <= i2_f_su_SW;
    reg [1023:0] i_f_su_SW; always @(posedge clk) i_f_su_SW <= i3_f_su_SW;
    reg [1121:0] i0_llk_N0; always @(posedge clk) i0_llk_N0 <= llk_N0;
    reg [1121:0] i1_llk_N0; always @(posedge clk) i1_llk_N0 <= i0_llk_N0;
    reg [1121:0] i2_llk_N0; always @(posedge clk) i2_llk_N0 <= i1_llk_N0;
    reg [1121:0] i3_llk_N0; always @(posedge clk) i3_llk_N0 <= i2_llk_N0;
    reg [1121:0] i_llk_N0; always @(posedge clk) i_llk_N0 <= i3_llk_N0;
    reg [1121:0] i0_llk_N1; always @(posedge clk) i0_llk_N1 <= llk_N1;
    reg [1121:0] i1_llk_N1; always @(posedge clk) i1_llk_N1 <= i0_llk_N1;
    reg [1121:0] i2_llk_N1; always @(posedge clk) i2_llk_N1 <= i1_llk_N1;
    reg [1121:0] i3_llk_N1; always @(posedge clk) i3_llk_N1 <= i2_llk_N1;
    reg [1121:0] i_llk_N1; always @(posedge clk) i_llk_N1 <= i3_llk_N1;
    reg [1121:0] i0_llk_N2; always @(posedge clk) i0_llk_N2 <= llk_N2;
    reg [1121:0] i1_llk_N2; always @(posedge clk) i1_llk_N2 <= i0_llk_N2;
    reg [1121:0] i2_llk_N2; always @(posedge clk) i2_llk_N2 <= i1_llk_N2;
    reg [1121:0] i3_llk_N2; always @(posedge clk) i3_llk_N2 <= i2_llk_N2;
    reg [1121:0] i_llk_N2; always @(posedge clk) i_llk_N2 <= i3_llk_N2;
    reg [1121:0] i0_llk_N3; always @(posedge clk) i0_llk_N3 <= llk_N3;
    reg [1121:0] i1_llk_N3; always @(posedge clk) i1_llk_N3 <= i0_llk_N3;
    reg [1121:0] i2_llk_N3; always @(posedge clk) i2_llk_N3 <= i1_llk_N3;
    reg [1121:0] i3_llk_N3; always @(posedge clk) i3_llk_N3 <= i2_llk_N3;
    reg [1121:0] i_llk_N3; always @(posedge clk) i_llk_N3 <= i3_llk_N3;
    reg [1121:0] i0_llk_S0; always @(posedge clk) i0_llk_S0 <= llk_S0;
    reg [1121:0] i1_llk_S0; always @(posedge clk) i1_llk_S0 <= i0_llk_S0;
    reg [1121:0] i2_llk_S0; always @(posedge clk) i2_llk_S0 <= i1_llk_S0;
    reg [1121:0] i3_llk_S0; always @(posedge clk) i3_llk_S0 <= i2_llk_S0;
    reg [1121:0] i_llk_S0; always @(posedge clk) i_llk_S0 <= i3_llk_S0;
    reg [1121:0] i0_llk_S1; always @(posedge clk) i0_llk_S1 <= llk_S1;
    reg [1121:0] i1_llk_S1; always @(posedge clk) i1_llk_S1 <= i0_llk_S1;
    reg [1121:0] i2_llk_S1; always @(posedge clk) i2_llk_S1 <= i1_llk_S1;
    reg [1121:0] i3_llk_S1; always @(posedge clk) i3_llk_S1 <= i2_llk_S1;
    reg [1121:0] i_llk_S1; always @(posedge clk) i_llk_S1 <= i3_llk_S1;
    reg [1121:0] i0_llk_S2; always @(posedge clk) i0_llk_S2 <= llk_S2;
    reg [1121:0] i1_llk_S2; always @(posedge clk) i1_llk_S2 <= i0_llk_S2;
    reg [1121:0] i2_llk_S2; always @(posedge clk) i2_llk_S2 <= i1_llk_S2;
    reg [1121:0] i3_llk_S2; always @(posedge clk) i3_llk_S2 <= i2_llk_S2;
    reg [1121:0] i_llk_S2; always @(posedge clk) i_llk_S2 <= i3_llk_S2;
    reg [1121:0] i0_llk_S3; always @(posedge clk) i0_llk_S3 <= llk_S3;
    reg [1121:0] i1_llk_S3; always @(posedge clk) i1_llk_S3 <= i0_llk_S3;
    reg [1121:0] i2_llk_S3; always @(posedge clk) i2_llk_S3 <= i1_llk_S3;
    reg [1121:0] i3_llk_S3; always @(posedge clk) i3_llk_S3 <= i2_llk_S3;
    reg [1121:0] i_llk_S3; always @(posedge clk) i_llk_S3 <= i3_llk_S3;
    reg [1121:0] i0_llk_S4; always @(posedge clk) i0_llk_S4 <= llk_S4;
    reg [1121:0] i1_llk_S4; always @(posedge clk) i1_llk_S4 <= i0_llk_S4;
    reg [1121:0] i2_llk_S4; always @(posedge clk) i2_llk_S4 <= i1_llk_S4;
    reg [1121:0] i3_llk_S4; always @(posedge clk) i3_llk_S4 <= i2_llk_S4;
    reg [1121:0] i_llk_S4; always @(posedge clk) i_llk_S4 <= i3_llk_S4;
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
    ot_hfd_coll_r25gq u_co (.clk(w_co_clk), .rst_n(w_co_rst_n), .rank(w_co_rank), .pf(w_co_pf), .go(w_co_go), .inj_idx(w_co_inj_idx), .inj_rd(w_co_inj_rd), .inj_q(w_co_inj_q), .del_valid(w_co_del_valid), .del_flit(w_co_del_flit), .fault(w_co_fault), .stat_credit_stall(w_co_stat_credit_stall), .hgi_rec(w_co_hgi_rec), .hgi_ret(w_co_hgi_ret), .hgi_cfg(w_co_hgi_cfg), .hgi_rowfmt_o(w_co_hgi_rowfmt_o), .hgi_rowfmt_i(w_co_hgi_rowfmt_i), .hgi_vmaddr(w_co_hgi_vmaddr), .hgi_del_obase(w_co_hgi_del_obase), .lk_tx_v(w_co_lk_tx_v), .lk_tx_flit(w_co_lk_tx_flit), .lk_rx_credit(w_co_lk_rx_credit), .lk_rx_v(w_co_lk_rx_v), .lk_rx_flit(w_co_lk_rx_flit), .lk_sw_cr(w_co_lk_sw_cr), .lk_session(w_co_lk_session), .lk_fault(w_co_lk_fault), .lk_locked(w_co_lk_locked), .lk_status(w_co_lk_status), .rgx_xq(w_co_rgx_xq), .rgx_xr(w_co_rgx_xr), .rgx_vmq(w_co_rgx_vmq), .rgx_vmr(w_co_rgx_vmr), .rgx_c_req(w_co_rgx_c_req), .rgx_c_gnt(w_co_rgx_c_gnt), .rgx_c_q(w_co_rgx_c_q), .rgx_c_cr(w_co_rgx_c_cr), .rgx_c_rsp(w_co_rgx_c_rsp), .rgx_xw(w_co_rgx_xw), .rgx_xwa(w_co_rgx_xwa));
    for (genvar k = 0; k < 94; k = k + 1) begin : g_sink_w_co_hgi_rowfmt_o
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_co_hgi_rowfmt_o[k]), .q());
    end
    for (genvar k = 0; k < 18; k = k + 1) begin : g_sink_w_co_lk_status
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_co_lk_status[k]), .q());
    end
    wire fclk_0; ot_fwd_clk_inv u_fclk_0 (.a(clk), .y(fclk_0));
    wire fclk_1; ot_fwd_clk_inv u_fclk_1 (.a(clk), .y(fclk_1));
    wire fclk_2; ot_fwd_clk_inv u_fclk_2 (.a(clk), .y(fclk_2));
    wire fclk_3; ot_fwd_clk_inv u_fclk_3 (.a(clk), .y(fclk_3));
    wire [1121:0] od_llk_N0 = {1'd0, clk, 2'd0, w_co_lk_session[143:120], 547'd0, w_co_lk_rx_credit[5:5], w_co_lk_tx_flit[3269:2725], w_co_lk_tx_v[5:5]};
    wire [1121:0] o_llk_N0;
    for (genvar k = 0; k < 1122; k = k + 1) begin : g_o_llk_N0
        ot_hfd_oreg5 u (.clk(clk), .d(od_llk_N0[k]), .q(o_llk_N0[k]));
    end
    assign llk_N0[546:0] = o_llk_N0[546:0];
    assign llk_N0[1117:1094] = o_llk_N0[1117:1094];
    assign llk_N0[1120:1120] = o_llk_N0[1120:1120];
    wire [1121:0] od_llk_N1 = {1'd0, clk, 2'd0, w_co_lk_session[167:144], 547'd0, w_co_lk_rx_credit[6:6], w_co_lk_tx_flit[3814:3270], w_co_lk_tx_v[6:6]};
    wire [1121:0] o_llk_N1;
    for (genvar k = 0; k < 1122; k = k + 1) begin : g_o_llk_N1
        ot_hfd_oreg5 u (.clk(clk), .d(od_llk_N1[k]), .q(o_llk_N1[k]));
    end
    assign llk_N1[546:0] = o_llk_N1[546:0];
    assign llk_N1[1117:1094] = o_llk_N1[1117:1094];
    assign llk_N1[1120:1120] = o_llk_N1[1120:1120];
    wire [1121:0] od_llk_N2 = {1'd0, clk, 2'd0, w_co_lk_session[191:168], 547'd0, w_co_lk_rx_credit[7:7], w_co_lk_tx_flit[4359:3815], w_co_lk_tx_v[7:7]};
    wire [1121:0] o_llk_N2;
    for (genvar k = 0; k < 1122; k = k + 1) begin : g_o_llk_N2
        ot_hfd_oreg5 u (.clk(clk), .d(od_llk_N2[k]), .q(o_llk_N2[k]));
    end
    assign llk_N2[546:0] = o_llk_N2[546:0];
    assign llk_N2[1117:1094] = o_llk_N2[1117:1094];
    assign llk_N2[1120:1120] = o_llk_N2[1120:1120];
    wire [1121:0] od_llk_N3 = {1'd0, clk, 2'd0, w_co_lk_session[215:192], 547'd0, w_co_lk_rx_credit[8:8], w_co_lk_tx_flit[4904:4360], w_co_lk_tx_v[8:8]};
    wire [1121:0] o_llk_N3;
    for (genvar k = 0; k < 1122; k = k + 1) begin : g_o_llk_N3
        ot_hfd_oreg5 u (.clk(clk), .d(od_llk_N3[k]), .q(o_llk_N3[k]));
    end
    assign llk_N3[546:0] = o_llk_N3[546:0];
    assign llk_N3[1117:1094] = o_llk_N3[1117:1094];
    assign llk_N3[1120:1120] = o_llk_N3[1120:1120];
    wire [1121:0] od_llk_S0 = {1'd0, clk, 2'd0, w_co_lk_session[23:0], 547'd0, w_co_lk_rx_credit[0:0], w_co_lk_tx_flit[544:0], w_co_lk_tx_v[0:0]};
    wire [1121:0] o_llk_S0;
    for (genvar k = 0; k < 1122; k = k + 1) begin : g_o_llk_S0
        ot_hfd_oreg5 u (.clk(clk), .d(od_llk_S0[k]), .q(o_llk_S0[k]));
    end
    assign llk_S0[546:0] = o_llk_S0[546:0];
    assign llk_S0[1117:1094] = o_llk_S0[1117:1094];
    assign llk_S0[1120:1120] = o_llk_S0[1120:1120];
    wire [1121:0] od_llk_S1 = {1'd0, clk, 2'd0, w_co_lk_session[47:24], 547'd0, w_co_lk_rx_credit[1:1], w_co_lk_tx_flit[1089:545], w_co_lk_tx_v[1:1]};
    wire [1121:0] o_llk_S1;
    for (genvar k = 0; k < 1122; k = k + 1) begin : g_o_llk_S1
        ot_hfd_oreg5 u (.clk(clk), .d(od_llk_S1[k]), .q(o_llk_S1[k]));
    end
    assign llk_S1[546:0] = o_llk_S1[546:0];
    assign llk_S1[1117:1094] = o_llk_S1[1117:1094];
    assign llk_S1[1120:1120] = o_llk_S1[1120:1120];
    wire [1121:0] od_llk_S2 = {1'd0, clk, 2'd0, w_co_lk_session[71:48], 547'd0, w_co_lk_rx_credit[2:2], w_co_lk_tx_flit[1634:1090], w_co_lk_tx_v[2:2]};
    wire [1121:0] o_llk_S2;
    for (genvar k = 0; k < 1122; k = k + 1) begin : g_o_llk_S2
        ot_hfd_oreg5 u (.clk(clk), .d(od_llk_S2[k]), .q(o_llk_S2[k]));
    end
    assign llk_S2[546:0] = o_llk_S2[546:0];
    assign llk_S2[1117:1094] = o_llk_S2[1117:1094];
    assign llk_S2[1120:1120] = o_llk_S2[1120:1120];
    wire [1121:0] od_llk_S3 = {1'd0, clk, 2'd0, w_co_lk_session[95:72], 547'd0, w_co_lk_rx_credit[3:3], w_co_lk_tx_flit[2179:1635], w_co_lk_tx_v[3:3]};
    wire [1121:0] o_llk_S3;
    for (genvar k = 0; k < 1122; k = k + 1) begin : g_o_llk_S3
        ot_hfd_oreg5 u (.clk(clk), .d(od_llk_S3[k]), .q(o_llk_S3[k]));
    end
    assign llk_S3[546:0] = o_llk_S3[546:0];
    assign llk_S3[1117:1094] = o_llk_S3[1117:1094];
    assign llk_S3[1120:1120] = o_llk_S3[1120:1120];
    wire [1121:0] od_llk_S4 = {1'd0, clk, 2'd0, w_co_lk_session[119:96], 547'd0, w_co_lk_rx_credit[4:4], w_co_lk_tx_flit[2724:2180], w_co_lk_tx_v[4:4]};
    wire [1121:0] o_llk_S4;
    for (genvar k = 0; k < 1122; k = k + 1) begin : g_o_llk_S4
        ot_hfd_oreg5 u (.clk(clk), .d(od_llk_S4[k]), .q(o_llk_S4[k]));
    end
    assign llk_S4[546:0] = o_llk_S4[546:0];
    assign llk_S4[1117:1094] = o_llk_S4[1117:1094];
    assign llk_S4[1120:1120] = o_llk_S4[1120:1120];
    wire [0:0] od_pll_hbm = {1'd0};
    wire [0:0] o_pll_hbm;
    for (genvar k = 0; k < 1; k = k + 1) begin : g_o_pll_hbm
        ot_hfd_oreg5 u (.clk(clk), .d(od_pll_hbm[k]), .q(o_pll_hbm[k]));
    end
    assign pll_hbm[0] = fclk_0;
    wire [0:0] od_pll_link = {1'd0};
    wire [0:0] o_pll_link;
    for (genvar k = 0; k < 1; k = k + 1) begin : g_o_pll_link
        ot_hfd_oreg5 u (.clk(clk), .d(od_pll_link[k]), .q(o_pll_link[k]));
    end
    assign pll_link[0] = fclk_1;
    wire [0:0] od_pll_serial = {1'd0};
    wire [0:0] o_pll_serial;
    for (genvar k = 0; k < 1; k = k + 1) begin : g_o_pll_serial
        ot_hfd_oreg5 u (.clk(clk), .d(od_pll_serial[k]), .q(o_pll_serial[k]));
    end
    assign pll_serial[0] = fclk_2;
    wire [0:0] od_pll_stream = {1'd0};
    wire [0:0] o_pll_stream;
    for (genvar k = 0; k < 1; k = k + 1) begin : g_o_pll_stream
        ot_hfd_oreg5 u (.clk(clk), .d(od_pll_stream[k]), .q(o_pll_stream[k]));
    end
    assign pll_stream[0] = fclk_3;
    wire [0:0] od_por_hbm = {rst_s[1]};
    wire [0:0] o_por_hbm;
    for (genvar k = 0; k < 1; k = k + 1) begin : g_o_por_hbm
        ot_hfd_oreg5 u (.clk(clk), .d(od_por_hbm[k]), .q(o_por_hbm[k]));
    end
    assign por_hbm[0:0] = o_por_hbm[0:0];
    wire [0:0] od_por_link = {rst_s[1]};
    wire [0:0] o_por_link;
    for (genvar k = 0; k < 1; k = k + 1) begin : g_o_por_link
        ot_hfd_oreg5 u (.clk(clk), .d(od_por_link[k]), .q(o_por_link[k]));
    end
    assign por_link[0:0] = o_por_link[0:0];
    wire [0:0] od_por_serial = {rst_s[1]};
    wire [0:0] o_por_serial;
    for (genvar k = 0; k < 1; k = k + 1) begin : g_o_por_serial
        ot_hfd_oreg5 u (.clk(clk), .d(od_por_serial[k]), .q(o_por_serial[k]));
    end
    assign por_serial[0:0] = o_por_serial[0:0];
    wire [0:0] od_por_stream = {rst_s[1]};
    wire [0:0] o_por_stream;
    for (genvar k = 0; k < 1; k = k + 1) begin : g_o_por_stream
        ot_hfd_oreg5 u (.clk(clk), .d(od_por_stream[k]), .q(o_por_stream[k]));
    end
    assign por_stream[0:0] = o_por_stream[0:0];
    wire [32:0] od_t_cmdproc = {w_co_stat_credit_stall[31:0], w_co_fault[0:0]};
    wire [32:0] o_t_cmdproc;
    for (genvar k = 0; k < 33; k = k + 1) begin : g_o_t_cmdproc
        ot_hfd_oreg5 u (.clk(clk), .d(od_t_cmdproc[k]), .q(o_t_cmdproc[k]));
    end
    assign t_cmdproc[32:0] = o_t_cmdproc[32:0];
    wire [2:0] od_t_hgi_cmdproc = {w_co_hgi_ret[2:0]};
    wire [2:0] o_t_hgi_cmdproc;
    for (genvar k = 0; k < 3; k = k + 1) begin : g_o_t_hgi_cmdproc
        ot_hfd_oreg5 u (.clk(clk), .d(od_t_hgi_cmdproc[k]), .q(o_t_hgi_cmdproc[k]));
    end
    assign t_hgi_cmdproc[2:0] = o_t_hgi_cmdproc[2:0];
    wire [37:0] od_t_hgi_rgxq0 = {w_co_rgx_xq[37:0]};
    wire [37:0] o_t_hgi_rgxq0;
    for (genvar k = 0; k < 38; k = k + 1) begin : g_o_t_hgi_rgxq0
        ot_hfd_oreg5 u (.clk(clk), .d(od_t_hgi_rgxq0[k]), .q(o_t_hgi_rgxq0[k]));
    end
    assign t_hgi_rgxq0[37:0] = o_t_hgi_rgxq0[37:0];
    wire [37:0] od_t_hgi_rgxq1 = {w_co_rgx_xq[75:38]};
    wire [37:0] o_t_hgi_rgxq1;
    for (genvar k = 0; k < 38; k = k + 1) begin : g_o_t_hgi_rgxq1
        ot_hfd_oreg5 u (.clk(clk), .d(od_t_hgi_rgxq1[k]), .q(o_t_hgi_rgxq1[k]));
    end
    assign t_hgi_rgxq1[37:0] = o_t_hgi_rgxq1[37:0];
    wire [325:0] od_t_hgi_rgxw0 = {w_co_rgx_xw[325:0]};
    wire [325:0] o_t_hgi_rgxw0;
    for (genvar k = 0; k < 326; k = k + 1) begin : g_o_t_hgi_rgxw0
        ot_hfd_oreg5 u (.clk(clk), .d(od_t_hgi_rgxw0[k]), .q(o_t_hgi_rgxw0[k]));
    end
    assign t_hgi_rgxw0[325:0] = o_t_hgi_rgxw0[325:0];
    wire [325:0] od_t_hgi_rgxw1 = {w_co_rgx_xw[651:326]};
    wire [325:0] o_t_hgi_rgxw1;
    for (genvar k = 0; k < 326; k = k + 1) begin : g_o_t_hgi_rgxw1
        ot_hfd_oreg5 u (.clk(clk), .d(od_t_hgi_rgxw1[k]), .q(o_t_hgi_rgxw1[k]));
    end
    assign t_hgi_rgxw1[325:0] = o_t_hgi_rgxw1[325:0];
    wire [79:0] od_t_hgi_vmaddr_NE = {w_co_hgi_vmaddr[79:0]};
    wire [79:0] o_t_hgi_vmaddr_NE;
    for (genvar k = 0; k < 80; k = k + 1) begin : g_o_t_hgi_vmaddr_NE
        ot_hfd_oreg5 u (.clk(clk), .d(od_t_hgi_vmaddr_NE[k]), .q(o_t_hgi_vmaddr_NE[k]));
    end
    assign t_hgi_vmaddr_NE[79:0] = o_t_hgi_vmaddr_NE[79:0];
    wire [79:0] od_t_hgi_vmaddr_NW = {w_co_hgi_vmaddr[79:0]};
    wire [79:0] o_t_hgi_vmaddr_NW;
    for (genvar k = 0; k < 80; k = k + 1) begin : g_o_t_hgi_vmaddr_NW
        ot_hfd_oreg5 u (.clk(clk), .d(od_t_hgi_vmaddr_NW[k]), .q(o_t_hgi_vmaddr_NW[k]));
    end
    assign t_hgi_vmaddr_NW[79:0] = o_t_hgi_vmaddr_NW[79:0];
    wire [79:0] od_t_hgi_vmaddr_SE = {w_co_hgi_vmaddr[79:0]};
    wire [79:0] o_t_hgi_vmaddr_SE;
    for (genvar k = 0; k < 80; k = k + 1) begin : g_o_t_hgi_vmaddr_SE
        ot_hfd_oreg5 u (.clk(clk), .d(od_t_hgi_vmaddr_SE[k]), .q(o_t_hgi_vmaddr_SE[k]));
    end
    assign t_hgi_vmaddr_SE[79:0] = o_t_hgi_vmaddr_SE[79:0];
    wire [79:0] od_t_hgi_vmaddr_SW = {w_co_hgi_vmaddr[79:0]};
    wire [79:0] o_t_hgi_vmaddr_SW;
    for (genvar k = 0; k < 80; k = k + 1) begin : g_o_t_hgi_vmaddr_SW
        ot_hfd_oreg5 u (.clk(clk), .d(od_t_hgi_vmaddr_SW[k]), .q(o_t_hgi_vmaddr_SW[k]));
    end
    assign t_hgi_vmaddr_SW[79:0] = o_t_hgi_vmaddr_SW[79:0];
    wire [337:0] od_t_hgi_vmq = {w_co_rgx_vmq[337:0]};
    wire [337:0] o_t_hgi_vmq;
    for (genvar k = 0; k < 338; k = k + 1) begin : g_o_t_hgi_vmq
        ot_hfd_oreg5 u (.clk(clk), .d(od_t_hgi_vmq[k]), .q(o_t_hgi_vmq[k]));
    end
    assign t_hgi_vmq[337:0] = o_t_hgi_vmq[337:0];
    wire [8960:0] od_t_hgi_vmw2 = {w_co_rgx_c_req[0:0], w_co_rgx_c_q[8959:0]};
    wire [8960:0] o_t_hgi_vmw2;
    for (genvar k = 0; k < 8961; k = k + 1) begin : g_o_t_hgi_vmw2
        ot_hfd_oreg5 u (.clk(clk), .d(od_t_hgi_vmw2[k]), .q(o_t_hgi_vmw2[k]));
    end
    assign t_hgi_vmw2[8960:0] = o_t_hgi_vmw2[8960:0];
    wire [0:0] od_t_mtp = {1'b1};
    wire [0:0] o_t_mtp;
    for (genvar k = 0; k < 1; k = k + 1) begin : g_o_t_mtp
        ot_hfd_oreg5 u (.clk(clk), .d(od_t_mtp[k]), .q(o_t_mtp[k]));
    end
    assign t_mtp[0:0] = o_t_mtp[0:0];
    wire [619:0] od_t_su_NE = {w_co_hgi_del_obase[159:120], w_co_inj_rd[1:0], w_co_inj_idx[31:0], w_co_del_valid[3:3], w_co_del_flit[2179:1635]};
    wire [619:0] o_t_su_NE;
    for (genvar k = 0; k < 620; k = k + 1) begin : g_o_t_su_NE
        ot_hfd_oreg5 u (.clk(clk), .d(od_t_su_NE[k]), .q(o_t_su_NE[k]));
    end
    assign t_su_NE[619:0] = o_t_su_NE[619:0];
    wire [619:0] od_t_su_NW = {w_co_hgi_del_obase[79:40], w_co_inj_rd[1:0], w_co_inj_idx[31:0], w_co_del_valid[1:1], w_co_del_flit[1089:545]};
    wire [619:0] o_t_su_NW;
    for (genvar k = 0; k < 620; k = k + 1) begin : g_o_t_su_NW
        ot_hfd_oreg5 u (.clk(clk), .d(od_t_su_NW[k]), .q(o_t_su_NW[k]));
    end
    assign t_su_NW[619:0] = o_t_su_NW[619:0];
    wire [619:0] od_t_su_SE = {w_co_hgi_del_obase[119:80], w_co_inj_rd[1:0], w_co_inj_idx[31:0], w_co_del_valid[2:2], w_co_del_flit[1634:1090]};
    wire [619:0] o_t_su_SE;
    for (genvar k = 0; k < 620; k = k + 1) begin : g_o_t_su_SE
        ot_hfd_oreg5 u (.clk(clk), .d(od_t_su_SE[k]), .q(o_t_su_SE[k]));
    end
    assign t_su_SE[619:0] = o_t_su_SE[619:0];
    wire [619:0] od_t_su_SW = {w_co_hgi_del_obase[39:0], w_co_inj_rd[1:0], w_co_inj_idx[31:0], w_co_del_valid[0:0], w_co_del_flit[544:0]};
    wire [619:0] o_t_su_SW;
    for (genvar k = 0; k < 620; k = k + 1) begin : g_o_t_su_SW
        ot_hfd_oreg5 u (.clk(clk), .d(od_t_su_SW[k]), .q(o_t_su_SW[k]));
    end
    assign t_su_SW[619:0] = o_t_su_SW[619:0];
endmodule
