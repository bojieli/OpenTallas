`timescale 1ns/1ps
// tb_qfd_tt_ctlm_i_psram (fe-push-qwen-1010, 2026-10-10; generated from the ot_qfd_tt_ctlm_i port list by the same
// recipe as tb_qfd_seq_su_bi_psram): LOCKSTEP equivalence of u1 (PSRAM U1_PSRAM, HQ2 U1_HQ2) against u0 (PSRAM 0 = the
// flop program store, HQ2 0).  Same stimulus to both: a random 64 x 1,024 program loaded through pw while idle, then
// h_start pulses (a reset every 400 cycles restarts the controller and keeps the store) and random inputs on every other
// port for NCYC cycles.  Every output, and the captured program word prog_q, must match on every cycle; the run must
// issue >= MINRD program reads.  Built with +define+OT_ICUT_NONFATAL: with the real ME unit (ot_qfd_tt_ctl) behind the
// in-tile shell and a random program, the ME unit's readiness can fall without a go, so the controller's ICUT check fires
// identically in u0 and u1 (counted as icut_stim, reported, not fatal); the comparison is still every output every cycle.
// Negative controls: PMUT = 1 (read one edge late) and U1_HQ2 = 2 (head overwrite) FAIL.
module tb_qfd_tt_ctlm_i_psram;
    parameter integer NCYC = 20000, SEED = 1, PMUT = 0, MINRD = 50, TW = 400;   // TW: cycles per token window
    parameter integer U1_PSRAM = 1, U1_HQ2 = 0;
    parameter integer U1_MEREG = 0, U1_RRG = 0, MOK = 0, U1_PCUT = 0;
    parameter integer PCOV = 0;
    parameter integer U1_AUD = 0;
    parameter integer DBGT = 0;     // el1011-q-seq debug: trace u1's MEREG 3 enable for DBGT cycles
    parameter integer DBGMX = 0;    // debug: print the first mx write of each window per DUT
    parameter integer DBGTX = 0;    // el1011-q-seq TXN debug: per-window stream counts and the cycles of mismatching events
    parameter integer DBGS = 7, DBGW = 0;   // DBGTX 2: print stream DBGS of window DBGW (value low 64 b)
    parameter integer TXT = 1;      // TXN: 1 = split-tree selects compared per level per wave (0 = the raw per-edge pattern, timing-dependent)
    parameter integer TXPC = 1;     // TXN port model: 1 = shifts on the DUT's engine edges (the ICG enable before the edge, as the real ports on
                                    // the exported gated clock); 0 = the earlier model (one edge late: its latency in engine edges then depends on
                                    // whether the previous edge clocked the engine -- a gap-dependent p_am alignment, not the design's)
    parameter integer TXRST = 1;    // el1011-q-seq TXN: the port model's reply pipeline is reset like the real port's valid line
    // el1013-qwen-small-masters r3b: TXN coverage refusal.  COVMASK bit s = stream s must carry >= MINEV events on BOTH
    // units over the run (else FAIL coverage): a transaction compare of streams that never fire is vacuous (the TP8 slot
    // bench passed its mutant with events on streams 0-2 only).
    parameter integer COVMASK = 0, MINEV = 1;
    parameter integer TXN = 0;      // el1011-q-seq: 1 = transaction-level compare (per-interface event streams, per reset window; MEREG 3 wakes +1)
    parameter integer PFMASK = 0;   // el1011-q-seq: 1 = p_f_e2 only while p_v_e2, scale_addr only while scale_re | scale_gre (valid/data): the
                                    //   port element registers it unconditionally but every use is behind raw_v / rv (valid/data contract)
    integer npfm = 0;   // el1011-q-seq: u1 textbook-audit rebuild (kv_ok / kv_write_drained one edge ahead for u1)   // el1011-q-seq: 1 = ME ops with DYN_TTILES (valid splits) and small chase targets (PCUT coverage)   // el1011-q-seq: u1 registered ME enable / replicated reset; MOK 1: random me_mem_ok (u1 sees it 2 edges ahead)
    reg clk = 0, rst_n = 1;
    initial #0.1 rst_n = 0;
    always #0.5 clk = ~clk;
    integer ndt = 0, nceq = 0;
    // qwen-tp8/seq (2026-10-12): TBG = the die's lane groups for BOTH instances (TP4 6,144 default; TP8 3,072), with the
    // G-sized ports (NPG = TBG >> 7 scale groups, NPE = NPG / 4 argmax partials, LGT = $clog2(TBG) tile-select bits).
    // GOLD (independent of the RTL's ot_hdc_dyn_ttiles): every u1 controller load of a DYN_TTILES ME op must set
    // me_tiles = ME_TILES + floor(pos / (16 * TBG / 2^split)) + 1 (valid splits); MINGC = minimum such checks for a PASS.
    // U1_TPMUT: ot_qfd_tt_ctlm_i TPMUT negative controls (1 = rounds at G 6144, 2 = controller at G 6144) must FAIL.
    parameter integer TBG = 6144, U1_TPMUT = 0, MINGC = 0;
    localparam integer NPG = TBG >> 7, NPE = NPG / 4, LGT = $clog2(TBG);
    integer ngc = 0, ngbad = 0;
    integer seed = SEED, cyc = 0, bad = 0, nrd = 0, nld = 0, nicut = 0, k, i;
    reg [11:0] pbase = 0;
    reg [15:0] xprog = 0, xrows = 0, lcnt = 0;
    reg [23:0] xacc = 0;
    reg  h_start = 0;
    reg [18-1:0] token = 0;
    reg [18-1:0] pos = 0;
    reg [11:0] prog_base = 0;
    reg  pw_v = 0;
    reg [9:0] pw_addr = 0;
    reg [63:0] pw_data = 0;
    reg [24-1:0] x_oacc = 0;
    reg  x_oidle = 0;
    reg [15:0] x_oprog = 0;
    reg [15:0] x_orows = 0;
    reg  kv_ok = 0;
    reg  kv_write_drained = 0;
    reg  me_mem_ok = 0;
    reg  mo_d1 = 1, mo_u0 = 1;   // el1011-q-seq: u0 sees me_mem_ok two edges after u1
    reg mo_d2 = 1;
    always @(posedge clk) begin mo_d1 <= me_mem_ok; mo_d2 <= mo_d1; mo_u0 <= (U1_MEREG >= 3) ? mo_d2 : mo_d1; end
    reg kv_d1 = 1, kvwd_d1 = 1;   // u0 sees kv_ok / kv_write_drained one edge after u1 when U1_AUD
    always @(posedge clk) begin kv_d1 <= kv_ok; kvwd_d1 <= kv_write_drained; end
    wire kv_u0 = ((U1_AUD & 4) != 0) ? kv_d1 : kv_ok, kvwd_u0 = ((U1_AUD & 4) != 0) ? kvwd_d1 : kv_write_drained;
    reg  up_fault = 0;
    reg [15:0] land_cnt = 0;
    reg  x_rdy = 0;
    reg [16-1:0] tr_fault = 0;
    reg [NPE*51-1:0] p_am = 0;
    reg [NPE-1:0] p_fault = 0;
    reg  fab_fault = 0;
    wire [24-1:0] me_acc_o_0, me_acc_o_1;
    wire  me_idle_o_0, me_idle_o_1;
    wire [15:0] me_prog_o_0, me_prog_o_1;
    wire  m_fin_o_0, m_fin_o_1;
    wire [18-1:0] m_fidx_o_0, m_fidx_o_1;
    wire [31:0] m_fval_o_0, m_fval_o_1;
    wire  kvd_v_0, kvd_v_1;
    wire [24-1:0] kvd_wbase_0, kvd_wbase_1;
    wire [24-1:0] kvd_ts_0, kvd_ts_1;
    wire [24-1:0] kvd_ks_0, kvd_ks_1;
    wire [24-1:0] kvd_js_0, kvd_js_1;
    wire [24-1:0] kvd_wcs_0, kvd_wcs_1;
    wire [3:0] kvd_split_0, kvd_split_1;
    wire [2:0] kvd_jsh_0, kvd_jsh_1;
    wire [18-1:0] kvd_tiles_0, kvd_tiles_1;
    wire [18-1:0] kvd_k_0, kvd_k_1;
    wire [18-1:0] kvd_nout_0, kvd_nout_1;
    wire  kvd_kindk_0, kvd_kindk_1;
    wire [18-1:0] kvd_pos_0, kvd_pos_1;
    wire  me_clk_en_0, me_clk_en_1;
    wire  c_fault_0, c_fault_1;
    wire  scale_re_0, scale_re_1;
    wire [NPG-1:0] scale_gre_0, scale_gre_1;
    wire [NPG*24-1:0] scale_addr_0, scale_addr_1;
    wire  x_dv_0, x_dv_1;
    wire [24-1:0] x_dc_0, x_dc_1;
    wire [24-1:0] x_dcs_0, x_dcs_1;
    wire [3:0] x_dsp_0, x_dsp_1;
    wire [LGT:0] t_sel_e_0, t_sel_e_1;
    wire [LGT:0] t_tv_e_0, t_tv_e_1;
    wire  p_v_e2_0, p_v_e2_1;
    wire [113-1:0] p_f_e2_0, p_f_e2_1;
    wire  ov_0, ov_1;
    wire  mx_we_0, mx_we_1;
    wire [24-1:0] mx_addr_0, mx_addr_1;
    wire [16-1:0] mx_mask_0, mx_mask_1;
    wire [16*32-1:0] mx_data_0, mx_data_1;
    // el1011-q-seq AUD 16: u0 sees the die-facing tree-top inputs one edge after u1 (u1 pin-flops them)
    reg [$bits(up_fault)-1:0] up_fault_d1; always @(posedge clk) up_fault_d1 <= up_fault;
    wire [$bits(up_fault)-1:0] up_fault_u0 = ((U1_AUD & 16) != 0) ? up_fault_d1 : up_fault;
    reg [$bits(land_cnt)-1:0] land_cnt_d1; always @(posedge clk) land_cnt_d1 <= land_cnt;
    wire [$bits(land_cnt)-1:0] land_cnt_u0 = ((U1_AUD & 16) != 0) ? land_cnt_d1 : land_cnt;
    reg [$bits(x_rdy)-1:0] x_rdy_d1; always @(posedge clk) x_rdy_d1 <= x_rdy;
    wire [$bits(x_rdy)-1:0] x_rdy_u0 = ((U1_AUD & 16) != 0) ? x_rdy_d1 : x_rdy;
    reg [$bits(tr_fault)-1:0] tr_fault_d1; always @(posedge clk) tr_fault_d1 <= tr_fault;
    wire [$bits(tr_fault)-1:0] tr_fault_u0 = ((U1_AUD & 16) != 0) ? tr_fault_d1 : tr_fault;
    reg [$bits(p_fault)-1:0] p_fault_d1; always @(posedge clk) p_fault_d1 <= p_fault;
    wire [$bits(p_fault)-1:0] p_fault_u0 = ((U1_AUD & 16) != 0) ? p_fault_d1 : p_fault;
    reg [$bits(fab_fault)-1:0] fab_fault_d1; always @(posedge clk) fab_fault_d1 <= fab_fault;
    wire [$bits(fab_fault)-1:0] fab_fault_u0 = ((U1_AUD & 16) != 0) ? fab_fault_d1 : fab_fault;
    // el1011-q-seq TXN: closed-loop landings -- each DUT's land_cnt counts ITS OWN result bursts (ov on its own clocked
    // edges), landed 4 edges later (the vector memory), cleared in reset; u0 one edge later than u1 (u1 pin-flops it)
    reg [15:0] lb0 = 0, lb1 = 0; reg [15:0] lp0 [0:4]; reg [15:0] lp1 [0:4]; reg ck0_q = 0, ck1_q = 0; integer lpk;
    always @(posedge clk) begin
        if (!rst_n) begin lb0 <= 0; lb1 <= 0; for (lpk = 0; lpk < 5; lpk = lpk + 1) begin lp0[lpk] <= 0; lp1[lpk] <= 0; end end
        else begin
            if (ck0_q && ov_0) lb0 <= lb0 + 1'b1;
            if (ck1_q && ov_1) lb1 <= lb1 + 1'b1;
            lp0[0] <= lb0; lp1[0] <= lb1; for (lpk = 1; lpk < 5; lpk = lpk + 1) begin lp0[lpk] <= lp0[lpk-1]; lp1[lpk] <= lp1[lpk-1]; end
        end
        ck0_q <= me_clk_en_0; ck1_q <= me_clk_en_1;
    end
    wire [15:0] land_tx0 = lp0[4], land_tx1 = lp1[3];
    // el1011-q-seq TXN: closed-loop port elements -- per DUT, on ITS OWN engine edges (the ports run on the exported gated
    // clock), the tag {p_v_e2, p_f_e2} returns as p_am 6 engine edges later, a fixed function of the tag (12 port words:
    // valid, key = hash of the tag, row = tag bits); ME-domain fault / ready inputs held benign in TXN mode
    localparam integer PL = 6;
    reg [113:0] pt0 [0:PL-1]; reg [113:0] pt1 [0:PL-1]; integer ptk;
    // the port elements' reply valid line is reset (ot_qwen_me_spport_w12: e_v / raw_v / u_rv vline are async-reset), so
    // the model clears its pipeline in reset (TXRST 1); TXRST 0 = the earlier unreset model (stale tags replayed after reset)
    always @(posedge clk) begin
        if (TXRST != 0 && !rst_n) begin for (ptk = 0; ptk < PL; ptk = ptk + 1) begin pt0[ptk] <= '0; pt1[ptk] <= '0; end end
        else begin
        if ((TXPC != 0) ? me_clk_en_0 : ck0_q) begin pt0[0] <= {p_v_e2_0, p_f_e2_0}; for (ptk = 1; ptk < PL; ptk = ptk + 1) pt0[ptk] <= pt0[ptk-1]; end
        if ((TXPC != 0) ? me_clk_en_1 : ck1_q) begin pt1[0] <= {p_v_e2_1, p_f_e2_1}; for (ptk = 1; ptk < PL; ptk = ptk + 1) pt1[ptk] <= pt1[ptk-1]; end
        end
    end
    function automatic [NPE*51-1:0] pam(input [113:0] tg);
        integer q; reg [31:0] h;
        begin
            for (q = 0; q < NPE; q = q + 1) begin
                h = tg[31:0] ^ tg[63:32] ^ tg[95:64] ^ {14'd0, tg[113:96]} ^ (32'h9e3779b9 * (q + 1));
                pam[q*51 +: 51] = {tg[113] && h[0], h, tg[17:0] ^ 18'(q)};
            end
        end
    endfunction
    wire [NPE*51-1:0] pam_tx0 = pam(pt0[PL-1]), pam_tx1 = pam(pt1[PL-1]);
    // el1011-q-seq AUD 32768 (coordinator 10-11: p_am pin register, argmax loop +1 cycle): the cycle-level golden u0 counts
    // the same +1 (u0 = the base with only the AMI bit); TXN keeps u0 the plain base (transaction-level, timing-free compare)
    localparam integer U0_AUD = ((U1_AUD & 32768) != 0 && TXN == 0) ? 32768 : 0;
    ot_qfd_tt_ctlm_i #(.PSRAM(U1_PSRAM), .PMUT(PMUT), .HQ2(U1_HQ2), .MEREG(U1_MEREG), .RRG(U1_RRG), .PCUT(U1_PCUT), .AUD(U1_AUD), .G(TBG), .TPMUT(U1_TPMUT)) u0 (
        .clk(clk), .rst_n(rst_n),
        .h_start(h_start),
        .token(token),
        .pos(pos),
        .prog_base(prog_base),
        .pw_v(pw_v),
        .pw_addr(pw_addr),
        .pw_data(pw_data),
        .x_oacc(x_oacc),
        .x_oidle(x_oidle),
        .x_oprog(x_oprog),
        .x_orows(x_orows),
        .kv_ok(kv_ok),
        .kv_write_drained(kv_write_drained),
        .me_mem_ok((U1_MEREG != 0) ? me_mem_ok : mo_u0),
        .up_fault(up_fault),
        .land_cnt((TXN != 0) ? land_tx1 : land_cnt),
        .x_rdy((TXN != 0) ? 1'b1 : x_rdy),
        .tr_fault((TXN != 0) ? '0 : tr_fault),
        .p_am((TXN != 0) ? pam_tx1 : p_am),
        .p_fault((TXN != 0) ? '0 : p_fault),
        .fab_fault((TXN != 0) ? 1'b0 : fab_fault),
        .me_acc_o(me_acc_o_0),
        .me_idle_o(me_idle_o_0),
        .me_prog_o(me_prog_o_0),
        .m_fin_o(m_fin_o_0),
        .m_fidx_o(m_fidx_o_0),
        .m_fval_o(m_fval_o_0),
        .kvd_v(kvd_v_0),
        .kvd_wbase(kvd_wbase_0),
        .kvd_ts(kvd_ts_0),
        .kvd_ks(kvd_ks_0),
        .kvd_js(kvd_js_0),
        .kvd_wcs(kvd_wcs_0),
        .kvd_split(kvd_split_0),
        .kvd_jsh(kvd_jsh_0),
        .kvd_tiles(kvd_tiles_0),
        .kvd_k(kvd_k_0),
        .kvd_nout(kvd_nout_0),
        .kvd_kindk(kvd_kindk_0),
        .kvd_pos(kvd_pos_0),
        .me_clk_en(me_clk_en_0),
        .c_fault(c_fault_0),
        .scale_re(scale_re_0),
        .scale_gre(scale_gre_0),
        .scale_addr(scale_addr_0),
        .x_dv(x_dv_0),
        .x_dc(x_dc_0),
        .x_dcs(x_dcs_0),
        .x_dsp(x_dsp_0),
        .t_sel_e(t_sel_e_0),
        .t_tv_e(t_tv_e_0),
        .p_v_e2(p_v_e2_0),
        .p_f_e2(p_f_e2_0),
        .ov(ov_0),
        .mx_we(mx_we_0),
        .mx_addr(mx_addr_0),
        .mx_mask(mx_mask_0),
        .mx_data(mx_data_0));
    ot_qfd_tt_ctlm_split #(.PSRAM(U1_PSRAM), .PMUT(PMUT), .HQ2(U1_HQ2), .MEREG(U1_MEREG), .RRG(U1_RRG), .PCUT(U1_PCUT), .AUD(U1_AUD), .G(TBG), .TPMUT(U1_TPMUT)) u1 (
        .ck_head(clk), .ck_tree(clk), .rst_n(rst_n),
        .h_start(h_start),
        .token(token),
        .pos(pos),
        .prog_base(prog_base),
        .pw_v(pw_v),
        .pw_addr(pw_addr),
        .pw_data(pw_data),
        .x_oacc(x_oacc),
        .x_oidle(x_oidle),
        .x_oprog(x_oprog),
        .x_orows(x_orows),
        .kv_ok(kv_ok),
        .kv_write_drained(kv_write_drained),
        .me_mem_ok((U1_MEREG != 0) ? me_mem_ok : mo_u0),
        .up_fault(up_fault),
        .land_cnt((TXN != 0) ? land_tx1 : land_cnt),
        .x_rdy((TXN != 0) ? 1'b1 : x_rdy),
        .tr_fault((TXN != 0) ? '0 : tr_fault),
        .p_am((TXN != 0) ? pam_tx1 : p_am),
        .p_fault((TXN != 0) ? '0 : p_fault),
        .fab_fault((TXN != 0) ? 1'b0 : fab_fault),
        .me_acc_o(me_acc_o_1),
        .me_idle_o(me_idle_o_1),
        .me_prog_o(me_prog_o_1),
        .m_fin_o(m_fin_o_1),
        .m_fidx_o(m_fidx_o_1),
        .m_fval_o(m_fval_o_1),
        .kvd_v(kvd_v_1),
        .kvd_wbase(kvd_wbase_1),
        .kvd_ts(kvd_ts_1),
        .kvd_ks(kvd_ks_1),
        .kvd_js(kvd_js_1),
        .kvd_wcs(kvd_wcs_1),
        .kvd_split(kvd_split_1),
        .kvd_jsh(kvd_jsh_1),
        .kvd_tiles(kvd_tiles_1),
        .kvd_k(kvd_k_1),
        .kvd_nout(kvd_nout_1),
        .kvd_kindk(kvd_kindk_1),
        .kvd_pos(kvd_pos_1),
        .me_clk_en(me_clk_en_1),
        .c_fault(c_fault_1),
        .scale_re(scale_re_1),
        .scale_gre(scale_gre_1),
        .scale_addr(scale_addr_1),
        .x_dv(x_dv_1),
        .x_dc(x_dc_1),
        .x_dcs(x_dcs_1),
        .x_dsp(x_dsp_1),
        .t_sel_e(t_sel_e_1),
        .t_tv_e(t_tv_e_1),
        .p_v_e2(p_v_e2_1),
        .p_f_e2(p_f_e2_1),
        .ov(ov_1),
        .mx_we(mx_we_1),
        .mx_addr(mx_addr_1),
        .mx_mask(mx_mask_1),
        .mx_data(mx_data_1));
    task automatic rand_inputs;
        begin
            token = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
            pos = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
            prog_base = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
            x_oacc = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
            x_oidle = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
            x_oprog = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
            x_orows = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
            kv_ok = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
            kv_write_drained = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
            me_mem_ok = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
            up_fault = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
            land_cnt = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
            x_rdy = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
            tr_fault = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
            p_am = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
            p_fault = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
            fab_fault = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
        end
    endtask
    wire out_mismatch = (me_acc_o_0 !== me_acc_o_1) || (me_idle_o_0 !== me_idle_o_1) || (me_prog_o_0 !== me_prog_o_1) || (m_fin_o_0 !== m_fin_o_1) || (m_fidx_o_0 !== m_fidx_o_1) || (m_fval_o_0 !== m_fval_o_1) || (kvd_v_0 !== kvd_v_1) || (kvd_wbase_0 !== kvd_wbase_1) || (kvd_ts_0 !== kvd_ts_1) || (kvd_ks_0 !== kvd_ks_1) || (kvd_js_0 !== kvd_js_1) || (kvd_wcs_0 !== kvd_wcs_1) || (kvd_split_0 !== kvd_split_1) || (kvd_jsh_0 !== kvd_jsh_1) || (kvd_tiles_0 !== kvd_tiles_1) || (kvd_k_0 !== kvd_k_1) || (kvd_nout_0 !== kvd_nout_1) || (kvd_kindk_0 !== kvd_kindk_1) || (kvd_pos_0 !== kvd_pos_1) || (me_clk_en_0 !== me_clk_en_1) || (c_fault_0 !== c_fault_1) || (scale_re_0 !== scale_re_1) || (scale_gre_0 !== scale_gre_1) || ((PFMASK == 0 || scale_re_0 || scale_gre_0) && (scale_addr_0 !== scale_addr_1)) || (x_dv_0 !== x_dv_1) || (x_dc_0 !== x_dc_1) || (x_dcs_0 !== x_dcs_1) || (x_dsp_0 !== x_dsp_1) || (t_sel_e_0 !== t_sel_e_1) || (t_tv_e_0 !== t_tv_e_1) || (p_v_e2_0 !== p_v_e2_1) || ((PFMASK == 0 || p_v_e2_0) && (p_f_e2_0 !== p_f_e2_1)) || (ov_0 !== ov_1) || (mx_we_0 !== mx_we_1) || (mx_addr_0 !== mx_addr_1) || (mx_mask_0 !== mx_mask_1) || (mx_data_0 !== mx_data_1);
    wire pq_mismatch = (u0.prog_q !== u1.u_head.prog_q);
    generate if (DBGT != 0) begin : g_dbg
        always @(posedge clk) if (rst_n && cyc < DBGT) $display("DBG c=%0d mo_m=%b en_d=%b en_c=%b ck0=%b ck1=%b idle=%b wake=%b go=%b gfl=%0d st=%0d nxv=%b du=%0d iss0=%b iss1=%b",
            cyc, u1.u_head.u_ctrl_me.g_merr.mo_m, u1.u_head.u_ctrl_me.g_merr.en_d, u1.u_head.u_ctrl_me.g_merr.en_c, me_clk_en_0, me_clk_en_1,
            u1.u_head.u_ctrl_me.me_idle, u1.u_head.u_ctrl_me.me_wake, u1.u_head.u_ctrl_me.me_go, u1.u_head.u_ctrl_me.g_merr.gfl, u1.u_head.u_ctrl_me.st, u1.u_head.u_ctrl_me.nx_v,
            u1.u_head.u_ctrl_me.d_unit, u0.u_ctrl_me.issue, u1.u_head.u_ctrl_me.issue);
    end endgenerate

    // ---- el1011-q-seq TXN: transaction-level comparison (coordinator 10-11: MEREG 3 registers the engine clock enable, the
    // engine wakes one edge later; results, order and faults must stay exact, latency may grow).  Per interface an event
    // stream is hashed per DUT (me_prog_o: monotone-status check only): engine-domain strobes only on edges the DUT's own engine was clocked (its me_clk_en of
    // the previous edge), controller outputs on their rising strobe / value change.  me_clk_en (the changed interface)
    // and me_idle_o (pure timing) are not compared.  Per reset window u1's stream must equal u0's up to the shorter one;
    // at the end u1 must have produced >= 80 % of u0's events.
    localparam integer NS = 25, ME = 8192;   // streams 11 + lv: the split-tree level lv's select, one event per wave (t_tv_e[lv])
    function automatic [16*32-1:0] mxm(input [15:0] m);   // lane mask -> data-bit mask (16 lanes x 32 b)
        integer k; begin for (k = 0; k < 16; k = k + 1) mxm[k*32 +: 32] = {32{m[k]}}; end
    endfunction
    function automatic [63:0] hv(input [2047:0] v);
        reg [63:0] h; integer k;
        begin h = 64'hcbf29ce484222325; for (k = 0; k < 32; k = k + 1) h = (h ^ v[k*64 +: 64]) * 64'h100000001b3; hv = h; end
    endfunction
    reg [63:0] tq0 [0:NS-1][0:ME-1]; reg [63:0] tq1 [0:NS-1][0:ME-1];
    integer tlv, ttw = 0; integer tc0 [0:NS-1]; integer tc1 [0:NS-1]; integer tt0 = 0, tt1 = 0, tbad = 0, tw = 0, ts, tk;
    reg en0_q = 0, en1_q = 0, kv0_q = 0, kv1_q = 0, fin0_q = 0, fin1_q = 0;
    reg [23:0] acc0_q = 0, acc1_q = 0; reg [15:0] prg0_q = 0, prg1_q = 0; reg cf0_q = 0, cf1_q = 0;
    integer tcs0 [0:NS-1]; integer tcs1 [0:NS-1]; integer ncov = 0;
    initial for (ts = 0; ts < NS; ts = ts + 1) begin tc0[ts] = 0; tc1[ts] = 0; tcs0[ts] = 0; tcs1[ts] = 0; end
    integer tcy0 [0:NS-1][0:ME-1]; integer tcy1 [0:NS-1][0:ME-1];
    task automatic tpush0(input integer s, input [2047:0] v); begin if (DBGTX == 2 && s == DBGS && tw == DBGW) $display("EV0 k=%0d c=%0d v=%h", tc0[s], cyc, v[63:0]); if (tc0[s] < ME) begin tq0[s][tc0[s]] = hv(v); tcy0[s][tc0[s]] = cyc; end tc0[s] = tc0[s] + 1; tt0 = tt0 + 1; end endtask
    task automatic tpush1(input integer s, input [2047:0] v); begin if (DBGTX == 2 && s == DBGS && tw == DBGW) $display("EV1 k=%0d c=%0d v=%h", tc1[s], cyc, v[63:0]); if (tc1[s] < ME) begin tq1[s][tc1[s]] = hv(v); tcy1[s][tc1[s]] = cyc; end tc1[s] = tc1[s] + 1; tt1 = tt1 + 1; end endtask
    task automatic twin;   // close a window: prefix-compare and clear
        integer s2, k2, m2;
        begin
            for (s2 = 0; s2 < NS; s2 = s2 + 1) begin
                m2 = (tc0[s2] < tc1[s2]) ? tc0[s2] : tc1[s2]; if (m2 > ME) m2 = ME;
                for (k2 = 0; k2 < m2; k2 = k2 + 1) if (tq0[s2][k2] !== tq1[s2][k2]) begin
                    tbad = tbad + 1; if (tbad <= 5) $display("TXN MISMATCH window=%0d stream=%0d event=%0d", tw, s2, k2);
                    if (DBGTX != 0 && tbad <= 40) $display("TXN DBG w=%0d s=%0d k=%0d cyc0=%0d cyc1=%0d n0=%0d n1=%0d", tw, s2, k2, tcy0[s2][k2], tcy1[s2][k2], tc0[s2], tc1[s2]); end
                if (DBGTX != 0) $display("TXN CNT w=%0d s=%0d n0=%0d n1=%0d", tw, s2, tc0[s2], tc1[s2]);
                tcs0[s2] = tcs0[s2] + tc0[s2]; tcs1[s2] = tcs1[s2] + tc1[s2];
                tc0[s2] = 0; tc1[s2] = 0;
            end
            tw = tw + 1;
        end
    endtask
    always @(posedge clk) if (TXN != 0) begin
        if (!rst_n) begin
            if (DBGTX == 2 && tw == DBGW) $display("RST c=%0d", cyc);
            if (tt0 + tt1 > ttw) begin twin; ttw = tt0 + tt1; end
        end else begin
            if (kvd_v_0 && !kv0_q) tpush0(0, {kvd_wbase_0, kvd_ts_0, kvd_ks_0, kvd_js_0, kvd_wcs_0, kvd_split_0, kvd_jsh_0, kvd_tiles_0, kvd_k_0, kvd_nout_0, kvd_kindk_0, kvd_pos_0});
            if (kvd_v_1 && !kv1_q) tpush1(0, {kvd_wbase_1, kvd_ts_1, kvd_ks_1, kvd_js_1, kvd_wcs_1, kvd_split_1, kvd_jsh_1, kvd_tiles_1, kvd_k_1, kvd_nout_1, kvd_kindk_1, kvd_pos_1});
            if (m_fin_o_0 && !fin0_q) tpush0(1, {m_fidx_o_0, m_fval_o_0});
            if (m_fin_o_1 && !fin1_q) tpush1(1, {m_fidx_o_1, m_fval_o_1});
            if (me_acc_o_0 !== acc0_q) tpush0(2, me_acc_o_0);   if (me_acc_o_1 !== acc1_q) tpush1(2, me_acc_o_1);
            // me_prog_o is a monotone STATUS (landed bursts; the other unit only chases it): MEREG 3 samples it on one more
            // edge at each idle entry, so it is checked for monotonicity within a window, not as an exact sequence
            if (me_prog_o_1 < prg1_q && prg1_q != 0 && me_prog_o_1 != 0) begin tbad = tbad + 1; if (tbad <= 5) $display("TXN PROGRESS DECREASE %0d -> %0d", prg1_q, me_prog_o_1); end
            if (c_fault_0 !== cf0_q) tpush0(4, c_fault_0);      if (c_fault_1 !== cf1_q) tpush1(4, c_fault_1);
            if (en0_q) begin
                if (scale_re_0 || |scale_gre_0) tpush0(5, {scale_re_0, scale_gre_0, scale_addr_0});
                if (x_dv_0) tpush0(6, {x_dc_0, x_dcs_0, x_dsp_0});
                // t_tv_e / t_sel_e are per-edge wave valids / selects of the split tree: the edge PATTERN depends on the gaps
                // between waves (timing), so TXN compares, per level, the select carried by each wave (stream 11 + lv)
                if (TXT == 0 && |t_tv_e_0) tpush0(7, {t_sel_e_0, t_tv_e_0});
                if (TXT != 0) for (tlv = 0; tlv <= LGT; tlv = tlv + 1) if (t_tv_e_0[tlv]) tpush0(11 + tlv, t_sel_e_0[tlv]);
                if (p_v_e2_0) tpush0(8, p_f_e2_0);
                if (ov_0) tpush0(9, 1'b1);
                if (DBGMX != 0 && mx_we_0 && tc0[10] == 0) $display("MX0 c=%0d w=%0d a=%h m=%h d=%h", cyc, tw, mx_addr_0, mx_mask_0, mx_data_0 & mxm(mx_mask_0));
                if (mx_we_0) tpush0(10, {mx_addr_0, mx_mask_0, mx_data_0 & mxm(mx_mask_0)});   // data under its lane mask
            end
            if (en1_q) begin
                if (scale_re_1 || |scale_gre_1) tpush1(5, {scale_re_1, scale_gre_1, scale_addr_1});
                if (x_dv_1) tpush1(6, {x_dc_1, x_dcs_1, x_dsp_1});
                if (TXT == 0 && |t_tv_e_1) tpush1(7, {t_sel_e_1, t_tv_e_1});
                if (TXT != 0) for (tlv = 0; tlv <= LGT; tlv = tlv + 1) if (t_tv_e_1[tlv]) tpush1(11 + tlv, t_sel_e_1[tlv]);
                if (p_v_e2_1) tpush1(8, p_f_e2_1);
                if (ov_1) tpush1(9, 1'b1);
                if (DBGMX != 0 && mx_we_1 && tc1[10] == 0) $display("MX1 c=%0d w=%0d a=%h m=%h d=%h", cyc, tw, mx_addr_1, mx_mask_1, mx_data_1 & mxm(mx_mask_1));
                if (mx_we_1) tpush1(10, {mx_addr_1, mx_mask_1, mx_data_1 & mxm(mx_mask_1)});
            end
        end
        en0_q <= me_clk_en_0; en1_q <= me_clk_en_1; kv0_q <= kvd_v_0; kv1_q <= kvd_v_1; fin0_q <= m_fin_o_0; fin1_q <= m_fin_o_1;
        acc0_q <= me_acc_o_0; acc1_q <= me_acc_o_1; prg0_q <= me_prog_o_0; prg1_q <= me_prog_o_1; cf0_q <= c_fault_0; cf1_q <= c_fault_1;
    end
    always @(posedge clk) if (rst_n && ((!p_v_e2_0 && (p_f_e2_0 !== p_f_e2_1)) || (!scale_re_0 && !scale_gre_0 && (scale_addr_0 !== scale_addr_1)))) npfm = npfm + 1;   // masked (invalid-word) differences
    // el1011-q-seq debug: name the mismatching outputs (first 5 mismatch cycles)
    always @(posedge clk) if (rst_n && out_mismatch && bad < 5) begin
        if (me_acc_o_0 !== me_acc_o_1) $display("  DIFF me_acc_o u0=%h u1=%h v=%b", me_acc_o_0, me_acc_o_1, p_v_e2_0);
        if (me_idle_o_0 !== me_idle_o_1) $display("  DIFF me_idle_o u0=%h u1=%h v=%b", me_idle_o_0, me_idle_o_1, p_v_e2_0);
        if (me_prog_o_0 !== me_prog_o_1) $display("  DIFF me_prog_o u0=%h u1=%h v=%b", me_prog_o_0, me_prog_o_1, p_v_e2_0);
        if (m_fin_o_0 !== m_fin_o_1) $display("  DIFF m_fin_o u0=%h u1=%h v=%b", m_fin_o_0, m_fin_o_1, p_v_e2_0);
        if (m_fidx_o_0 !== m_fidx_o_1) $display("  DIFF m_fidx_o u0=%h u1=%h v=%b", m_fidx_o_0, m_fidx_o_1, p_v_e2_0);
        if (m_fval_o_0 !== m_fval_o_1) $display("  DIFF m_fval_o u0=%h u1=%h v=%b", m_fval_o_0, m_fval_o_1, p_v_e2_0);
        if (kvd_v_0 !== kvd_v_1) $display("  DIFF kvd_v u0=%h u1=%h v=%b", kvd_v_0, kvd_v_1, p_v_e2_0);
        if (kvd_wbase_0 !== kvd_wbase_1) $display("  DIFF kvd_wbase u0=%h u1=%h v=%b", kvd_wbase_0, kvd_wbase_1, p_v_e2_0);
        if (kvd_ts_0 !== kvd_ts_1) $display("  DIFF kvd_ts u0=%h u1=%h v=%b", kvd_ts_0, kvd_ts_1, p_v_e2_0);
        if (kvd_ks_0 !== kvd_ks_1) $display("  DIFF kvd_ks u0=%h u1=%h v=%b", kvd_ks_0, kvd_ks_1, p_v_e2_0);
        if (kvd_js_0 !== kvd_js_1) $display("  DIFF kvd_js u0=%h u1=%h v=%b", kvd_js_0, kvd_js_1, p_v_e2_0);
        if (kvd_wcs_0 !== kvd_wcs_1) $display("  DIFF kvd_wcs u0=%h u1=%h v=%b", kvd_wcs_0, kvd_wcs_1, p_v_e2_0);
        if (kvd_split_0 !== kvd_split_1) $display("  DIFF kvd_split u0=%h u1=%h v=%b", kvd_split_0, kvd_split_1, p_v_e2_0);
        if (kvd_jsh_0 !== kvd_jsh_1) $display("  DIFF kvd_jsh u0=%h u1=%h v=%b", kvd_jsh_0, kvd_jsh_1, p_v_e2_0);
        if (kvd_tiles_0 !== kvd_tiles_1) $display("  DIFF kvd_tiles u0=%h u1=%h v=%b", kvd_tiles_0, kvd_tiles_1, p_v_e2_0);
        if (kvd_k_0 !== kvd_k_1) $display("  DIFF kvd_k u0=%h u1=%h v=%b", kvd_k_0, kvd_k_1, p_v_e2_0);
        if (kvd_nout_0 !== kvd_nout_1) $display("  DIFF kvd_nout u0=%h u1=%h v=%b", kvd_nout_0, kvd_nout_1, p_v_e2_0);
        if (kvd_kindk_0 !== kvd_kindk_1) $display("  DIFF kvd_kindk u0=%h u1=%h v=%b", kvd_kindk_0, kvd_kindk_1, p_v_e2_0);
        if (kvd_pos_0 !== kvd_pos_1) $display("  DIFF kvd_pos u0=%h u1=%h v=%b", kvd_pos_0, kvd_pos_1, p_v_e2_0);
        if (me_clk_en_0 !== me_clk_en_1) $display("  DIFF me_clk_en u0=%h u1=%h v=%b", me_clk_en_0, me_clk_en_1, p_v_e2_0);
        if (c_fault_0 !== c_fault_1) $display("  DIFF c_fault u0=%h u1=%h v=%b", c_fault_0, c_fault_1, p_v_e2_0);
        if (scale_re_0 !== scale_re_1) $display("  DIFF scale_re u0=%h u1=%h v=%b", scale_re_0, scale_re_1, p_v_e2_0);
        if (scale_gre_0 !== scale_gre_1) $display("  DIFF scale_gre u0=%h u1=%h v=%b", scale_gre_0, scale_gre_1, p_v_e2_0);
        if (scale_addr_0 !== scale_addr_1) $display("  DIFF scale_addr re=%b gre=%b", scale_re_0, scale_gre_0);
        if (x_dv_0 !== x_dv_1) $display("  DIFF x_dv u0=%h u1=%h v=%b", x_dv_0, x_dv_1, p_v_e2_0);
        if (x_dc_0 !== x_dc_1) $display("  DIFF x_dc u0=%h u1=%h v=%b", x_dc_0, x_dc_1, p_v_e2_0);
        if (x_dcs_0 !== x_dcs_1) $display("  DIFF x_dcs u0=%h u1=%h v=%b", x_dcs_0, x_dcs_1, p_v_e2_0);
        if (x_dsp_0 !== x_dsp_1) $display("  DIFF x_dsp u0=%h u1=%h v=%b", x_dsp_0, x_dsp_1, p_v_e2_0);
        if (t_sel_e_0 !== t_sel_e_1) $display("  DIFF t_sel_e u0=%h u1=%h v=%b", t_sel_e_0, t_sel_e_1, p_v_e2_0);
        if (t_tv_e_0 !== t_tv_e_1) $display("  DIFF t_tv_e u0=%h u1=%h v=%b", t_tv_e_0, t_tv_e_1, p_v_e2_0);
        if (p_v_e2_0 !== p_v_e2_1) $display("  DIFF p_v_e2 u0=%h u1=%h v=%b", p_v_e2_0, p_v_e2_1, p_v_e2_0);
        if (p_f_e2_0 !== p_f_e2_1) $display("  DIFF p_f_e2 u0=%h u1=%h v=%b", p_f_e2_0, p_f_e2_1, p_v_e2_0);
        if (ov_0 !== ov_1) $display("  DIFF ov u0=%h u1=%h v=%b", ov_0, ov_1, p_v_e2_0);
        if (mx_we_0 !== mx_we_1) $display("  DIFF mx_we u0=%h u1=%h v=%b", mx_we_0, mx_we_1, p_v_e2_0);
        if (mx_addr_0 !== mx_addr_1) $display("  DIFF mx_addr u0=%h u1=%h v=%b", mx_addr_0, mx_addr_1, p_v_e2_0);
        if (mx_mask_0 !== mx_mask_1) $display("  DIFF mx_mask u0=%h u1=%h v=%b", mx_mask_0, mx_mask_1, p_v_e2_0);
        if (mx_data_0 !== mx_data_1) $display("  DIFF mx_data u0=%h u1=%h v=%b", mx_data_0, mx_data_1, p_v_e2_0);
    end
    initial begin
        seed = SEED;   // the 5.050 simulator ignores the declaration initialiser for $random's seed: every SEED ran one stream
        repeat (6) @(posedge clk);
        rst_n = 1;
        repeat (6) @(posedge clk);
        // boot load: the program store (64 words x 16 slices) while the controller is idle
        for (k = 0; k < 1024; k = k + 1) begin
            @(negedge clk); pw_v = 1; pw_addr = k; pw_data = {$random(seed), $random(seed)};
            if (k % 16 == 0) begin         // slice 0: unit / barrier / chase / waits biased toward progress (barrier / chase / waits rare)
                // mostly SU ops (the other unit: they skip, so the fetch FIFO / head / store reads run at full rate), some ME
                // ops (this unit: issue; an ME op of the real ot_qfd_tt_ctl can hold the unit busy for the rest of the token),
                // rare END
                pw_data[1:0] = (($random(seed) & 31) == 0) ? 2'd0 : (($random(seed) & 15) == 0) ? 2'd1 : 2'd2;
                pw_data[3:2] = (($random(seed) & 7) == 0) ? 2'($random(seed)) : 2'd0;
                pw_data[21:20] = (($random(seed) & 7) == 0) ? 2'($random(seed)) : 2'd0;
                // ME op sizes small (NOUT [38:23], TILES [54:39], K [70:55]) so an ME op finishes within a token
                pw_data[38:23] = 16'(1 + ($random(seed) & 3)); pw_data[54:39] = 16'(1 + ($random(seed) & 3));
                pw_data[63:55] = 9'(1 + ($random(seed) & 3));
                if (PCOV != 0) begin
                    if ($random(seed) & 1) pw_data[1:0] = 2'd1;             // more ME ops (this unit)
                    pw_data[3] = $random(seed) & 1;                          // CHASE
                    pw_data[19:4] = 16'(1 + ($random(seed) & 3));            // CHASE_N small: meets the climbing x_oprog
                end
            end
            if (k % 16 == 1) pw_data[6:0] = 7'd0;            // K [70:64]
            if (k % 16 == 3) pw_data[44:27] = 18'd0;         // the ME DYN selectors D_* [236:219]: static sizes / bases
            if (k % 16 == 3 && PCOV != 0 && ($random(seed) & 1)) pw_data[41:39] = 3'd6;   // D_TILES [233:231] = DYN_TTILES
            if (k % 16 == 5 && PCOV != 0) pw_data[20:17] = 4'($random(seed) % 12);        // ME_SPLIT [340:337]: valid splits
        end
        @(negedge clk); pw_v = 0;
        repeat (8) @(posedge clk);
        for (i = 0; i < NCYC; i = i + 1) begin
            @(negedge clk);
            rand_inputs;
            // status inputs follow the ICUT contract (readiness never falls without the unit's own go; the other
            // unit's accepted-op count, progress and landings only climb)
            kv_ok = 1; kv_write_drained = 1; x_oidle = 1; x_rdy = 1;
            // MOK: the supply stalls the engine on random edges (~1 in 4), never within the reset window (+-2 edges)
            me_mem_ok = (MOK == 0) || (((i % TW) >= TW - 14) || ((i % TW) < 5)) || (($random(seed) & 3) != 0);
            // the other unit's progress counters only climb within a token (chase compares never fall)
            if ((i % TW) == 0) begin xprog = 0; xrows = 0; xacc = 0; end
            else begin
                xprog = xprog + 16'(($random(seed) & 7) == 0); xrows = xrows + 16'(($random(seed) & 7) == 0);
                xacc = xacc + 24'(($random(seed) & 3) == 0);   // the other unit accepts its ops (count only climbs)
            end
            x_oacc = xacc;
            x_oprog = xprog; x_orows = xrows;
            land_cnt = lcnt; lcnt = ((i % TW) == 0) ? 16'd0 : lcnt + 16'd1;   // landings only climb (one a cycle: the memory keeps up)
            up_fault = 0; tr_fault = 0; p_fault = 0; fab_fault = 0;
            if ((i % TW) == 0) pbase = 12'($random(seed)) % 48;
            prog_base = pbase;   // held for the token (the die holds it); runs past word 63 read the out-of-store zeros
            rst_n = (i % TW) < TW - 8;                 // an 8-cycle reset every 400 cycles restarts the controller (store kept)
            h_start = (i % TW) == 12;
        end
        @(negedge clk); h_start = 0;
        repeat (20) @(posedge clk);
        if (TXN != 0) twin;
        if (TXN != 0 && (tbad != 0 || tt1 * 5 < tt0 * 4)) bad = bad + 1 + tbad;
        if (TXN != 0) begin
            for (ts = 0; ts < NS; ts = ts + 1) if (COVMASK[ts]) begin
                if (tcs0[ts] < MINEV || tcs1[ts] < MINEV) begin ncov = ncov + 1; $display("TXN COVERAGE stream=%0d u0=%0d u1=%0d (min %0d)", ts, tcs0[ts], tcs1[ts], MINEV); end
            end
            if (COVMASK != 0) $display("TXN STREAMS s0 kvd=%0d/%0d s1 argmax=%0d/%0d s2 acc=%0d/%0d s5 scale=%0d/%0d s6 xdesc=%0d/%0d s8 pword=%0d/%0d s9 ov=%0d/%0d s10 mx=%0d/%0d s19..23 tree=%0d/%0d %0d/%0d %0d/%0d %0d/%0d %0d/%0d",
                tcs0[0], tcs1[0], tcs0[1], tcs1[1], tcs0[2], tcs1[2], tcs0[5], tcs1[5], tcs0[6], tcs1[6], tcs0[8], tcs1[8], tcs0[9], tcs1[9], tcs0[10], tcs1[10],
                tcs0[19], tcs1[19], tcs0[20], tcs1[20], tcs0[21], tcs1[21], tcs0[22], tcs1[22], tcs0[23], tcs1[23]);
            if (ncov != 0) begin bad = bad + ncov; $display("TXN COVERAGE REFUSED: %0d required streams below the floor", ncov); end
        end
        if (TXN != 0) $display("TXN events u0=%0d u1=%0d windows=%0d mismatches=%0d", tt0, tt1, tw, tbad);
        $display("GOLD dyn_ttiles G=%0d checks=%0d bad=%0d (min %0d)", TBG, ngc, ngbad, MINGC);
        if (ngbad != 0 || ngc < MINGC) bad = bad + 1 + ngbad;
        if (bad == 0 && nrd >= MINRD) $display("PASS tt_ctlm_i_psram cycles=%0d program_reads=%0d loads=%0d icut_stim=%0d dyn_tiles_ld=%0d chase_eq=%0d pf_invalid_diffs=%0d", cyc, nrd, nld, nicut, ndt, nceq, npfm);
        else $display("FAIL tt_ctlm_i_psram mismatches=%0d program_reads=%0d (min %0d) loads=%0d", bad, nrd, MINRD, nld);
        $finish;
    end
    // qwen-tp8/seq GOLD: DYN_TTILES rounds of TBG position tiles, from the instruction word and pos_r at u1's load edge
    // (independent arithmetic: a plain divide by 16 * TBG / 2^split), compared with u1's me_tiles one edge later.
    function automatic integer tz(input integer v); integer n; begin n = 0; while (v > 0 && (v & 1) == 0) begin v = v >> 1; n = n + 1; end tz = n; end endfunction
    localparam integer GTZ = tz(TBG);
    reg        gq_v = 0;
    reg [17:0] gq_e = 0;
    reg [3:0]  g_sp;
    always @(posedge clk) begin
        if (rst_n && gq_v) begin
            ngc = ngc + 1;
            if (18'(u1.u_head.u_ctrl_me.me_tiles) !== gq_e) begin
                ngbad = ngbad + 1;
                if (ngbad <= 5) $display("GOLDBAD cyc=%0d me_tiles=%0d exp=%0d", cyc, u1.u_head.u_ctrl_me.me_tiles, gq_e);
            end
        end
        g_sp = u1.u_head.u_ctrl_me.ir[u1.u_head.u_ctrl_me.O_ME_SPLIT +: 4];
        gq_v <= rst_n && u1.u_head.u_ctrl_me.load && u1.u_head.u_ctrl_me.ir[u1.u_head.u_ctrl_me.O_ME_D_TILES +: 3] == 3'd6 && g_sp <= GTZ;
        gq_e <= 18'(u1.u_head.u_ctrl_me.ir[u1.u_head.u_ctrl_me.O_ME_TILES +: u1.u_head.u_ctrl_me.W_ME_TILES])
              + 18'(u1.u_head.u_ctrl_me.pos_r / ((16 * TBG) >> g_sp)) + 18'd1;
    end
    // coverage note: where the controller waits when each token's window closes (cycle 390 of 400)
    always @(posedge clk) if (rst_n && ((i % TW) == TW - 10) && (i < 5 * TW))
        $display("WAITSTATE i=%0d st=%0d nx_v=%b unit=%0d ur=%b mr=%b men=%b xdep=%b bar=%b ch=%b wu=%b wo=%b oi=%b od=%b",
            i, u0.u_ctrl_me.st, u0.u_ctrl_me.nx_v, u0.u_ctrl_me.d_unit, u0.u_ctrl_me.unit_ready, u0.u_ctrl_me.me_ready,
            u0.u_ctrl_me.me_en, u0.u_ctrl_me.xdep_ok, u0.u_ctrl_me.d_barrier, u0.u_ctrl_me.d_chase, u0.u_ctrl_me.wait_u,
            u0.u_ctrl_me.wait_o, u0.u_ctrl_me.own_idle, u0.u_ctrl_me.o_drained);
    always @(posedge clk) if (rst_n) begin
        cyc = cyc + 1;
        if (u0.prog_re_r) nrd = nrd + 1;
        if ($isunknown({u0.u_ctrl_me.st, u0.u_ctrl_me.fq_n, u0.u_ctrl_me.nx_v, u0.u_ctrl_me.issue, u0.u_ctrl_me.load, u1.u_head.u_ctrl_me.issue, u1.u_head.u_ctrl_me.load})) begin
            bad = bad + 1;
            if (bad <= 5) $display("XSTATE cyc=%0d", cyc);
        end
        if (u0.u_ctrl_me.load) nld = nld + 1;
        if (u0.u_ctrl_me.load && u0.u_ctrl_me.ir[u0.u_ctrl_me.O_ME_D_TILES +: 3] == 3'd6) ndt = ndt + 1;   // el1011-q-seq coverage: DYN_TTILES loads
        if (u0.u_ctrl_me.osync && u0.u_ctrl_me.d_chase && u0.u_ctrl_me.x_och == u0.u_ctrl_me.d_chase_n) nceq = nceq + 1;   // chase at equality
        if (u0.u_ctrl_me.issue && !u0.u_ctrl_me.issue_live) nicut = nicut + 1;
        if (out_mismatch || pq_mismatch) begin
            bad = bad + 1;
            if (bad <= 5) $display("MISMATCH cyc=%0d outputs=%b prog_q=%b", cyc, out_mismatch, pq_mismatch);
        end
    end

    integer station_checks=0, enable_checks=0;
    always @(negedge clk) if(rst_n) begin
        enable_checks=enable_checks+1;
        if(u1.u_head.me_clk_en !== u1.u_tree.local_en) $fatal(1,"native pre-edge enable mismatch");
        station_checks=station_checks+1;
        if({u1.u_head.c_me_ready,u1.u_head.c_me_idle,u1.u_head.c_me_wrom_re,u1.u_head.c_me_wrom_addr,u1.u_head.c_me_am_idx,u1.u_head.c_me_am_val,u1.u_head.c_me_am_any,u1.u_head.c_me_progress,u1.u_head.c_me_fault} !==
           {u1.u_tree.u_shadow.c_me_ready,u1.u_tree.u_shadow.c_me_idle,u1.u_tree.u_shadow.c_me_wrom_re,u1.u_tree.u_shadow.c_me_wrom_addr,u1.u_tree.u_shadow.c_me_am_idx,u1.u_tree.u_shadow.c_me_am_val,u1.u_tree.u_shadow.c_me_am_any,u1.u_tree.u_shadow.c_me_progress,u1.u_tree.u_shadow.c_me_fault}) $fatal(1,"native return station epoch mismatch");
    end
    final $display("NATIVE_STATION_PROOF enable_checks=%0d station_checks=%0d",enable_checks,station_checks);
endmodule
