// hfd_coll, rtl_hgi (hgi-takeover 2026-10-09): the rtl_ps per-port split view + the HGI-1 normative record path.
// Changes against rtl_ps (every other line identical):
//  * endpoint ot_hbm_accel_tu_endpoint_ps -> ot_hbm_accel_tu_endpoint_psg (ENABLE 1, REARM 1: group sizes 1/2/4/8/96,
//    GROUP_REDUCE_MCAST, done / fault handshake); legacy DS gsz = 4'hF reset;
//  * die pins f_hgi_cmdproc[967:0] = {die_id 8, n_I, n_O, n_A (21 each), desc_I, desc_O, desc_A (256 each), header 128,
//    valid}, f_hgi_cfg[39:0] = the HGI config station bus (word 46 coll_group_size, reset 96 = DS)
//    and t_hgi_cmdproc[2:0] = {fault, done, ready} (tools/hgi_die_dispatch.py 'coll', bit 0 first), one register stage
//    each way; ot_hgi_coll_record decodes the record (ot_hgi_coll_decode) and drives the endpoint;
//  * the legacy f_cmdproc {go, pf, rank} path stays live: the endpoint takes its control from whichever source issued
//    the last go (legacy: gsz F, no mcast, completion auto-acknowledged as on the PS endpoint, which has none);
//  * ROW_GATHER start fields leave on t_hgi_rowfmt[93:0] / f_hgi_rowfmt[2:0] (the row formatter sits at the row
//    reader) and the A / O effective bases on t_hgi_vmaddr[79:0] (SU inject / deliver addressing).  These three
//    die buses are not yet declared by the generator: open integration items, flagged by die lint.
//  * a record arriving while the station is busy (credit violation upstream) latches the fault (fail-closed).
// hfd_coll, rtl_ps (stream hbm-coll-rtl, 2026-10-08): PER-PORT SPLIT die view.  The rtl/hfd_coll.sv die wrapper
// (tools/hbm_die_wrap.py; die ports exactly as the r16g generator master, every pin registered) with the endpoint
// replaced by ot_hbm_accel_tu_endpoint_ps: 8 x ot_hcoll_port hard blocks (one hardened slice, 18 SRAM macros each:
// port queues, arbiter + switch credit, TX/RX wire stages, pacing, 256-entry receive buffer with a credit-flow
// exported head) + the core (hub lines, slots, 112-adder tree, delivery, own queue; 21 SRAM macros) in this top.
// pclk = clk as before.  Every non-comment line equals rtl/hfd_coll.sv except the endpoint instance line
// (rtl_sr/run_sr_bench.sh checks it).
module hfd_coll (
    input wire [24:0] f_cmdproc,
    input wire [967:0] f_hgi_cmdproc,
    input wire [39:0] f_hgi_cfg,
    output wire [2:0] t_hgi_cmdproc,
    output wire [93:0] t_hgi_rowfmt,
    input wire [2:0] f_hgi_rowfmt,
    output wire [79:0] t_hgi_vmaddr,
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
    // ---- HGI-1 record path (fault_ack is 0: an endpoint fault is sticky until the drained reset, HGI-1 MX-1) ----
    reg [967:0] i_f_hgi; always @(posedge clk) i_f_hgi <= f_hgi_cmdproc;
    wire [7:0] w_ep_mg; wire w_ep_mall; wire [3:0] w_ep_gsz; wire w_ep_start_ready, w_ep_done_valid, w_ep_done_ready;
    wire [7:0] r_rank, r_mg; wire r_mall, r_byp; wire [3:0] r_gsz; wire [15:0] r_pf; wire r_go, r_done_ready;
    wire [39:0] r_abase, r_obase; wire rec_rdy, rec_done, rec_fault;
    wire rf_sv, rf_dr; wire [7:0] rf_g, rf_b, rf_d; wire [20:0] rf_rows; wire [15:0] rf_words; wire [31:0] rf_ctx;
    // static coll_group_size (MD word 46 [7:0]) from the config station bus; die id rides the record (seq rank strap)
    wire [31:0] cfg_w46;
    ot_hgi_cfg_rx #(.W0(46), .NW(1), .RST(32'd96)) u_cfg (.clk(clk), .rst_n(rst_n), .bus(f_hgi_cfg), .act(cfg_w46));
    wire [7:0] cfg_g = cfg_w46[7:0];
    wire [7:0] cfg_die = i_f_hgi[967:960];
    ot_hgi_coll_record u_rec (.clk(clk), .rst_n(rst_n), .cfg_coll_group_size(cfg_g), .cfg_die_id(cfg_die),
        .rec_v(i_f_hgi[0]), .rec_rdy(rec_rdy), .rec_hdr(i_f_hgi[128:1]), .rec_a(i_f_hgi[384:129]),
        .rec_o(i_f_hgi[640:385]), .rec_i(i_f_hgi[896:641]), .rec_n_a(i_f_hgi[917:897]), .rec_n_o(i_f_hgi[938:918]),
        .rec_n_i(i_f_hgi[959:939]), .rec_done(rec_done), .rec_fault(rec_fault),
        .ep_rank(r_rank), .ep_mcast_group_size(r_mg), .ep_mcast_all(r_mall), .ep_gsz(r_gsz), .ep_byp(r_byp), .ep_pf(r_pf), .ep_go(r_go),
        .ep_start_ready(w_ep_start_ready), .ep_done_valid(w_ep_done_valid), .ep_done_ready(r_done_ready),
        .ep_fault(w_ep_fault[0]), .ep_a_base(r_abase), .ep_o_base(r_obase),
        .rf_start_v(rf_sv), .rf_start_r(i_f_rowfmt[0]), .rf_group_size(rf_g), .rf_owner_block(rf_b),
        .rf_destinations(rf_d), .rf_row_count(rf_rows), .rf_row_words(rf_words), .rf_context_rows(rf_ctx),
        .rf_done_v(i_f_rowfmt[1]), .rf_done_r(rf_dr), .rf_fault(i_f_rowfmt[2]));
    reg [2:0] i_f_rowfmt; always @(posedge clk) i_f_rowfmt <= f_hgi_rowfmt;
    // endpoint control owner: the source of the last go
    reg own_hgi; always @(posedge clk or negedge rst_n) if (!rst_n) own_hgi <= 1'b0;
        else if (r_go) own_hgi <= 1'b1; else if (i_f_cmdproc[24]) own_hgi <= 1'b0;
    wire sel_hgi = r_go | (own_hgi & ~i_f_cmdproc[24]);
    assign w_ep_rank = sel_hgi ? r_rank : {i_f_cmdproc[7:0]};
    assign w_ep_pf = sel_hgi ? r_pf : {i_f_cmdproc[23:8]};
    assign w_ep_go = {r_go | i_f_cmdproc[24]};
    assign w_ep_mg = sel_hgi ? r_mg : 8'd96;
    assign w_ep_mall = sel_hgi & r_mall;
    assign w_ep_gsz = sel_hgi ? r_gsz : 4'hF;
    assign w_ep_done_ready = own_hgi ? r_done_ready : w_ep_done_valid;
    reg ovf; always @(posedge clk or negedge rst_n) if (!rst_n) ovf <= 1'b0; else if (i_f_hgi[0] && !rec_rdy) ovf <= 1'b1;
    reg [2:0] o_hgi; always @(posedge clk) o_hgi <= {rec_fault | ovf, rec_done, rec_rdy};
    assign t_hgi_cmdproc = o_hgi;
    reg [93:0] o_rowfmt; always @(posedge clk) o_rowfmt <= {rf_ctx, rf_words, rf_rows, rf_d, rf_b, rf_g, rf_dr, rf_sv};
    assign t_hgi_rowfmt = o_rowfmt;
    reg [79:0] o_vmaddr; always @(posedge clk) o_vmaddr <= {r_obase, r_abase};
    assign t_hgi_vmaddr = o_vmaddr;
    assign w_ep_inj_data = i_f_su_SW[1023:0] | i_f_su_NW[1023:0] | i_f_su_SE[1023:0] | i_f_su_NE[1023:0];   // SU-quarter ownership OR (rtl/spec.json contracts)
`ifndef SYNTHESIS
    // inject ownership contract (rtl/spec.json contracts ep.inj_data): at most one SU quarter drives a non-zero
    // inject beat; the owner of flit i is quarter i mod 4 (SW, NW, SE, NE).  Any overlap is a contract violation.
    always @(posedge clk) if (rst_n && ((|i_f_su_SW[1023:0]) + (|i_f_su_NW[1023:0]) + (|i_f_su_SE[1023:0]) + (|i_f_su_NE[1023:0])) > 1)
        $error("hfd_coll: SU inject ownership violated (more than one quarter drives inject data)");
`endif
    assign w_ep_sw_cr_ret = {i_llk_N3[966:959]};
    assign w_ep_ph_rx_v = {i_llk_S0[494:487]};
    assign w_ep_ph_rx_flit = {i_llk_N3[958:487], i_llk_N2[973:487], i_llk_N1[973:487], i_llk_N0[973:487], i_llk_S4[973:487], i_llk_S3[973:487], i_llk_S2[973:487], i_llk_S1[973:487], i_llk_S0[973:495]};
    ot_hbm_accel_tu_endpoint_psg #(.ENABLE(1), .REARM(1), .NOG(12)) u_ep (.clk(w_ep_clk), .rst_n(w_ep_rst_n), .pclk(w_ep_pclk), .prst_n(w_ep_prst_n), .rank(w_ep_rank), .mcast_group_size(w_ep_mg), .mcast_all(w_ep_mall), .gsz(w_ep_gsz), .byp(sel_hgi & r_byp), .pf(w_ep_pf), .go(w_ep_go), .start_ready(w_ep_start_ready), .done_valid(w_ep_done_valid), .done_ready(w_ep_done_ready), .fault_ack(1'b0), .inj_idx(w_ep_inj_idx), .inj_rd(w_ep_inj_rd), .inj_data(w_ep_inj_data), .ph_tx_v(w_ep_ph_tx_v), .ph_tx_flit(w_ep_ph_tx_flit), .sw_cr_ret(w_ep_sw_cr_ret), .ph_rx_v(w_ep_ph_rx_v), .ph_rx_flit(w_ep_ph_rx_flit), .rx_credit(w_ep_rx_credit), .del_valid(w_ep_del_valid), .del_flit(w_ep_del_flit), .fault(w_ep_fault), .stat_credit_stall(w_ep_stat_credit_stall));
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
