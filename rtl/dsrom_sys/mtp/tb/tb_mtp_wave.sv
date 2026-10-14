`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// tb_mtp_wave: production-shape throughput bench of the integrated DS-ROM MTP draft / WFC verify / accept loop as bound
// on the S81 dies (el1011-ds-mtp [wave], 2026-10-11; throughput qualification of the 'wave' class, AGENTS.md
// "Throughput qualification": measured cycles within 10 % of the simulator price, results/arch/mtp_step_20261009/
// ds_rom_step.json charges).  One user, gamma 5 drafts, a deterministic accept pattern committing 1..6 rows a step
// (mean 4.167 ~ tau 4.159), 3 P2 transactions a draft, 80-beat (5,120 BF16) main-hidden row parts, S81 station depths.
//
// Closed element RTL in the loop (each block exactly as built; links over the routed station counts):
//   verify wave   S0 die wv_s0 (dsfd_wfc_src TOKIN + dsfd_wfc_tok_hard + crp) -> NSTG = 4 stage dies wv_stg (dsfd_wfc_crp +
//                 dsfd_wfc_stg + dsfd_vm_wfc_ep + dsfd_stage_seq), collective hops between dies as wv_cstub
//   head die      dsfd_mtp_seq_rtt (head631 stations 6/7, 9/9, 11/11) + dsfd_cap_mtp_ep + dsfd_vm_mtp_ep
//   MTP lanes     dsfd_coll_mtp_lane pairs (head -> S0: token return + accept word; head -> primary: seed)
//   primary die   dsfd_mtp_seed_launch + dsfd_mtp_hrow (fed by ot_dsrom_mtp_hrow_tx on stage dies 1..3 = layers 37/38/39)
//   draft die A   dsfd_coll_p2_lane_pa / _ba (+ the far lane ends), dsfd_coll_p2_ep, dsfd_vm_p2_ep, dsfd_p2_rtt
//                 (dsfd_p2_lnk + ot_mtp_p2_prefix_path), 3 serial P2 transactions a draft (fixture gold rows)
//   draft head    ot_dsrom_markov_row K 256 PINREG 1 (released vectors results/rtl/dsrom_markov_row_20261008) per step
//   accept        ot_mtp_commit, ot_mtp_hist_ring / ot_mtp_hist_ring_p (Engram history with rollback)
//   twin          p2.link_ends price basis: dsfd_p2_rtt at 0 stations vs the core driven directly (saturated)
// Stubs (not under test, measured busy times): stage core (T_BUSY), S0 core, head lm-head (T_LM, pipelined), seed_ctl
// (T_SC after 240 beats), draft block compute before each P2 transaction (T_BLK), rest of the draft-head sweep (T_HX).
// Exactness: committed tokens = greedy truth; every HIDDEN word at every hop; P2 rows = gold.hex; Markov joins =
// gold.hex; every seed beat = the committed position's main-hidden row; commit n / squash; history reads.
// Output: WAVE_CHARGE lines (tools/mtp_wave_bench.py builds the opentallas.mtp-wave-bench.v1 record), WAVE PASS|FAIL.
// ---------------------------------------------------------------------------------------------------------------
module tb_mtp_wave;
    parameter integer T_BUSY = 8453;     // stage busy, slow cycles (11,271 fast: results/rtl/dsrom_wavefront_verify_20261004)
    parameter integer T_BUSY0 = 8453;    // S0 (layer die) busy, slow cycles
    parameter integer T_LM = 12217;      // head lm-head latency (pipelined), fast cycles
    parameter integer T_BLK = 2467;      // draft block compute before each P2 transaction, fast cycles
    parameter integer T_HX = 300;        // rest of a draft-head step after the Markov join, fast cycles
    parameter integer T_SC = 11780;      // seed_ctl processing after a row's 240 beats (316 + 1,433 x RP 8), fast cycles
    parameter integer NSTEPMAX = 13;     // speculative steps to run after the prefill close
    parameter integer PLEN = 5;
    parameter integer MAXC = 20000000;
    parameter integer VERB = 0;
    localparam integer FLIT = 512, NW = 21, USER_W = 10, G = 5, V = 129280, MAXP = 512;
    localparam integer SW = USER_W + 3 * NW + 4, DW = USER_W + 3 + NW, AW = 2 * NW + USER_W + 5, PW = USER_W + 2 * NW + 4;
    localparam integer HDR_TYPE = 16, HDR_LEN = 24, HDR_USER = 32, HDR_POS = 40, HDR_IDX = 61, HDR_VAL = 82, HDR_TOK = 114,
                       HDR_USER_HI = 151;
    localparam integer S_L = 10;                         // die hub stations WFC <-> collective, each way (layer1 x1b+rgap)
    localparam integer FC = 6, RC = 7, FT = 9, RT = 9, FV = 11, RV = 11;   // head631 + split3cr MTP lane
    localparam integer LL = 17;                          // lane latency (UCIe leg incl. the vendor channel)
    localparam integer PF = 9, PR = 9, QF = 6, QR = 6, XH = 4, SF = 9, SR = 9;   // primary die (tb_mtp_hrow counts)
    localparam integer P2FV = 12, P2RV = 14, P2FC = 8, P2RC = 9;   // draft die A (draftA_stages.json)
    `include "tb_mtp_wave_fn.svh"

    reg fclk = 0, sclk = 0;
    always #1.5 fclk = ~fclk;
    always #2.0 sclk = ~sclk;
    reg rst_n = 0;
    integer cyc = 0;
    always @(posedge fclk) cyc <= cyc + 1;
    integer errs = 0;
    task automatic fail(input [8*120-1:0] msg); begin $display("WAVE FAIL: %0s at %0d", msg, cyc); errs = errs + 1; end endtask

    // ------------------------------------------------------------------ greedy truth (one user)
    integer tru [0:MAXP-1]; reg [31:0] ph [0:MAXP-1]; integer tok_at [0:MAXP-1]; reg [31:0] phi [0:MAXP-1];
    integer plen, ngen, steps, i, k;
    function automatic integer htok(input [31:0] h); htok = wv_mix(h, 77) % V; endfunction
    // deterministic accept pattern: drafts correct = a (committed rows a + 1 = 4,6,3,5,1,6,4,5,2,6,4,4: mean 4.167)
    integer PAT [0:11];
    initial begin
        PAT[0] = 3; PAT[1] = 5; PAT[2] = 2; PAT[3] = 4; PAT[4] = 0; PAT[5] = 5;
        PAT[6] = 3; PAT[7] = 4; PAT[8] = 1; PAT[9] = 5; PAT[10] = 3; PAT[11] = 3;
    end

    // ------------------------------------------------------------------ S0 die + stage dies + collective hops
    reg [54:0] cfgw = 0; wire [52:0] t_tok; wire s0_ft; wire [512:0] s0_mrt; wire s0_mrg;
    wire s0_lov, s0_loc; wire [512:0] s0_lod;
    wv_s0 #(.T_BUSY(T_BUSY0)) s0 (.fclk(fclk), .sclk(sclk), .rst_n(rst_n), .f_c(cfgw), .t_tok(t_tok), .f_mrt(s0_mrt),
        .t_mrg(s0_mrg), .t_lov(s0_lov), .t_lod(s0_lod), .f_loc(s0_loc), .fault(s0_ft));
    // die link segments: [d] = die d's link out (d = 0: S0), stub d -> d+1, die d+1's link in; 4 stage dies, head = 5
    wire [5:0] o_v, o_c, ox_v, ox_c, i_v, i_c, ix_v, ix_c; wire [512:0] o_d [0:5]; wire [512:0] ox_d [0:5];
    wire [512:0] i_d [0:5]; wire [512:0] ix_d [0:5]; wire [5:0] stub_bad; wire [4:1] stg_ft;
    assign o_v[0] = s0_lov; assign o_d[0] = s0_lod; assign s0_loc = o_c[0];
    wire [3:1] h_lv, h_lg; wire [513:0] h_ld [1:3];
    genvar gd;
    generate for (gd = 0; gd < 5; gd = gd + 1) begin : g_hop
        // die gd link out -> S_L stations -> stub (credit back S_L stations)
        wv_relay #(.W(514), .N(S_L)) r_o (.clk(fclk), .rst_n(rst_n), .d({o_v[gd], o_d[gd]}), .q({ox_v[gd], ox_d[gd]}));
        wv_relay #(.W(1), .N(S_L)) r_oc (.clk(fclk), .rst_n(rst_n), .d(ox_c[gd]), .q(o_c[gd]));
        if (gd < 4) begin : g_stub
            wv_cstub #(.SIN(gd == 0 ? 1 : 100 + gd), .SOUT(gd + 1), .INW(gd == 0 ? 41 : 46), .OUTW(41)) u_st (.clk(fclk),
                .rst_n(rst_n), .i_v(ox_v[gd]), .i_d(ox_d[gd]), .i_c(ox_c[gd]), .n_v(ix_v[gd+1]), .n_d(ix_d[gd+1]),
                .n_c(ix_c[gd+1]), .bad(stub_bad[gd]));
            // stub -> S_L stations -> die gd+1 link in (credit back)
            wv_relay #(.W(514), .N(S_L)) r_i (.clk(fclk), .rst_n(rst_n), .d({ix_v[gd+1], ix_d[gd+1]}), .q({i_v[gd+1], i_d[gd+1]}));
            wv_relay #(.W(1), .N(S_L)) r_ic (.clk(fclk), .rst_n(rst_n), .d(i_c[gd+1]), .q(ix_c[gd+1]));
        end
    end endgenerate
    assign stub_bad[4] = 1'b0; assign stub_bad[5] = 1'b0;
    wv_stg #(.D(1), .HP(0), .T_BUSY(T_BUSY)) s1 (.fclk(fclk), .sclk(sclk), .rst_n(rst_n), .f_liv(i_v[1]), .f_lid(i_d[1]),
        .t_lic(i_c[1]), .t_lov(o_v[1]), .t_lod(o_d[1]), .f_loc(o_c[1]), .h_lv(h_lv[1]), .h_ld(h_ld[1]), .h_lg(h_lg[1]), .fault(stg_ft[1]));
    wv_stg #(.D(2), .HP(1), .T_BUSY(T_BUSY)) s2 (.fclk(fclk), .sclk(sclk), .rst_n(rst_n), .f_liv(i_v[2]), .f_lid(i_d[2]),
        .t_lic(i_c[2]), .t_lov(o_v[2]), .t_lod(o_d[2]), .f_loc(o_c[2]), .h_lv(h_lv[2]), .h_ld(h_ld[2]), .h_lg(h_lg[2]), .fault(stg_ft[2]));
    wv_stg #(.D(3), .HP(2), .T_BUSY(T_BUSY)) s3 (.fclk(fclk), .sclk(sclk), .rst_n(rst_n), .f_liv(i_v[3]), .f_lid(i_d[3]),
        .t_lic(i_c[3]), .t_lov(o_v[3]), .t_lod(o_d[3]), .f_loc(o_c[3]), .h_lv(h_lv[3]), .h_ld(h_ld[3]), .h_lg(h_lg[3]), .fault(stg_ft[3]));
    wire s4_hlv; wire [513:0] s4_hld;
    wv_stg #(.D(4), .HP(-1), .T_BUSY(T_BUSY)) s4 (.fclk(fclk), .sclk(sclk), .rst_n(rst_n), .f_liv(i_v[4]), .f_lid(i_d[4]),
        .t_lic(i_c[4]), .t_lov(o_v[4]), .t_lod(o_d[4]), .f_loc(o_c[4]), .h_lv(s4_hlv), .h_ld(s4_hld), .h_lg(1'b0), .fault(stg_ft[4]));

    // ------------------------------------------------------------------ head die: lm-head stub -> RESULT (cap ep) -> seq
    // last stage's 46-word HIDDEN lands here (credit link from die 4); target = greedy of the ISSUED context
    reg [512:0] hq [0:255]; integer hq_w = 0, hq_r = 0, hm_k = -1, hm_p, hm_t, hm_n = 0; reg hc = 0;
    integer pq_p [0:1023], pq_g [0:1023], pq_t [0:1023], pq_w = 0, pq_r = 0, tg;
    assign ox_c[4] = hc;
    reg br_v = 0; reg [FLIT-1:0] br_d = 0; wire br_r;
    always @(posedge fclk) begin
        hc <= 1'b0;
        if (rst_n) begin
            if (hq_r < hq_w) begin
                if (hm_k < 0) begin
                    if (hq[hq_r % 256][HDR_TYPE +: 4] != 4'd1 || hq[hq_r % 256][HDR_LEN +: 8] != 46) fail("head: non-HIDDEN header");
                    hm_p = hq[hq_r % 256][HDR_POS +: NW]; hm_t = hq[hq_r % 256][HDR_TOK +: NW]; hm_k = 0;
                end else begin
                    if (hq[hq_r % 256][511:0] !== wv_word(104, hm_p, hm_t, hm_k)) fail("head: HIDDEN payload word");
                    hm_k = hm_k + 1;
                    if (hm_k == 46) begin
                        tok_at[hm_p] = hm_t;
                        phi[hm_p] = wv_mix((hm_p == 0) ? 32'd5 : phi[hm_p - 1], hm_t);
                        tg = htok(phi[hm_p]);
                        pq_p[pq_w % 1024] = hm_p; pq_g[pq_w % 1024] = tg; pq_t[pq_w % 1024] = cyc + T_LM; pq_w = pq_w + 1;
                        hm_k = -1; hm_n = hm_n + 1;
                    end
                end
                hq_r = hq_r + 1; hc <= 1'b1;
            end
            if (ox_v[4]) begin hq[hq_w % 256] = ox_d[4]; hq_w = hq_w + 1; end
            if (br_v && br_r) br_v <= 1'b0;
            if ((!br_v || br_r) && pq_r < pq_w && cyc >= pq_t[pq_r % 1024]) begin
                br_v <= 1'b1; br_d <= 0;
                br_d[15:0] <= 16'h3a00; br_d[HDR_TYPE +: 4] <= 4'd2; br_d[HDR_USER +: 8] <= 0; br_d[HDR_USER_HI +: 2] <= 0;
                br_d[HDR_POS +: NW] <= pq_p[pq_r % 1024]; br_d[HDR_IDX +: NW] <= pq_g[pq_r % 1024];
                br_d[HDR_VAL +: 32] <= 32'h40000000 + pq_g[pq_r % 1024];
                pq_r = pq_r + 1;
            end
        end
    end
    // sequencer + partner ends + station chains
    wire s_rv, s_rg, s_tv, s_tg, s_sv, s_sg, s_wv, s_wg, s_hv, s_hg, s_qv, s_qg;       // partner side
    wire [FLIT-1:0] s_rd, s_td; wire [SW-1:0] s_sd; wire [USER_W-1:0] s_wd; wire [DW-1:0] s_hd, s_qd;
    wire p_rv, p_rg, p_tv, p_tg, p_sv, p_sg, p_wv, p_wg, p_hv, p_hg, p_qv, p_qg;       // sequencer pins
    wire [FLIT-1:0] p_rd, p_td; wire [SW-1:0] p_sd; wire [USER_W-1:0] p_wd; wire [DW-1:0] p_hd, p_qd;
    wire [2*NW+USER_W+4:0] s_acc, x_acc;
    wv_relay #(.W(FLIT+1), .N(FC)) r_r (.clk(fclk), .rst_n(rst_n), .d({s_rd, s_rv}), .q({p_rd, p_rv}));
    wv_relay #(.W(1), .N(RC)) r_rg (.clk(fclk), .rst_n(rst_n), .d(p_rg), .q(s_rg));
    wv_relay #(.W(FLIT+1), .N(FT)) r_t (.clk(fclk), .rst_n(rst_n), .d({p_td, p_tv}), .q({s_td, s_tv}));
    wv_relay #(.W(1), .N(RT)) r_tg (.clk(fclk), .rst_n(rst_n), .d(s_tg), .q(p_tg));
    wv_relay #(.W(SW+1), .N(FT)) r_s (.clk(fclk), .rst_n(rst_n), .d({p_sd, p_sv}), .q({s_sd, s_sv}));
    wv_relay #(.W(1), .N(RT)) r_sg (.clk(fclk), .rst_n(rst_n), .d(s_sg), .q(p_sg));
    wv_relay #(.W(USER_W+1), .N(FV)) r_w (.clk(fclk), .rst_n(rst_n), .d({s_wd, s_wv}), .q({p_wd, p_wv}));
    wv_relay #(.W(1), .N(RV)) r_wg (.clk(fclk), .rst_n(rst_n), .d(p_wg), .q(s_wg));
    wv_relay #(.W(DW+1), .N(RV)) r_h (.clk(fclk), .rst_n(rst_n), .d({p_hd, p_hv}), .q({s_hd, s_hv}));
    wv_relay #(.W(1), .N(FV)) r_hg (.clk(fclk), .rst_n(rst_n), .d(s_hg), .q(p_hg));
    wv_relay #(.W(DW+1), .N(FV)) r_q (.clk(fclk), .rst_n(rst_n), .d({s_qd, s_qv}), .q({p_qd, p_qv}));
    wv_relay #(.W(1), .N(RV)) r_qg (.clk(fclk), .rst_n(rst_n), .d(p_qg), .q(s_qg));
    wv_relay #(.W(AW), .N(FT)) r_acc (.clk(fclk), .rst_n(rst_n), .d(s_acc), .q(x_acc));
    wire [9:0] cfg_users_unused;
    dsfd_mtp_seq_rtt #(.MAXU(8)) u_seq (.ck(fclk), .rst(rst_n), .f_cfg({NW'(ngen), NW'(plen)}),
        .f_rv(p_rv), .f_rd(p_rd), .t_rg(p_rg), .t_tv(p_tv), .t_td(p_td), .f_tg(p_tg),
        .t_sv(p_sv), .t_sd(p_sd), .f_sg(p_sg), .f_wv(p_wv), .f_wd(p_wd), .t_wg(p_wg),
        .t_hv(p_hv), .t_hd(p_hd), .f_hg(p_hg), .f_qv(p_qv), .f_qd(p_qd), .t_qg(p_qg), .t_acc(s_acc));
    dsfd_cap_mtp_ep e_cap (.ck(fclk), .rst(rst_n), .c_rv(br_v), .c_rr(br_r), .c_rd(br_d), .t_rv(s_rv), .t_rd(s_rd), .f_rg(s_rg));
    wire bh_v; wire [DW-1:0] bh_d; reg bw_v = 0; reg [USER_W-1:0] bw_d = 0; wire bw_r; reg bq_v = 0; reg [DW-1:0] bq_d = 0; wire bq_r;
    dsfd_vm_mtp_ep #(.FWD_H(RV), .RET_H(FV)) e_vm (.ck(fclk), .rst(rst_n),
        .f_hv(s_hv), .f_hd(s_hd), .t_hg(s_hg), .c_hv(bh_v), .c_hr(1'b1), .c_hd(bh_d),
        .c_wv(bw_v), .c_wr(bw_r), .c_wd(bw_d), .t_wv(s_wv), .t_wd(s_wd), .f_wg(s_wg),
        .c_qv(bq_v), .c_qr(bq_r), .c_qd(bq_d), .t_qv(s_qv), .t_qd(s_qd), .f_qg(s_qg));
    // draft_head.pipe_regs reference: the same receiver without OUTPUT_PIPE on the same input (probe, drives nothing)
    wire rf_hv, rf_hg_unused; wire [DW-1:0] rf_hd; reg [1:0] ref_rn = 0;
    always @(posedge fclk or negedge rst_n) if (!rst_n) ref_rn <= 2'b00; else ref_rn <= {ref_rn[0], 1'b1};
    ot_dsrom_mtp_lrx_rtt #(.W(DW), .D(RV+FV+4), .SEL(1), .ENABLE_RTT(1), .OUTPUT_PIPE(0), .FORWARD_HOPS(RV), .RETURN_HOPS(FV)) e_ref (
        .clk(fclk), .rst_n(ref_rn[1]), .l_valid(s_hv), .l_ready(rf_hg_unused), .l_data(s_hd), .c_valid(rf_hv), .c_ready(1'b1), .c_data(rf_hd));

    // ------------------------------------------------------------------ MTP lanes: head -> S0 (token, accept), head -> primary (seed)
    wire hT_lov, hT_lor, hT_liv, hT_lir, sT_lov, sT_lor, sT_liv, sT_lir; wire [552:0] hT_lod, hT_lid, sT_lod, sT_lid;
    wire hS_lov, hS_lor, hS_liv, hS_lir, pS_lov, pS_lor, pS_liv, pS_lir; wire [552:0] hS_lod, hS_lid, pS_lod, pS_lid;
    wire [AW-1:0] sT_racc, hT_racc, hS_racc, pS_racc; wire [3:0] lane_ft;
    wire sT_rtv, sT_rtg; wire [FLIT-1:0] sT_rtd;
    wire pS_rsv, pS_rsg; wire [SW-1:0] pS_rsd;
    dsfd_coll_mtp_lane u_hT (.ck(fclk), .rs(rst_n), .f_tv(s_tv), .f_td(s_td), .t_tg(s_tg), .f_sv(1'b0), .f_sd({SW{1'b0}}), .t_sg(),
        .f_acc(x_acc), .lo_v(hT_lov), .lo_r(hT_lor), .lo_d(hT_lod), .li_v(hT_liv), .li_r(hT_lir), .li_d(hT_lid),
        .t_rtv(), .t_rtd(), .f_rtg(1'b0), .t_rsv(), .t_rsd(), .f_rsg(1'b0), .t_racc(hT_racc), .f_lflt(3'b0));
    dsfd_coll_mtp_lane u_sT (.ck(fclk), .rs(rst_n), .f_tv(1'b0), .f_td({FLIT{1'b0}}), .t_tg(), .f_sv(1'b0), .f_sd({SW{1'b0}}), .t_sg(),
        .f_acc({AW{1'b0}}), .lo_v(sT_lov), .lo_r(sT_lor), .lo_d(sT_lod), .li_v(sT_liv), .li_r(sT_lir), .li_d(sT_lid),
        .t_rtv(sT_rtv), .t_rtd(sT_rtd), .f_rtg(sT_rtg), .t_rsv(), .t_rsd(), .f_rsg(1'b0), .t_racc(sT_racc), .f_lflt(3'b0));
    wv_lane #(.LL(LL)) l_hs (.clk(fclk), .rst_n(rst_n), .a_v(hT_lov), .a_d(hT_lod), .a_c(hT_lor), .b_v(sT_liv), .b_d(sT_lid), .b_c(sT_lir), .fault(lane_ft[0]));
    wv_lane #(.LL(LL)) l_sh (.clk(fclk), .rst_n(rst_n), .a_v(sT_lov), .a_d(sT_lod), .a_c(sT_lor), .b_v(hT_liv), .b_d(hT_lid), .b_c(hT_lir), .fault(lane_ft[1]));
    assign s0_mrt = {sT_rtd, sT_rtv}; assign sT_rtg = s0_mrg;                         // S0 kit TOKIN (abutting)
    dsfd_coll_mtp_lane u_hS (.ck(fclk), .rs(rst_n), .f_tv(1'b0), .f_td({FLIT{1'b0}}), .t_tg(), .f_sv(s_sv), .f_sd(s_sd), .t_sg(s_sg),
        .f_acc({AW{1'b0}}), .lo_v(hS_lov), .lo_r(hS_lor), .lo_d(hS_lod), .li_v(hS_liv), .li_r(hS_lir), .li_d(hS_lid),
        .t_rtv(), .t_rtd(), .f_rtg(1'b0), .t_rsv(), .t_rsd(), .f_rsg(1'b0), .t_racc(hS_racc), .f_lflt(3'b0));
    dsfd_coll_mtp_lane u_pS (.ck(fclk), .rs(rst_n), .f_tv(1'b0), .f_td({FLIT{1'b0}}), .t_tg(), .f_sv(1'b0), .f_sd({SW{1'b0}}), .t_sg(),
        .f_acc({AW{1'b0}}), .lo_v(pS_lov), .lo_r(pS_lor), .lo_d(pS_lod), .li_v(pS_liv), .li_r(pS_lir), .li_d(pS_lid),
        .t_rtv(), .t_rtd(), .f_rtg(1'b0), .t_rsv(pS_rsv), .t_rsd(pS_rsd), .f_rsg(pS_rsg), .t_racc(pS_racc), .f_lflt(3'b0));
    wv_lane #(.LL(LL)) l_hp (.clk(fclk), .rst_n(rst_n), .a_v(hS_lov), .a_d(hS_lod), .a_c(hS_lor), .b_v(pS_liv), .b_d(pS_lid), .b_c(pS_lir), .fault(lane_ft[2]));
    wv_lane #(.LL(LL)) l_ph (.clk(fclk), .rst_n(rst_n), .a_v(pS_lov), .a_d(pS_lod), .a_c(pS_lor), .b_v(hS_liv), .b_d(hS_lid), .b_c(hS_lir), .fault(lane_ft[3]));

    // ------------------------------------------------------------------ primary die: seed launch, row store, seed_ctl stub
    wire [SW:0] sl_mrs; wire sl_mrsg;
    wv_relay #(.W(SW+1), .N(SF)) r_sl (.clk(fclk), .rst_n(rst_n), .d({pS_rsd, pS_rsv}), .q(sl_mrs));
    wv_relay #(.W(1), .N(SR)) r_slg (.clk(fclk), .rst_n(rst_n), .d(sl_mrsg), .q(pS_rsg));
    wire [24:0] t_vrq, vrq_far; wire vg_far, vg_near; wire [1024:0] t_vrs, vrs_near;
    wire [1024:0] t_x, x_far; wire [1:0] f_x; reg [1:0] x_join = 0; wire [PW:0] t_ps; wire [3:0] sl_flt; wire [2:0] hr_flt;
    dsfd_mtp_seed_launch #(.NW(NW), .USER_W(USER_W), .VM_AW(24), .FWD_C(SF), .RET_C(SR)) u_sl (.ck(fclk), .rst(rst_n),
        .f_mrs(sl_mrs), .t_mrs(sl_mrsg), .f_clr({USER_W'(0), 1'b0}), .t_vrq(t_vrq), .f_vrq(vg_near), .f_vrs(vrs_near),
        .t_x(t_x), .f_x(f_x), .t_ps(t_ps), .t_flt(sl_flt));
    wv_relay #(.W(25), .N(QF)) r_qf (.clk(fclk), .rst_n(rst_n), .d(t_vrq), .q(vrq_far));
    wv_relay #(.W(1), .N(QR)) r_qr (.clk(fclk), .rst_n(rst_n), .d(vg_far), .q(vg_near));
    wv_relay #(.W(1025), .N(QR)) r_qs (.clk(fclk), .rst_n(rst_n), .d(t_vrs), .q(vrs_near));
    wire [514:0] hp_far [1:3]; wire [3:1] hp_g;
    generate for (gd = 1; gd <= 3; gd = gd + 1) begin : g_hp
        wv_relay #(.W(515), .N(PF)) r_p (.clk(fclk), .rst_n(rst_n), .d({h_ld[gd], h_lv[gd]}), .q(hp_far[gd]));
        wv_relay #(.W(1), .N(PR)) r_pg (.clk(fclk), .rst_n(rst_n), .d(hp_g[gd]), .q(h_lg[gd]));
    end endgenerate
    dsfd_mtp_hrow #(.NW(NW), .USER_W(USER_W), .AW(24), .FWD_P(PF), .RET_P(PR), .FWD_Q(QF), .RET_Q(QR)) u_hr (.ck(fclk), .rst(rst_n),
        .f_hp0(hp_far[1]), .f_hp1(hp_far[2]), .f_hp2(hp_far[3]), .t_hpg({hp_g[3], hp_g[2], hp_g[1]}),
        .f_vrq(vrq_far), .t_vrq(vg_far), .t_vrs(t_vrs), .f_clr({USER_W'(0), 1'b0}), .t_flt(hr_flt));
    wv_relay #(.W(1025), .N(XH)) r_xf (.clk(fclk), .rst_n(rst_n), .d(t_x), .q(x_far));
    wv_relay #(.W(2), .N(XH)) r_xr (.clk(fclk), .rst_n(rst_n), .d(x_join), .q(f_x));
    // seed descriptors as they leave the sequencer (the expected seed rows / program starts)
    integer sd_n = 0, sd_u [0:63], sd_anc [0:63], sd_nrow [0:63], sd_y [0:63], sd_ep [0:63], sd_t [0:63];
    integer sc_d = 0, sc_pos = -1, sc_beat = 0, sc_t = -1, sc_rows = 0;      // seed_ctl stub: descriptor / position / beat
    always @(posedge fclk) if (rst_n) begin
        x_join[1] <= 1'b0;
        x_join[0] <= (sc_t < 0 && sc_beat == 0);
        if (x_far[0]) begin
            if (sc_d >= sd_n) fail("seed beat without a descriptor");
            else begin
                if (sc_pos < 0) sc_pos = (sd_nrow[sc_d] > 256) ? sd_anc[sc_d] + 1 - 256 : sd_anc[sc_d] - sd_nrow[sc_d] + 1;
                if (x_far[1024:1] !== wv_beat(sc_beat / 80, sc_pos, (sc_pos < plen) ? tru[sc_pos] : tru[sc_pos], sc_beat % 80)) begin
                    $display("WAVE FAIL: seed beat %0d of pos %0d (descriptor %0d) is not the committed row", sc_beat, sc_pos, sc_d);
                    errs = errs + 1;
                end
                sc_beat = sc_beat + 1;
                if (sc_beat == 240) begin sc_beat = 0; sc_t = cyc + T_SC; end
            end
        end
        if (sc_t >= 0 && cyc >= sc_t) begin
            sc_t = -1; x_join[1] <= 1'b1; sc_rows = sc_rows + 1;
            if (sc_pos == sd_anc[sc_d]) begin sc_pos = -1; sc_d = sc_d + 1; end else sc_pos = sc_pos + 1;
        end
    end

    // ------------------------------------------------------------------ draft die A: P2 transactions (primary-driven)
    reg [31:0] p2in [0:3839]; reg [31:0] p2gold [0:1279];
    localparam [73:0] IDN0 = 74'h12345678; localparam [26:0] IDS = {9'd127, 9'd65, 9'd3};
    function automatic [511:0] p2flit(input integer e, input integer w);
        integer s; begin for (s = 0; s < 16; s = s + 1) p2flit[32*s +: 32] = p2in[e*1280 + w*16 + s]; end
    endfunction
    function automatic [603:0] l1w(input integer n); integer w; reg [73:0] id; begin w = n % 80; id = IDN0 + n / 80;
        l1w = {id, 9'd3, 1'b0, w == 79, 7'(w), p2flit(0, w)}; end endfunction
    function automatic [603:0] l0w(input integer n); integer kk; reg [73:0] id; begin kk = n % 160; id = IDN0 + n / 160;
        l0w = kk < 80 ? {id, 9'd127, 1'b0, kk == 79, 7'(kk), p2flit(2, kk)} : {id, 9'd65, 1'b0, kk == 159, 7'(kk - 80), p2flit(1, kk - 80)}; end
    endfunction
    reg ps_v = 0, l1_v = 0, l0_v = 0; wire ps_r, l1_r, l0_r; integer p2_tx = 0, p2_rows = 0, p2_open = 0; reg [31:0] p2_s1 = 0, p2_s0 = 0;
    wire pr_rv; wire [593:0] pr_rd; wire [2:0] pr_ev; wire [5:0] p2l_ft;
    // primary end (board lane W4) and die B end (UCIe lane E4): the far lane ends of draft die A's adapters
    wire pP_lov, pP_lor, pP_liv, pP_lir, aP_lov, aP_lor, aP_liv, aP_lir, bB_lov, bB_lor, bB_liv, bB_lir, aB_lov, aB_lor, aB_liv, aB_lir;
    wire [552:0] pP_lod, pP_lid, aP_lod, aP_lid, bB_lod, bB_lid, aB_lod, aB_lid;
    dsfd_coll_p2_lane #(.TXK(6), .TXW(101), .RXK(7), .RXW(594), .EVT(1), .EVR(3), .CRED(8), .TCRED(8)) u_pP (
        .ck(fclk), .rs(rst_n), .x_v(ps_v), .x_r(ps_r), .x_d({IDN0 + p2_tx, IDS}), .r_v(pr_rv), .r_r(1'b1), .r_d(pr_rd),
        .x_ev(1'b0), .r_ev(pr_ev), .lo_v(pP_lov), .lo_r(pP_lor), .lo_d(pP_lod), .li_v(pP_liv), .li_r(pP_lir), .li_d(pP_lid),
        .f_lflt(3'b0), .t_flt(p2l_ft[0]));
    dsfd_coll_p2_lane #(.TXK(5), .TXW(604), .RXK(0), .RXW(0), .EVT(0), .EVR(0), .CRED(0), .TCRED(0)) u_bB (
        .ck(fclk), .rs(rst_n), .x_v(l1_v), .x_r(l1_r), .x_d(l1w(p2_s1)), .r_v(), .r_r(1'b0), .r_d(),
        .x_ev(1'b0), .r_ev(), .lo_v(bB_lov), .lo_r(bB_lor), .lo_d(bB_lod), .li_v(bB_liv), .li_r(bB_lir), .li_d(bB_lid),
        .f_lflt(3'b0), .t_flt(p2l_ft[1]));
    wv_lane #(.LL(LL)) l_pa (.clk(fclk), .rst_n(rst_n), .a_v(pP_lov), .a_d(pP_lod), .a_c(pP_lor), .b_v(aP_liv), .b_d(aP_lid), .b_c(aP_lir), .fault(p2l_ft[2]));
    wv_lane #(.LL(LL)) l_ap (.clk(fclk), .rst_n(rst_n), .a_v(aP_lov), .a_d(aP_lod), .a_c(aP_lor), .b_v(pP_liv), .b_d(pP_lid), .b_c(pP_lir), .fault(p2l_ft[3]));
    wv_lane #(.LL(LL)) l_ba (.clk(fclk), .rst_n(rst_n), .a_v(bB_lov), .a_d(bB_lod), .a_c(bB_lor), .b_v(aB_liv), .b_d(aB_lid), .b_c(aB_lir), .fault(p2l_ft[4]));
    wv_lane #(.LL(LL)) l_ab (.clk(fclk), .rst_n(rst_n), .a_v(aB_lov), .a_d(aB_lod), .a_c(aB_lor), .b_v(bB_liv), .b_d(bB_lid), .b_c(bB_lir), .fault(p2l_ft[5]));
    // die A: lane adapters (hardened masters), collective P2 end, P2 slab (link ends + core) over draft-A stations
    wire a_sv, a_sr, a_ov, a_or; wire [100:0] a_sd; wire [593:0] a_od; wire [2:0] a_ev; wire a_ab; wire [1:0] a_ft;
    wire b1_v, b1_r; wire [603:0] b1_d;
    dsfd_coll_p2_lane_pa u_pa (.ck(fclk), .rs(rst_n), .x_v(a_ov), .x_r(a_or), .x_d(a_od), .r_v(a_sv), .r_r(a_sr), .r_d(a_sd),
        .x_ev(a_ev), .r_ev(a_ab), .lo_v(aP_lov), .lo_r(aP_lor), .lo_d(aP_lod), .li_v(aP_liv), .li_r(aP_lir), .li_d(aP_lid),
        .f_lflt(3'b0), .t_flt(a_ft[0]));
    dsfd_coll_p2_lane_ba u_ba (.ck(fclk), .rs(rst_n), .r_v(b1_v), .r_r(b1_r), .r_d(b1_d),
        .lo_v(aB_lov), .lo_r(aB_lor), .lo_d(aB_lod), .li_v(aB_liv), .li_r(aB_lir), .li_d(aB_lid), .f_lflt(3'b0), .t_flt(a_ft[1]));
    wire ce_sv, ce_sg, ce_ov, ce_og; wire [100:0] ce_sd; wire [593:0] ce_od;
    dsfd_coll_p2_ep #(.FWD_C(P2FC), .RET_C(P2RC)) u_cpe (.ck(fclk), .rst(rst_n), .c_sv(a_sv), .c_sr(a_sr), .c_sd(a_sd),
        .t_sv(ce_sv), .t_sd(ce_sd), .f_sg(ce_sg), .f_ov(ce_ov), .f_od(ce_od), .t_og(ce_og), .c_ov(a_ov), .c_or(a_or), .c_od(a_od));
    wire v0_v, v0_g; wire [603:0] v0_d;
    // The VM endpoint receives unhandshaked memory returns, RL edges after
    // an issue accepted by its registered credit. A held valid request is not
    // itself a returned beat.
    wire vm0_ret_v; wire [603:0] vm0_ret_d;
    wv_vm_p2_returns #(.RL(4)) vm0_returns (.clk(fclk), .rst_n(rst_n),
        .issue_v(l0_v), .issue_r(l0_r), .issue_d(l0w(p2_s0)), .ret_v(vm0_ret_v), .ret_d(vm0_ret_d));
    dsfd_vm_p2_ep u_vpe (.ck(fclk), .rst(rst_n), .c_l0v(vm0_ret_v), .c_l0r(l0_r), .c_l0d(vm0_ret_d), .t_l0v(v0_v), .t_l0d(v0_d), .f_l0g(v0_g));
    wire q_l0v, q_l0g, q_l1v, q_l1g, q_sv, q_sg, q_ov, q_og, q_done, q_fault, q_corr; wire [603:0] q_l0d, q_l1d; wire [100:0] q_sd; wire [593:0] q_od;
    wv_relay #(.W(605), .N(P2FV)) r20 (.clk(fclk), .rst_n(rst_n), .d({v0_v, v0_d}), .q({q_l0v, q_l0d}));
    wv_relay #(.W(1), .N(P2RV)) r20g (.clk(fclk), .rst_n(rst_n), .d(q_l0g), .q(v0_g));
    wv_relay #(.W(605), .N(P2FC)) r21 (.clk(fclk), .rst_n(rst_n), .d({b1_v, b1_d}), .q({q_l1v, q_l1d}));
    wv_relay #(.W(1), .N(P2RC)) r21g (.clk(fclk), .rst_n(rst_n), .d(q_l1g), .q(b1_r));
    wv_relay #(.W(102), .N(P2FC)) r2s (.clk(fclk), .rst_n(rst_n), .d({ce_sv, ce_sd}), .q({q_sv, q_sd}));
    wv_relay #(.W(1), .N(P2RC)) r2sg (.clk(fclk), .rst_n(rst_n), .d(q_sg), .q(ce_sg));
    wv_relay #(.W(595), .N(P2RC)) r2o (.clk(fclk), .rst_n(rst_n), .d({q_ov, q_od}), .q({ce_ov, ce_od}));
    wv_relay #(.W(1), .N(P2FC)) r2og (.clk(fclk), .rst_n(rst_n), .d(ce_og), .q(q_og));
    wv_relay #(.W(3), .N(P2RC)) r2ev (.clk(fclk), .rst_n(rst_n), .d({q_corr, q_fault, q_done}), .q(a_ev));
    dsfd_p2_rtt #(.FWD_V(P2FV), .RET_V(P2RV), .FWD_C(P2FC), .RET_C(P2RC)) u_p2 (.ck(fclk), .rst(rst_n),
        .f_l0v(q_l0v), .f_l0d(q_l0d), .t_l0g(q_l0g), .f_l1v(q_l1v), .f_l1d(q_l1d), .t_l1g(q_l1g), .f_sv(q_sv), .f_sd(q_sd), .t_sg(q_sg),
        .t_ov(q_ov), .t_od(q_od), .f_og(q_og), .f_abort(1'b0), .t_done(q_done), .t_fault(q_fault), .t_corrected(q_corr));
    // primary-side controller: program start -> 3 x (T_BLK block compute, P2 transaction) -> rows ready to the sequencer
    integer ps_q = 0, ps_seen = 0, blk = -1, blk_t = -1, done_n = 0, rows_rdy = 0; reg pr_done_q = 0;
    integer ps_word [0:63];
    always @(posedge fclk) if (rst_n) begin
        if (t_ps[0]) begin
            if (ps_q >= sd_n || t_ps[PW:1] !== {USER_W'(sd_u[ps_q]), NW'(sd_anc[ps_q]), NW'(sd_y[ps_q]), 4'(sd_ep[ps_q])})
                fail("program start != the descriptor");
            ps_q = ps_q + 1;
        end
        if (blk < 0 && ps_seen < ps_q) begin ps_seen = ps_seen + 1; blk = 0; blk_t = cyc + T_BLK; end
        if (blk >= 0 && !p2_open && blk_t >= 0 && cyc >= blk_t) begin ps_v <= 1'b1; p2_open = 1; blk_t = -1; end
        if (ps_v && ps_r) begin ps_v <= 1'b0; end
        l1_v <= p2_open && p2_s1 + (l1_v && l1_r) < 80 * (p2_tx + 1);
        l0_v <= p2_open && p2_s0 + (l0_v && l0_r) < 160 * (p2_tx + 1);
        if (l1_v && l1_r) p2_s1 <= p2_s1 + 1;
        if (l0_v && l0_r) p2_s0 <= p2_s0 + 1;
        pr_done_q <= pr_ev[0];
        if (pr_ev[0] && !pr_done_q) done_n = done_n + 1;
        if (pr_ev[1]) fail("P2 core fault at the primary");
        if (pr_rv) begin
            if (pr_rd[81:8] !== IDN0 + p2_tx || pr_rd[7:1] !== 7'(p2_rows) || pr_rd[0] !== (p2_rows == 79)) fail("P2 row metadata");
            for (k = 0; k < 16; k = k + 1) if (pr_rd[82 + 32*k +: 32] !== p2gold[p2_rows * 16 + k]) fail("P2 row numeric");
            p2_rows = p2_rows + 1;
        end
        if (p2_open && p2_rows == 80 && done_n == p2_tx + 1) begin
            p2_open = 0; p2_rows = 0; p2_tx = p2_tx + 1; blk = blk + 1;
            if (blk == 3) begin blk = -1; bw_v <= 1'b1; bw_d <= 0; rows_rdy = rows_rdy + 1; end
            else blk_t = cyc + T_BLK;
        end
        if (bw_v && bw_r) bw_v <= 1'b0;
    end

    // ------------------------------------------------------------------ draft head: Markov join (real row) + sweep stub
    reg [255:0] mk_w [0:767]; reg [255:0] mk_x [0:767]; reg [31:0] mk_h [0:47]; reg [31:0] mk_g [0:47];
    reg mk_start = 0, mk_iv = 0, mk_ordy = 0; reg [31:0] mk_head = 0; reg [255:0] mk_wb = 0, mk_xb = 0;
    wire mk_sr, mk_ir, mk_ov, mk_flt; wire [31:0] mk_out;
    ot_dsrom_markov_row #(.K(256), .PINREG(1)) u_mk (.clk(fclk), .rst_n(rst_n), .start(mk_start), .start_ready(mk_sr),
        .head_logit(mk_head), .in_valid(mk_iv), .in_ready(mk_ir), .weight_bf16(mk_wb), .embed_bf16(mk_xb),
        .out_valid(mk_ov), .out_ready(mk_ordy), .out_bits(mk_out), .fault(mk_flt));
    integer drafts [0:4]; integer sd_last_y = 0, sd_last_anc = 0, n_seed = 0, a_cur = 0;
    integer dh_st = 0, dh_u, dh_j, dh_n = 0, mk_n = 0, mk_b = 0, mk_t0 = 0, dh_t = -1;
    integer mk_lat_n = 0, mk_lat_sum = 0;
    always @(posedge fclk) if (rst_n) begin
        mk_start <= 1'b0; mk_ordy <= 1'b0;
        if (bq_v && bq_r) bq_v <= 1'b0;
        case (dh_st)
            0: if (bh_v) begin
                   dh_u = bh_d[DW-1 -: USER_W]; dh_j = bh_d[NW +: 3];
                   if (dh_j < 1 || dh_j > 5 || bh_d[NW-1:0] != ((dh_j == 1) ? sd_last_y : drafts[dh_j - 2])) fail("draft-head step prev token");
                   dh_n = dh_n + 1; dh_st = 1;
               end
            1: if (mk_sr) begin mk_start <= 1'b1; mk_head <= mk_h[mk_n % 48]; mk_t0 = cyc + 1; mk_b = 0; dh_st = 2; end
            2: begin
                   if (mk_iv && mk_ir) mk_b = mk_b + 1;
                   if (mk_b < 16) begin mk_iv <= 1'b1; mk_wb <= mk_w[(mk_n % 48) * 16 + mk_b]; mk_xb <= mk_x[(mk_n % 48) * 16 + mk_b]; end
                   else mk_iv <= 1'b0;
                   if (mk_ov) begin
                       if (mk_out !== mk_g[mk_n % 48]) fail("Markov join != gold");
                       mk_lat_sum = mk_lat_sum + (cyc - mk_t0); mk_lat_n = mk_lat_n + 1;
                       mk_ordy <= 1'b1; mk_n = mk_n + 1; dh_t = cyc + T_HX; dh_st = 3; mk_iv <= 1'b0;
                   end
               end
            3: if (cyc >= dh_t) begin
                   bq_v <= 1'b1; bq_d <= {USER_W'(dh_u), 3'(dh_j), NW'(drafts[dh_j - 1])}; dh_st = 0;
               end
        endcase
        if (mk_flt) fail("Markov row fault");
    end

    // ------------------------------------------------------------------ accept: commit / rollback broadcast + history rings
    reg cm_pass = 0, cm_acc = 0, cm_pre = 0; reg [31:0] cm_q = 0, cm_pren = 0; reg [3:0] cm_g = 0, cm_a = 0;
    wire cm_nset, cm_sq, cm_err; wire [31:0] cm_n, cm_qn, cm_sf, cm_st; wire [7:0] cm_ep;
    ot_mtp_commit u_cm (.clk(fclk), .rst_n(rst_n), .pass_v(cm_pass), .pass_q(cm_q), .pass_g(cm_g), .acc_done(cm_acc), .acc_a(cm_a),
        .pre_v(cm_pre), .pre_n(cm_pren), .n_set(cm_nset), .n_val(cm_n), .q_next(cm_qn), .squash_v(cm_sq), .squash_from(cm_sf),
        .squash_to(cm_st), .epoch(cm_ep), .err(cm_err));
    reg hw_v = 0, hr_v = 0; reg [31:0] hw_pos = 0, hr_pos = 0; reg [16:0] hw_tok = 0;
    wire h0_rdy, h0_v, h0_pad, h0_last, h0_err, h1_rdy, h1_v, h1_pad, h1_last, h1_err; wire [16:0] h0_tok, h1_tok;
    ot_mtp_hist_ring u_h0 (.clk(fclk), .rst_n(rst_n), .n_set(cm_nset), .n_val(cm_n), .tw_v(hw_v), .tw_pos(hw_pos), .tw_tok(hw_tok),
        .rd_v(hr_v && h1_rdy), .rd_ready(h0_rdy), .rd_pos(hr_pos), .h_v(h0_v), .h_tok(h0_tok), .h_pad(h0_pad), .h_last(h0_last), .err(h0_err));
    ot_mtp_hist_ring_p u_h1 (.clk(fclk), .rst_n(rst_n), .n_set(cm_nset), .n_val(cm_n), .tw_v(hw_v), .tw_pos(hw_pos), .tw_tok(hw_tok),
        .rd_v(hr_v && h0_rdy), .rd_ready(h1_rdy), .rd_pos(hr_pos), .h_v(h1_v), .h_tok(h1_tok), .h_pad(h1_pad), .h_last(h1_last), .err(h1_err));

    // ------------------------------------------------------------------ twin: P2 link ends vs the core driven directly
    wire [1:0] tw_done; integer tw_cyc [0:1][0:2];
    wv_p2twin #(.LNK(0)) u_tw0 (.clk(fclk), .rst_n(rst_n), .done(tw_done[0]));
    wv_p2twin #(.LNK(1)) u_tw1 (.clk(fclk), .rst_n(rst_n), .done(tw_done[1]));

    // ------------------------------------------------------------------ the loop's checks (sequencer pins, committed tokens)
    integer emitted = 0, last_pos, acc_n = 0, bq_exp = 0, bg_exp = 0, exa, xw, n_g5 = 0;
    integer t_rin [0:MAXP-1]; integer t_win = -1, t_qin = -1, t_qlast = -1;
    integer n_rw = 0, s_rw = 0, n_dh = 0, s_dh = 0, n_sac = 0, s_sac = 0, n_ldf = 0, s_ldf = 0;
    integer hw_q [0:63], hp_q [0:63], hwn = 0, hwr = 0, hr_list [0:15], hr_n = 0, hr_i = 0, hr_k = 0, h_pass_q = 0;
    integer h_tok [0:MAXP-1]; integer h_rd_n = 0, h_rd_tok = 0, h_rd_cyc = 0, h_t0 = -1; integer h1_t0 = -1, h1_tok_n = 0, h1_cyc = 0;
    integer rv_since_q = 0, n_ldc = 0, s_ldc = 0;
    integer h_hold = 0, cm_pend = 0; reg h_errd = 0;
    integer cm_t = -1, cm_lat_sum = 0, cm_lat_n = 0, cm_xw = 0, cm_aa = 0, cm_gg = 0;
    always @(posedge fclk) if (rst_n) begin
        cm_pass <= 1'b0; cm_acc <= 1'b0; cm_pre <= 1'b0; hw_v <= 1'b0; hr_v <= 1'b0;
        // committed tokens from the S0 kit
        if (t_tok[52] && t_tok[2*NW-1:NW] >= plen - 1) begin
            if (t_tok[2*NW-1:NW] != last_pos + 1) fail("committed position out of order");
            last_pos = t_tok[2*NW-1:NW];
            if (t_tok[NW-1:0] != tru[last_pos + 1]) begin
                $display("WAVE FAIL: committed pos %0d token %0d != greedy %0d", last_pos, t_tok[NW-1:0], tru[last_pos + 1]); errs = errs + 1;
            end
            emitted = emitted + 1;
        end
        // accept words (the sequencer's t_acc)
        if (s_acc[2*NW+3+USER_W]) begin
            exa = s_acc[2*NW +: 3]; xw = s_acc[NW +: NW];
            if (VERB) $display("WAVE_DBG close %0d at pos %0d a %0d (bq %0d bg %0d d0 %0d tru %0d) at %0d", acc_n, xw, exa, bq_exp, bg_exp, drafts[0], tru[bq_exp + 1], cyc);
            if (acc_n == 0) begin
                if (xw != plen - 1 || exa != 0) fail("prefill close");
                cm_pre <= 1'b1; cm_pren <= plen;
            end else begin
                exa = 0;
                while (exa < bg_exp && drafts[exa] == tru[bq_exp + 1 + exa]) exa = exa + 1;
                if (s_acc[2*NW +: 3] != exa || xw != bq_exp + exa) begin
                    $display("WAVE FAIL: closed at %0d a %0d, expected %0d a %0d", xw, s_acc[2*NW +: 3], bq_exp + exa, exa); errs = errs + 1;
                end
                if (bg_exp == 5) n_g5 = n_g5 + 1;
                cm_acc <= 1'b1; cm_a <= s_acc[2*NW +: 3]; cm_t = cyc + 1; cm_xw = xw; cm_aa = s_acc[2*NW +: 3];
            end
            bq_exp = xw + 1; bg_exp = (xw + 1 >= steps) ? 0 : (steps - 1 - (xw + 1) < 5) ? steps - 1 - (xw + 1) : 5;
            acc_n = acc_n + 1;
            h_hold = 8;
        end
        // RESULT arrivals at the sequencer pin (seed_after_close)
        if (p_rv) t_rin[p_rd[HDR_POS +: NW] % MAXP] = cyc;
        // seeds leaving the sequencer pin
        if (p_sv) begin
            sd_u[sd_n] = p_sd[SW-1 -: USER_W]; sd_anc[sd_n] = p_sd[3*NW+3 -: NW]; sd_nrow[sd_n] = p_sd[2*NW+3 -: NW];
            sd_y[sd_n] = p_sd[NW+3 -: NW]; sd_ep[sd_n] = p_sd[3:0]; sd_t[sd_n] = cyc;
            if (sd_y[sd_n] != tru[sd_anc[sd_n] + 1]) fail("seed bonus != greedy");
            n_sac = n_sac + 1; s_sac = s_sac + (cyc - t_rin[sd_anc[sd_n] % MAXP]);
            sd_last_y = sd_y[sd_n]; sd_last_anc = sd_anc[sd_n];
            a_cur = PAT[n_seed % 12];
            for (k = 0; k < 5; k = k + 1)
                drafts[k] = (k < a_cur) ? tru[sd_anc[sd_n] + 2 + k] : (tru[sd_anc[sd_n] + 2 + k] + 1 + k) % V;
            n_seed = n_seed + 1;
            if (VERB) $display("WAVE_DBG seed %0d anc %0d nrow %0d y %0d ep %0d a %0d g %0d at %0d", sd_n, sd_anc[sd_n], sd_nrow[sd_n], sd_y[sd_n], sd_ep[sd_n], a_cur, bg_exp, cyc);
            // commit: a pass starts at this anchor with g drafts
            cm_pend = 3; cm_q <= sd_anc[sd_n]; cm_g <= bg_exp; cm_gg = bg_exp;      // the pass starts after the commit broadcast
            // history: the pass's tokens y, d1..dg at q+1 .. q+1+g, then a read at every pass position
            h_pass_q = sd_anc[sd_n];
            hw_q[hwn % 64] = sd_y[sd_n]; hp_q[hwn % 64] = sd_anc[sd_n] + 1; hwn = hwn + 1;
            h_tok[sd_anc[sd_n] + 1] = sd_y[sd_n];
            for (k = 0; k < bg_exp; k = k + 1) begin
                hw_q[hwn % 64] = drafts[k]; hp_q[hwn % 64] = sd_anc[sd_n] + 2 + k; hwn = hwn + 1;
                h_tok[sd_anc[sd_n] + 2 + k] = drafts[k];
            end
            for (k = 0; k <= bg_exp; k = k + 1) hr_list[k] = sd_anc[sd_n] + 1 + k;
            hr_n = bg_exp + 1; hr_i = 0;
            sd_n = sd_n + 1;
        end
        // draft chain at the sequencer pins
        if (p_wv) t_win = cyc;
        if (p_qv) begin t_qin = cyc; t_qlast = cyc; rv_since_q = 0; end
        if (p_hv) begin
            if (p_hd[NW +: 3] == 1) begin n_rw = n_rw + 1; s_rw = s_rw + (cyc - t_win); end
            else begin n_dh = n_dh + 1; s_dh = s_dh + (cyc - t_qin); end
        end
        if (p_rv) rv_since_q = rv_since_q + 1;
        if (p_tv && p_td[HDR_TYPE +: 4] == 4'd4) begin
            n_ldf = n_ldf + 1; s_ldf = s_ldf + (cyc - t_qlast);
            // the price's condition (s0_hash_u1_fast): no squashed verify result still arriving after the last draft head
            if (rv_since_q == 0 && pq_r == pq_w) begin n_ldc = n_ldc + 1; s_ldc = s_ldc + (cyc - t_qlast); end
        end
        if (s_acc[2*NW+USER_W+4]) fail("sequencer fault");
        // commit outputs
        if (cm_nset && cm_t >= 0) begin
            cm_lat_sum = cm_lat_sum + (cyc - cm_t); cm_lat_n = cm_lat_n + 1; cm_t = -1;
            if (cm_n != cm_xw + 1 || cm_qn != cm_xw || cm_sq != (cm_aa != cm_gg)) fail("commit n / q_next / squash");
        end
        if (cm_err) fail("commit err");
        // history ring: writes then reads (both rings in lockstep), every streamed token checked
        if (cm_pend > 0) begin cm_pend = cm_pend - 1; if (cm_pend == 0) cm_pass <= 1'b1; end
        if (cm_nset) h_hold = 4; else if (h_hold > 0) h_hold = h_hold - 1;
        if (hwr < hwn && h_hold == 0) begin hw_v <= 1'b1; hw_pos <= hp_q[hwr % 64]; hw_tok <= hw_q[hwr % 64]; if (VERB) $display("WAVE_DBG hwrite pos %0d tok %0d at %0d", hp_q[hwr % 64], hw_q[hwr % 64], cyc); hwr = hwr + 1; end
        else if (hwr == hwn && h_hold == 0 && hr_i < hr_n && h0_rdy && h1_rdy && !hr_v) begin hr_v <= 1'b1; hr_pos <= hr_list[hr_i]; hr_i = hr_i + 1; if (h_t0 < 0) h_t0 = cyc + 1; end
        if ((h0_err || h1_err) && !h_errd) begin fail("history ring err"); h_errd = 1; end
    end
    // ------------------------------------------------------------------ fault watch
    always @(posedge fclk) if (rst_n) begin
        if (s0_ft || (|stg_ft) || (|stub_bad) || (|lane_ft) || (|p2l_ft) || (|a_ft) || q_fault || (|sl_flt) || (|hr_flt)
            || sT_racc[AW-1] || hT_racc[AW-1] || pS_racc[AW-1] || hS_racc[AW-1]) begin
            $display("WAVE FAIL: fault s0 %b stg %b stub %b lane %b p2l %b a %b p2core %b seedl %b hrow %b racc %b%b%b%b at %0d",
                     s0_ft, stg_ft, stub_bad, lane_ft, p2l_ft, a_ft, q_fault, sl_flt, hr_flt,
                     sT_racc[AW-1], hT_racc[AW-1], pS_racc[AW-1], hS_racc[AW-1], cyc);
            $finish;
        end
        if (errs > 20) begin $display("WAVE FAIL: too many errors"); $finish; end
    end

    // ------------------------------------------------------------------ adapter traversal timing (mtp_lane / p2 lanes)
    `include "tb_mtp_wave_meas.svh"

    // ------------------------------------------------------------------ setup / run / report
    task cfgw_put(input [1:0] sel, input integer uu, input integer pp, input integer vv);
        begin @(negedge fclk); cfgw = {1'b1, sel, USER_W'(uu), NW'(pp), NW'(vv)}; @(negedge fclk); cfgw = 0; end
    endtask
    integer run_end;
    initial begin
        $readmemh("inputs.hex", p2in); $readmemh("gold.hex", p2gold);
        $readmemh("mk_w.hex", mk_w); $readmemh("mk_x.hex", mk_x); $readmemh("mk_head.hex", mk_h); $readmemh("mk_gold.hex", mk_g);
        plen = PLEN;
        ngen = 0; for (k = 0; k < NSTEPMAX; k = k + 1) ngen = ngen + PAT[k % 12] + 1;
        ngen = ngen + 1 + 6;                                   // the prefill token + a tail whose blocks are shorter than gamma
        steps = plen + ngen - 1;
        for (i = 0; i < plen; i = i + 1) begin
            tru[i] = wv_mix(1001 + i, 32'h51ed2701) % V;
            ph[i] = wv_mix(i == 0 ? 32'd5 : ph[i-1], tru[i]);
        end
        for (i = plen - 1; i + 1 < MAXP; i = i + 1) begin
            tru[i+1] = htok(ph[i]); ph[i+1] = wv_mix(ph[i], tru[i+1]);
        end
        last_pos = plen - 2;
        for (i = 0; i < plen; i = i + 1) begin hw_q[i] = tru[i]; hp_q[i] = i; end
        hwn = plen;
        cfgw_put(2'd0, 0, 0, 1); cfgw_put(2'd1, 0, 0, plen); cfgw_put(2'd2, 0, 0, ngen);
        for (i = 0; i < plen; i = i + 1) cfgw_put(2'd3, 0, i, tru[i]);
        repeat (8) @(posedge fclk);
        rst_n = 1;
        while (emitted < ngen && cyc < MAXC && errs == 0) begin
            @(posedge fclk);
            if (cyc % 200000 == 0) $display("WAVE_HB cyc=%0d emitted=%0d closes=%0d seeds=%0d p2_tx=%0d s4_jobs=%0d s0_jobs=%0d", cyc,
                                            emitted, acc_n, sd_n, p2_tx, s4.n_job, s0.n_job); $fflush;
        end
        repeat (400) @(posedge fclk);
        if (emitted < ngen) begin $display("WAVE FAIL: timeout at %0d cycles (emitted %0d of %0d)", cyc, emitted, ngen); errs = errs + 1; end
        if (tw_done !== 2'b11) begin $display("WAVE FAIL: P2 twin not done"); errs = errs + 1; end
        run_end = cyc;
        report();
        $display("WAVE %s steps=%0d g5_steps=%0d emitted=%0d seeds=%0d p2_tx=%0d markov=%0d seed_rows=%0d hrow_rows=%0d/%0d/%0d cycles=%0d errors=%0d",
                 errs == 0 ? "PASS" : "FAIL", acc_n, n_g5, emitted, sd_n, p2_tx, mk_n, sc_rows,
                 s1.g_hrow.rows_sent, s2.g_hrow.rows_sent, s3.g_hrow.rows_sent, cyc, errs);
        $finish;
    end
endmodule

// P2 twin (p2.link_ends price basis, tools/mtp_fixlat_gate.py p2_lat_direct0 / p2_lat_lnk0): NTX 3 back-to-back saturated
// transactions, rows always consumed; LNK 0 = ot_mtp_p2_prefix_path driven directly, LNK 1 = dsfd_p2_rtt (dsfd_p2_lnk + the
// core) at 0 stations with its partner ends.  Logs per transaction: start presented -> last row consumed.
module wv_p2twin #(parameter integer LNK = 0) (input wire clk, rst_n, output reg done);
    reg [31:0] inputs [0:3839]; reg [31:0] gold [0:1279];
    localparam [73:0] IDN0 = 74'h12345678; localparam [26:0] IDS = {9'd127, 9'd65, 9'd3};
    function automatic [511:0] flit(input integer e, input integer w);
        integer s; begin for (s = 0; s < 16; s = s + 1) flit[32*s +: 32] = inputs[e*1280 + w*16 + s]; end
    endfunction
    function automatic [603:0] l1w(input integer n); integer w; reg [73:0] id; begin w = n % 80; id = IDN0 + n / 80;
        l1w = {id, 9'd3, 1'b0, w == 79, 7'(w), flit(0, w)}; end endfunction
    function automatic [603:0] l0w(input integer n); integer kk; reg [73:0] id; begin kk = n % 160; id = IDN0 + n / 160;
        l0w = kk < 80 ? {id, 9'd127, 1'b0, kk == 79, 7'(kk), flit(2, kk)} : {id, 9'd65, 1'b0, kk == 159, 7'(kk - 80), flit(1, kk - 80)}; end
    endfunction
    initial begin $readmemh("inputs.hex", inputs); $readmemh("gold.hex", gold); end
    reg cs_v = 0, c1_v = 0, c0_v = 0; wire cs_r, c1_r, c0_r, co_v; wire [593:0] co_d; wire t_done, t_fault, t_corr;
    integer starts = 0, s1 = 0, s0 = 0, received = 0, cyc = 0, t0 = 0, i, open = 0;
    integer tx_cyc [0:2];
    generate if (LNK) begin : g_lnk
        wire l0v, l0g, l1v, l1g, sv, sg, ov, og; wire [603:0] l0d, l1d; wire [100:0] sd; wire [593:0] od;
        wire vm_ret_v; wire [603:0] vm_ret_d;
        wv_vm_p2_returns #(.RL(4)) vm_returns (.clk(clk), .rst_n(rst_n),
            .issue_v(c0_v), .issue_r(c0_r), .issue_d(l0w(s0)), .ret_v(vm_ret_v), .ret_d(vm_ret_d));
        dsfd_vm_p2_ep vme (.ck(clk), .rst(rst_n), .c_l0v(vm_ret_v), .c_l0r(c0_r), .c_l0d(vm_ret_d), .t_l0v(l0v), .t_l0d(l0d), .f_l0g(l0g));
        ot_dsrom_mtp_ltx_rc #(.W(604)) l1tx (.clk(clk), .rst_n(rst_n), .c_valid(c1_v), .c_ready(c1_r), .c_data(l1w(s1)),
            .l_valid(l1v), .l_ready(l1g), .l_data(l1d));
        dsfd_coll_p2_ep #(.FWD_C(0), .RET_C(0)) cle (.ck(clk), .rst(rst_n), .c_sv(cs_v), .c_sr(cs_r), .c_sd({IDN0 + starts, IDS}),
            .t_sv(sv), .t_sd(sd), .f_sg(sg), .f_ov(ov), .f_od(od), .t_og(og), .c_ov(co_v), .c_or(1'b1), .c_od(co_d));
        dsfd_p2_rtt #(.FWD_V(0), .RET_V(0), .FWD_C(0), .RET_C(0)) dut (.ck(clk), .rst(rst_n), .f_l0v(l0v), .f_l0d(l0d), .t_l0g(l0g),
            .f_l1v(l1v), .f_l1d(l1d), .t_l1g(l1g), .f_sv(sv), .f_sd(sd), .t_sg(sg), .t_ov(ov), .t_od(od), .f_og(og),
            .f_abort(1'b0), .t_done(t_done), .t_fault(t_fault), .t_corrected(t_corr));
    end else begin : g_direct
        wire [1:0] ir; wire [511:0] od; wire [73:0] oid; wire [6:0] ow; wire ol; reg rn = 0;
        always @(posedge clk) rn <= rst_n;
        wire [603:0] d1 = l1w(s1), d0 = l0w(s0);
        assign c0_r = ir[0]; assign c1_r = ir[1]; assign co_d = {od, oid, ow, ol};
        ot_mtp_p2_prefix_path #(.ENABLE(1), .REGB(1), .ROOTPIPE(1)) dut (.clk(clk), .rst_n(rst_n),
            .start_v(cs_v), .start_r(cs_r), .start_identity(IDN0 + starts), .start_ids(IDS),
            .in_v({c1_v, c0_v}), .in_r(ir), .in_identity({d1[603:530], d0[603:530]}), .in_expert({d1[529:521], d0[529:521]}),
            .in_shared({d1[520], d0[520]}), .in_last({d1[519], d0[519]}), .in_word({d1[518:512], d0[518:512]}),
            .in_data({d1[511:0], d0[511:0]}), .out_v(co_v), .out_r(1'b1), .out_data(od), .out_identity(oid), .out_word(ow),
            .out_last(ol), .abort(1'b0), .done(t_done), .fault(t_fault), .corrected(t_corr));
    end endgenerate
    always @(negedge clk) if (rst_n) begin
        cs_v = starts < 3 && !open;
        c1_v = open && s1 < 80 * starts;
        c0_v = open && s0 < 160 * starts;
    end
    always @(posedge clk) if (!rst_n) done <= 1'b0; else begin
        cyc <= cyc + 1;
        if (cs_v && cs_r) begin starts <= starts + 1; open <= 1; t0 <= cyc; end
        if (c1_v && c1_r) s1 <= s1 + 1;
        if (c0_v && c0_r) s0 <= s0 + 1;
        if (t_fault) begin $display("WAVE FAIL: P2 twin %0d fault", LNK); end
        if (co_v) begin
            if (co_d[81:8] !== IDN0 + received / 80 || co_d[7:1] !== 7'(received % 80)) $display("WAVE FAIL: P2 twin %0d row meta", LNK);
            for (i = 0; i < 16; i = i + 1) if (co_d[82 + 32*i +: 32] !== gold[(received % 80) * 16 + i]) $display("WAVE FAIL: P2 twin %0d row numeric", LNK);
            received <= received + 1;
            if (received % 80 == 79) begin tx_cyc[received / 80] = cyc + 1 - t0; open <= 0; if (received / 80 == 2) done <= 1'b1; end
        end
    end
endmodule

// VM memory-return model for P2: every granted request produces exactly one
// response after the endpoint's contracted RL cycles, even if credit drops.
module wv_vm_p2_returns #(parameter integer RL = 4) (
    input wire clk, rst_n, issue_v, issue_r,
    input wire [603:0] issue_d,
    output wire ret_v, output wire [603:0] ret_d
);
    reg [RL-1:0] valid_q;
    reg [603:0] data_q [0:RL-1];
    integer j;
    always @(posedge clk) begin
        if (!rst_n) valid_q <= 0;
        else valid_q <= {valid_q[RL-2:0], issue_v && issue_r};
        data_q[0] <= issue_d;
        for (j = 1; j < RL; j = j + 1) data_q[j] <= data_q[j-1];
    end
    assign ret_v = valid_q[RL-1];
    assign ret_d = data_q[RL-1];
endmodule
