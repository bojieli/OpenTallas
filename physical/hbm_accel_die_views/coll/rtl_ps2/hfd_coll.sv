// hfd_coll, rtl_ps2 (stream coll-fallback, 2026-10-08): the rtl/hfd_coll.sv die wrapper with the endpoint replaced by
// ot_hbm_accel_tu_endpoint_ps2: 4 x ot_hcoll_port2 hard pair slices (two ports a slice, 36 SRAM macros each, hardened
// once) + the core (hub lines, slots, 112-adder tree, delivery, 8 K=8 landing heads, 21 SRAM macros).  pclk = clk.
// Every non-comment line equals rtl/hfd_coll.sv except the endpoint instance line (rtl_sr/run_sr_bench.sh checks it).
module hfd_coll (
    input wire [24:0] f_cmdproc,
    input wire [1023:0] f_su_NE,
    input wire [1023:0] f_su_NW,
    input wire [1023:0] f_su_SE,
    input wire [1023:0] f_su_SW,
    inout wire [975:0] llk_N0,
    inout wire [975:0] llk_N1,
    inout wire [975:0] llk_N2,
    inout wire [975:0] llk_N3,
    inout wire [975:0] llk_S0,
    inout wire [975:0] llk_S1,
    inout wire [975:0] llk_S2,
    inout wire [975:0] llk_S3,
    inout wire [975:0] llk_S4,
    output wire [0:0] pll_hbm,
    output wire [0:0] pll_link,
    output wire [0:0] pll_serial,
    output wire [0:0] pll_stream,
    output wire [0:0] por_hbm,
    output wire [0:0] por_link,
    output wire [0:0] por_serial,
    output wire [0:0] por_stream,
    output wire [32:0] t_cmdproc,
    output wire [579:0] t_su_NE,
    output wire [579:0] t_su_NW,
    output wire [579:0] t_su_SE,
    output wire [579:0] t_su_SW,
    /* NOT A GENERATOR PORT (generator-side defect, see note) */ input wire refclk,
    /* NOT A GENERATOR PORT (generator-side defect, see note) */ input wire por
);
    wire clk = refclk;
    reg [1:0] rst_s; always @(posedge clk) rst_s <= {rst_s[0], por};
    wire rst_n = ~rst_s[1];
    reg [24:0] i0_f_cmdproc; always @(posedge clk) i0_f_cmdproc <= f_cmdproc;
    reg [24:0] i1_f_cmdproc; always @(posedge clk) i1_f_cmdproc <= i0_f_cmdproc;
    reg [24:0] i_f_cmdproc; always @(posedge clk) i_f_cmdproc <= i1_f_cmdproc;
    reg [1023:0] i0_f_su_NE; always @(posedge clk) i0_f_su_NE <= f_su_NE;
    reg [1023:0] i1_f_su_NE; always @(posedge clk) i1_f_su_NE <= i0_f_su_NE;
    reg [1023:0] i2_f_su_NE; always @(posedge clk) i2_f_su_NE <= i1_f_su_NE;
    reg [1023:0] i_f_su_NE; always @(posedge clk) i_f_su_NE <= i2_f_su_NE;
    reg [1023:0] i0_f_su_NW; always @(posedge clk) i0_f_su_NW <= f_su_NW;
    reg [1023:0] i1_f_su_NW; always @(posedge clk) i1_f_su_NW <= i0_f_su_NW;
    reg [1023:0] i2_f_su_NW; always @(posedge clk) i2_f_su_NW <= i1_f_su_NW;
    reg [1023:0] i_f_su_NW; always @(posedge clk) i_f_su_NW <= i2_f_su_NW;
    reg [1023:0] i0_f_su_SE; always @(posedge clk) i0_f_su_SE <= f_su_SE;
    reg [1023:0] i1_f_su_SE; always @(posedge clk) i1_f_su_SE <= i0_f_su_SE;
    reg [1023:0] i2_f_su_SE; always @(posedge clk) i2_f_su_SE <= i1_f_su_SE;
    reg [1023:0] i_f_su_SE; always @(posedge clk) i_f_su_SE <= i2_f_su_SE;
    reg [1023:0] i0_f_su_SW; always @(posedge clk) i0_f_su_SW <= f_su_SW;
    reg [1023:0] i1_f_su_SW; always @(posedge clk) i1_f_su_SW <= i0_f_su_SW;
    reg [1023:0] i2_f_su_SW; always @(posedge clk) i2_f_su_SW <= i1_f_su_SW;
    reg [1023:0] i_f_su_SW; always @(posedge clk) i_f_su_SW <= i2_f_su_SW;
    reg [975:0] i0_llk_N0; always @(posedge clk) i0_llk_N0 <= llk_N0;
    reg [975:0] i1_llk_N0; always @(posedge clk) i1_llk_N0 <= i0_llk_N0;
    reg [975:0] i_llk_N0; always @(posedge clk) i_llk_N0 <= i1_llk_N0;
    reg [975:0] i0_llk_N1; always @(posedge clk) i0_llk_N1 <= llk_N1;
    reg [975:0] i1_llk_N1; always @(posedge clk) i1_llk_N1 <= i0_llk_N1;
    reg [975:0] i_llk_N1; always @(posedge clk) i_llk_N1 <= i1_llk_N1;
    reg [975:0] i0_llk_N2; always @(posedge clk) i0_llk_N2 <= llk_N2;
    reg [975:0] i1_llk_N2; always @(posedge clk) i1_llk_N2 <= i0_llk_N2;
    reg [975:0] i_llk_N2; always @(posedge clk) i_llk_N2 <= i1_llk_N2;
    reg [975:0] i0_llk_N3; always @(posedge clk) i0_llk_N3 <= llk_N3;
    reg [975:0] i1_llk_N3; always @(posedge clk) i1_llk_N3 <= i0_llk_N3;
    reg [975:0] i_llk_N3; always @(posedge clk) i_llk_N3 <= i1_llk_N3;
    reg [975:0] i0_llk_S0; always @(posedge clk) i0_llk_S0 <= llk_S0;
    reg [975:0] i1_llk_S0; always @(posedge clk) i1_llk_S0 <= i0_llk_S0;
    reg [975:0] i_llk_S0; always @(posedge clk) i_llk_S0 <= i1_llk_S0;
    reg [975:0] i0_llk_S1; always @(posedge clk) i0_llk_S1 <= llk_S1;
    reg [975:0] i1_llk_S1; always @(posedge clk) i1_llk_S1 <= i0_llk_S1;
    reg [975:0] i_llk_S1; always @(posedge clk) i_llk_S1 <= i1_llk_S1;
    reg [975:0] i0_llk_S2; always @(posedge clk) i0_llk_S2 <= llk_S2;
    reg [975:0] i1_llk_S2; always @(posedge clk) i1_llk_S2 <= i0_llk_S2;
    reg [975:0] i_llk_S2; always @(posedge clk) i_llk_S2 <= i1_llk_S2;
    reg [975:0] i0_llk_S3; always @(posedge clk) i0_llk_S3 <= llk_S3;
    reg [975:0] i1_llk_S3; always @(posedge clk) i1_llk_S3 <= i0_llk_S3;
    reg [975:0] i_llk_S3; always @(posedge clk) i_llk_S3 <= i1_llk_S3;
    reg [975:0] i0_llk_S4; always @(posedge clk) i0_llk_S4 <= llk_S4;
    reg [975:0] i1_llk_S4; always @(posedge clk) i1_llk_S4 <= i0_llk_S4;
    reg [975:0] i_llk_S4; always @(posedge clk) i_llk_S4 <= i1_llk_S4;
    wire [0:0] w_ep_clk;
    wire [0:0] w_ep_rst_n;
    wire [0:0] w_ep_pclk;
    wire [0:0] w_ep_prst_n;
    wire [7:0] w_ep_rank;
    wire [15:0] w_ep_pf;
    wire [0:0] w_ep_go;
    wire [31:0] w_ep_inj_idx;
    wire [1:0] w_ep_inj_rd;
    wire [1023:0] w_ep_inj_data;
    wire [7:0] w_ep_ph_tx_v;
    wire [4359:0] w_ep_ph_tx_flit;
    wire [7:0] w_ep_sw_cr_ret;
    wire [7:0] w_ep_ph_rx_v;
    wire [4359:0] w_ep_ph_rx_flit;
    wire [7:0] w_ep_rx_credit;
    wire [3:0] w_ep_del_valid;
    wire [2179:0] w_ep_del_flit;
    wire [0:0] w_ep_fault;
    wire [31:0] w_ep_stat_credit_stall;
    assign w_ep_clk = {1{clk}};
    assign w_ep_rst_n = {1{rst_n}};
    assign w_ep_pclk = {1{clk}};
    assign w_ep_prst_n = {1{rst_n}};
    assign w_ep_rank = {i_f_cmdproc[7:0]};
    assign w_ep_pf = {i_f_cmdproc[23:8]};
    assign w_ep_go = {i_f_cmdproc[24:24]};
    assign w_ep_inj_data = {i_f_su_SW[1023:0]};
    assign w_ep_sw_cr_ret = {i_llk_N3[966:959]};
    assign w_ep_ph_rx_v = {i_llk_S0[494:487]};
    assign w_ep_ph_rx_flit = {i_llk_N3[958:487], i_llk_N2[973:487], i_llk_N1[973:487], i_llk_N0[973:487], i_llk_S4[973:487], i_llk_S3[973:487], i_llk_S2[973:487], i_llk_S1[973:487], i_llk_S0[973:495]};
    ot_hbm_accel_tu_endpoint_ps2 #(.ENABLE(1)) u_ep (.clk(w_ep_clk), .rst_n(w_ep_rst_n), .pclk(w_ep_pclk), .prst_n(w_ep_prst_n), .rank(w_ep_rank), .pf(w_ep_pf), .go(w_ep_go), .inj_idx(w_ep_inj_idx), .inj_rd(w_ep_inj_rd), .inj_data(w_ep_inj_data), .ph_tx_v(w_ep_ph_tx_v), .ph_tx_flit(w_ep_ph_tx_flit), .sw_cr_ret(w_ep_sw_cr_ret), .ph_rx_v(w_ep_ph_rx_v), .ph_rx_flit(w_ep_ph_rx_flit), .rx_credit(w_ep_rx_credit), .del_valid(w_ep_del_valid), .del_flit(w_ep_del_flit), .fault(w_ep_fault), .stat_credit_stall(w_ep_stat_credit_stall));
    wire fclk_0; ot_fwd_clk_inv u_fclk_0 (.a(clk), .y(fclk_0));
    wire fclk_1; ot_fwd_clk_inv u_fclk_1 (.a(clk), .y(fclk_1));
    wire fclk_2; ot_fwd_clk_inv u_fclk_2 (.a(clk), .y(fclk_2));
    wire fclk_3; ot_fwd_clk_inv u_fclk_3 (.a(clk), .y(fclk_3));
    wire fclk_4; ot_fwd_clk_inv u_fclk_4 (.a(clk), .y(fclk_4));
    wire fclk_5; ot_fwd_clk_inv u_fclk_5 (.a(clk), .y(fclk_5));
    wire fclk_6; ot_fwd_clk_inv u_fclk_6 (.a(clk), .y(fclk_6));
    wire fclk_7; ot_fwd_clk_inv u_fclk_7 (.a(clk), .y(fclk_7));
    wire fclk_8; ot_fwd_clk_inv u_fclk_8 (.a(clk), .y(fclk_8));
    wire fclk_9; ot_fwd_clk_inv u_fclk_9 (.a(clk), .y(fclk_9));
    wire fclk_10; ot_fwd_clk_inv u_fclk_10 (.a(clk), .y(fclk_10));
    wire fclk_11; ot_fwd_clk_inv u_fclk_11 (.a(clk), .y(fclk_11));
    wire fclk_12; ot_fwd_clk_inv u_fclk_12 (.a(clk), .y(fclk_12));
    wire [975:0] od_llk_N0 = {489'd0, w_ep_ph_tx_flit[2913:2427]};
    wire [975:0] o_llk_N0;
    for (genvar k = 0; k < 976; k = k + 1) begin : g_o_llk_N0
        ot_hfd_oreg3 u (.clk(clk), .d(od_llk_N0[k]), .q(o_llk_N0[k]));
    end
    assign llk_N0[486:0] = o_llk_N0[486:0];
    assign llk_N0[974] = fclk_0;
    wire [975:0] od_llk_N1 = {489'd0, w_ep_ph_tx_flit[3400:2914]};
    wire [975:0] o_llk_N1;
    for (genvar k = 0; k < 976; k = k + 1) begin : g_o_llk_N1
        ot_hfd_oreg3 u (.clk(clk), .d(od_llk_N1[k]), .q(o_llk_N1[k]));
    end
    assign llk_N1[486:0] = o_llk_N1[486:0];
    assign llk_N1[974] = fclk_1;
    wire [975:0] od_llk_N2 = {489'd0, w_ep_ph_tx_flit[3887:3401]};
    wire [975:0] o_llk_N2;
    for (genvar k = 0; k < 976; k = k + 1) begin : g_o_llk_N2
        ot_hfd_oreg3 u (.clk(clk), .d(od_llk_N2[k]), .q(o_llk_N2[k]));
    end
    assign llk_N2[486:0] = o_llk_N2[486:0];
    assign llk_N2[974] = fclk_2;
    wire [975:0] od_llk_N3 = {496'd0, w_ep_rx_credit[7:0], w_ep_ph_tx_flit[4359:3888]};
    wire [975:0] o_llk_N3;
    for (genvar k = 0; k < 976; k = k + 1) begin : g_o_llk_N3
        ot_hfd_oreg3 u (.clk(clk), .d(od_llk_N3[k]), .q(o_llk_N3[k]));
    end
    assign llk_N3[486:0] = o_llk_N3[486:0];
    assign llk_N3[974] = fclk_3;
    wire [975:0] od_llk_S0 = {489'd0, w_ep_ph_tx_flit[478:0], w_ep_ph_tx_v[7:0]};
    wire [975:0] o_llk_S0;
    for (genvar k = 0; k < 976; k = k + 1) begin : g_o_llk_S0
        ot_hfd_oreg3 u (.clk(clk), .d(od_llk_S0[k]), .q(o_llk_S0[k]));
    end
    assign llk_S0[486:0] = o_llk_S0[486:0];
    assign llk_S0[974] = fclk_4;
    wire [975:0] od_llk_S1 = {489'd0, w_ep_ph_tx_flit[965:479]};
    wire [975:0] o_llk_S1;
    for (genvar k = 0; k < 976; k = k + 1) begin : g_o_llk_S1
        ot_hfd_oreg3 u (.clk(clk), .d(od_llk_S1[k]), .q(o_llk_S1[k]));
    end
    assign llk_S1[486:0] = o_llk_S1[486:0];
    assign llk_S1[974] = fclk_5;
    wire [975:0] od_llk_S2 = {489'd0, w_ep_ph_tx_flit[1452:966]};
    wire [975:0] o_llk_S2;
    for (genvar k = 0; k < 976; k = k + 1) begin : g_o_llk_S2
        ot_hfd_oreg3 u (.clk(clk), .d(od_llk_S2[k]), .q(o_llk_S2[k]));
    end
    assign llk_S2[486:0] = o_llk_S2[486:0];
    assign llk_S2[974] = fclk_6;
    wire [975:0] od_llk_S3 = {489'd0, w_ep_ph_tx_flit[1939:1453]};
    wire [975:0] o_llk_S3;
    for (genvar k = 0; k < 976; k = k + 1) begin : g_o_llk_S3
        ot_hfd_oreg3 u (.clk(clk), .d(od_llk_S3[k]), .q(o_llk_S3[k]));
    end
    assign llk_S3[486:0] = o_llk_S3[486:0];
    assign llk_S3[974] = fclk_7;
    wire [975:0] od_llk_S4 = {489'd0, w_ep_ph_tx_flit[2426:1940]};
    wire [975:0] o_llk_S4;
    for (genvar k = 0; k < 976; k = k + 1) begin : g_o_llk_S4
        ot_hfd_oreg3 u (.clk(clk), .d(od_llk_S4[k]), .q(o_llk_S4[k]));
    end
    assign llk_S4[486:0] = o_llk_S4[486:0];
    assign llk_S4[974] = fclk_8;
    wire [0:0] od_pll_hbm = {1'd0};
    wire [0:0] o_pll_hbm;
    for (genvar k = 0; k < 1; k = k + 1) begin : g_o_pll_hbm
        ot_hfd_oreg5 u (.clk(clk), .d(od_pll_hbm[k]), .q(o_pll_hbm[k]));
    end
    assign pll_hbm[0] = fclk_9;
    wire [0:0] od_pll_link = {1'd0};
    wire [0:0] o_pll_link;
    for (genvar k = 0; k < 1; k = k + 1) begin : g_o_pll_link
        ot_hfd_oreg5 u (.clk(clk), .d(od_pll_link[k]), .q(o_pll_link[k]));
    end
    assign pll_link[0] = fclk_10;
    wire [0:0] od_pll_serial = {1'd0};
    wire [0:0] o_pll_serial;
    for (genvar k = 0; k < 1; k = k + 1) begin : g_o_pll_serial
        ot_hfd_oreg5 u (.clk(clk), .d(od_pll_serial[k]), .q(o_pll_serial[k]));
    end
    assign pll_serial[0] = fclk_11;
    wire [0:0] od_pll_stream = {1'd0};
    wire [0:0] o_pll_stream;
    for (genvar k = 0; k < 1; k = k + 1) begin : g_o_pll_stream
        ot_hfd_oreg5 u (.clk(clk), .d(od_pll_stream[k]), .q(o_pll_stream[k]));
    end
    assign pll_stream[0] = fclk_12;
    wire [0:0] od_por_hbm = {rst_s[1]};
    wire [0:0] o_por_hbm;
    for (genvar k = 0; k < 1; k = k + 1) begin : g_o_por_hbm
        ot_hfd_oreg3 u (.clk(clk), .d(od_por_hbm[k]), .q(o_por_hbm[k]));
    end
    assign por_hbm[0:0] = o_por_hbm[0:0];
    wire [0:0] od_por_link = {rst_s[1]};
    wire [0:0] o_por_link;
    for (genvar k = 0; k < 1; k = k + 1) begin : g_o_por_link
        ot_hfd_oreg3 u (.clk(clk), .d(od_por_link[k]), .q(o_por_link[k]));
    end
    assign por_link[0:0] = o_por_link[0:0];
    wire [0:0] od_por_serial = {rst_s[1]};
    wire [0:0] o_por_serial;
    for (genvar k = 0; k < 1; k = k + 1) begin : g_o_por_serial
        ot_hfd_oreg3 u (.clk(clk), .d(od_por_serial[k]), .q(o_por_serial[k]));
    end
    assign por_serial[0:0] = o_por_serial[0:0];
    wire [0:0] od_por_stream = {rst_s[1]};
    wire [0:0] o_por_stream;
    for (genvar k = 0; k < 1; k = k + 1) begin : g_o_por_stream
        ot_hfd_oreg3 u (.clk(clk), .d(od_por_stream[k]), .q(o_por_stream[k]));
    end
    assign por_stream[0:0] = o_por_stream[0:0];
    wire [32:0] od_t_cmdproc = {w_ep_stat_credit_stall[31:0], w_ep_fault[0:0]};
    wire [32:0] o_t_cmdproc;
    for (genvar k = 0; k < 33; k = k + 1) begin : g_o_t_cmdproc
        ot_hfd_oreg3 u (.clk(clk), .d(od_t_cmdproc[k]), .q(o_t_cmdproc[k]));
    end
    assign t_cmdproc[32:0] = o_t_cmdproc[32:0];
    wire [579:0] od_t_su_NE = {w_ep_inj_rd[1:0], w_ep_inj_idx[31:0], w_ep_del_valid[3:3], w_ep_del_flit[2179:1635]};
    wire [579:0] o_t_su_NE;
    for (genvar k = 0; k < 580; k = k + 1) begin : g_o_t_su_NE
        ot_hfd_oreg4 u (.clk(clk), .d(od_t_su_NE[k]), .q(o_t_su_NE[k]));
    end
    assign t_su_NE[579:0] = o_t_su_NE[579:0];
    wire [579:0] od_t_su_NW = {w_ep_inj_rd[1:0], w_ep_inj_idx[31:0], w_ep_del_valid[1:1], w_ep_del_flit[1089:545]};
    wire [579:0] o_t_su_NW;
    for (genvar k = 0; k < 580; k = k + 1) begin : g_o_t_su_NW
        ot_hfd_oreg4 u (.clk(clk), .d(od_t_su_NW[k]), .q(o_t_su_NW[k]));
    end
    assign t_su_NW[579:0] = o_t_su_NW[579:0];
    wire [579:0] od_t_su_SE = {w_ep_inj_rd[1:0], w_ep_inj_idx[31:0], w_ep_del_valid[2:2], w_ep_del_flit[1634:1090]};
    wire [579:0] o_t_su_SE;
    for (genvar k = 0; k < 580; k = k + 1) begin : g_o_t_su_SE
        ot_hfd_oreg4 u (.clk(clk), .d(od_t_su_SE[k]), .q(o_t_su_SE[k]));
    end
    assign t_su_SE[579:0] = o_t_su_SE[579:0];
    wire [579:0] od_t_su_SW = {w_ep_inj_rd[1:0], w_ep_inj_idx[31:0], w_ep_del_valid[0:0], w_ep_del_flit[544:0]};
    wire [579:0] o_t_su_SW;
    for (genvar k = 0; k < 580; k = k + 1) begin : g_o_t_su_SW
        ot_hfd_oreg4 u (.clk(clk), .d(od_t_su_SW[k]), .q(o_t_su_SW[k]));
    end
    assign t_su_SW[579:0] = o_t_su_SW[579:0];
endmodule
