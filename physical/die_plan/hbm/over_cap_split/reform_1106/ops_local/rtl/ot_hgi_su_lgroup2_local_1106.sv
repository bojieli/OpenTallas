// Opt-in stage-write distribution (+1 write visibility) / macro-local read capture (+1 read response).
// DREG=RREG=0 retains the captured log-depth primitive; original masters/default recipes are untouched.
module ot_hgi_su_lgroup2_local_1106 #(
    parameter integer N = 16, M = 8, LWB = 17, AW = 24,
    parameter integer NLW = 0,             // lane write ports (GO: N)
    parameter integer MACRO = 1,
    parameter integer MUT_XBAR = 0,        // bench mutant: identity lanes take the neighbouring bank's word
    parameter integer LAT = 0,             // bench mutant: bank read latency 1 = +1 edge, 2 = -1 edge (see ot_hgi_su_lbank)
    parameter integer NS = 1,              // sector lanes: NS independent 8-word stage writes / drain reads an edge
    parameter integer BREG = 0,            // 1 = registered bank inputs (+1 edge on rd / sr_d / sr_rv)
    parameter integer DREG = 0, RREG = 0, NCOL = 4,
    parameter integer FREG = 0             // 1 = registered fault terms (per bank row check next to the bank): flt +1 edge
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [N-1:0]      rq,                    // qualified lane reads (used port, vector-memory source)
    input  wire [N-1:0]      rr,                    // raw lane read enables
    input  wire [N*AW-1:0]   ra,
    output wire [N*32-1:0]   rd,
    input  wire [NS-1:0]     sr_v,                  // per sector lane: 8 consecutive words (drain / STREAM-out)
    input  wire [NS*LWB-1:0] sr_addr,
    output wire [NS*256-1:0] sr_d,
    output wire [NS-1:0]     sr_rv,                 // sr_d valid: the sector read's response (follows the banks' latency)
    input  wire [NS-1:0]     sw_v,                  // per sector lane: up to 8 consecutive words (stage)
    input  wire [NS*LWB-1:0] sw_addr,
    input  wire [NS*8-1:0]   sw_mask,
    input  wire [NS*256-1:0] sw_d,
    input  wire [(NLW>0?NLW:1)-1:0]    lw,          // lane writes (element writes)
    input  wire [(NLW>0?NLW:1)*AW-1:0] lwa,
    input  wire [(NLW>0?NLW:1)*32-1:0] lwd,
    input  wire              s1_v,                  // one word (STREAM landing)
    input  wire [LWB-1:0]    s1_a,
    input  wire [31:0]       s1_d,
    output reg               flt
);
    // One complete stage-write cohort per physical bank column. The old
    // primitive driven by stage inputs delayed one edge is the exact reference.
    // No reset: every issued write remains in flight across reset, as in BREG.
    wire [NS-1:0] sw_v_col[0:NCOL-1];
    wire [NS*LWB-1:0] sw_addr_col[0:NCOL-1];
    wire [NS*8-1:0] sw_mask_col[0:NCOL-1];
    wire [NS*256-1:0] sw_d_col[0:NCOL-1];
    generate for (genvar dc=0; dc<NCOL; dc=dc+1) begin:g_dist
        if (DREG != 0) begin:g_reg
            localparam integer W = NS*(1+LWB+8+256), PART = W/3;
            (* keep = 1 *) reg [PART-1:0] q_a, q_b;
            (* keep = 1 *) reg [W-2*PART-1:0] q_c;
            wire [W-1:0] q = {q_c,q_b,q_a};
            always @(posedge clk) {q_c,q_b,q_a} <= {sw_v, sw_addr, sw_mask, sw_d};
            assign {sw_v_col[dc],sw_addr_col[dc],sw_mask_col[dc],sw_d_col[dc]} = q;
        end else begin:g_direct
            assign {sw_v_col[dc],sw_addr_col[dc],sw_mask_col[dc],sw_d_col[dc]} = {sw_v,sw_addr,sw_mask,sw_d};
        end
    end endgenerate
    wire [NS-1:0] sw_v_d = sw_v_col[0];
    wire [NS*LWB-1:0] sw_addr_d = sw_addr_col[0];
    wire [NS*8-1:0] sw_mask_d = sw_mask_col[0];
    wire [NS*256-1:0] sw_d_d = sw_d_col[0];
    initial if (DREG != 0 && (N != 16 || NCOL != 4 || NLW != 0))
        $error("DREG requires the measured16-bank/4-column stage-only store");

    localparam integer LN = $clog2(N), RB = LWB - LN, NROT = N / M, NHALF = (2 * N) / M, HM = (M / 2 > 0) ? M / 2 : 1;
    localparam integer NCAND = 2 * NROT + NHALF;
    localparam integer NL = (NLW > 0) ? NLW : 1;
    // candidate bank c of lane l (k < NCAND)
    function automatic [LN-1:0] cbank(input integer l, input integer k);
        integer j;
        if (k < NROT) cbank = (l + k * M) % N;
        else if (k < 2 * NROT) begin j = k - NROT; cbank = ((l ^ 1) + j * M) % N; end
        else begin j = k - 2 * NROT; cbank = ((l >> 1) + j * HM) % N; end
    endfunction
    // ---- read side: per bank, the row of the first requesting candidate lane mapped to it
    reg  [N-1:0]  b_re; reg [RB-1:0] b_ra [0:N-1];
    wire [31:0]   b_rd [0:N-1];
    reg  [N-1:0]  lok;                               // the lane's bank is one of its candidates
    integer b, l, k;
    reg src;                                         // sector-lane read conflict (this edge)
    // HBM-REFORM-B9 log form (same function as ot_hgi_su_lgroup2): the lane read select and the stage write select are
    // per-bank one-hot priority selects (log depth) instead of the N-deep / NS*8-deep sequential "last assignment wins" chains.
    always @* begin : lokc
        integer lc_, kc_; reg [LN-1:0] bl;
        bl = {LN{1'b0}};
        for (lc_ = 0; lc_ < N; lc_ = lc_ + 1) begin
            bl = ra[lc_*AW +: LN]; lok[lc_] = (lc_ == 0);
            for (kc_ = 0; kc_ < NCAND; kc_ = kc_ + 1) if (cbank(lc_, kc_) == bl) lok[lc_] = 1'b1;
        end
    end
    // lane reads: per bank, the LOWEST-index lane that hits it gives the row (the old loop ran l = N-1 .. 0)
    wire [N-1:0]  lr_re; wire [RB-1:0] lr_ra [0:N-1];
    for (genvar gbr = 0; gbr < N; gbr = gbr + 1) begin : g_lrs
        wire [N-1:0] h, oh;
        for (genvar glr = 0; glr < N; glr = glr + 1) begin : g_h
            assign h[glr] = rr[glr] && lok[glr] && ra[glr*AW +: LN] == gbr;
            if (glr == 0) begin : g_o0 assign oh[glr] = h[glr]; end
            else begin : g_on assign oh[glr] = h[glr] && !(|h[glr-1:0]); end
        end
        reg [RB-1:0] row;
        always @* begin : ao
            integer i_;
            row = {RB{1'b0}};
            for (i_ = 0; i_ < N; i_ = i_ + 1) row = row | ({RB{oh[i_]}} & ra[i_*AW + LN +: RB]);
        end
        assign lr_re[gbr] = |h; assign lr_ra[gbr] = row;
    end
    always @* begin : rsel
        integer rj_, sl_, br_; reg [LWB-1:0] sa;
        sa = {LWB{1'b0}};
        for (br_ = 0; br_ < N; br_ = br_ + 1) begin b_re[br_] = 1'b0; b_ra[br_] = {RB{1'b0}}; end
        src = 1'b0;
        if (|sr_v) begin
            // sector lanes: 8 words each; two words on one bank must be one row (else a sector-lane conflict, fail closed)
            for (sl_ = 0; sl_ < NS; sl_ = sl_ + 1) if (sr_v[sl_])
                for (rj_ = 0; rj_ < 8; rj_ = rj_ + 1) begin
                    sa = sr_addr[sl_*LWB +: LWB] + rj_;
                    if (b_re[sa[LN-1:0]] && b_ra[sa[LN-1:0]] != sa[LWB-1:LN]) src = 1'b1;
                    b_re[sa[LN-1:0]] = 1'b1; b_ra[sa[LN-1:0]] = sa[LWB-1:LN];
                end
        end else begin
            for (br_ = 0; br_ < N; br_ = br_ + 1) begin b_re[br_] = lr_re[br_]; b_ra[br_] = lr_ra[br_]; end
        end
    end
    reg [LN-1:0] lb_q [0:N-1]; reg [LN-1:0] sr_lo [0:NS-1];
    reg [LN-1:0] lb_q2 [0:N-1]; reg [LN-1:0] sr_lo2 [0:NS-1]; reg [NS-1:0] srv1, srv2;
    integer s_;
    always @(posedge clk) begin
        for (l = 0; l < N; l = l + 1) if (rr[l]) lb_q[l] <= ra[l*AW +: LN];
        for (s_ = 0; s_ < NS; s_ = s_ + 1) begin if (sr_v[s_]) sr_lo[s_] <= sr_addr[s_*LWB +: LN]; sr_lo2[s_] <= sr_lo[s_]; end
        for (l = 0; l < N; l = l + 1) lb_q2[l] <= lb_q[l];
        srv2 <= srv1;
    end
    always @(posedge clk or negedge rst_n) if (!rst_n) srv1 <= {NS{1'b0}}; else srv1 <= sr_v;
    // the response valid and the network selects follow the banks' latency (LAT mutants move the data, valid and
    // selects together, so a valid-driven reader stays exact and a fixed-latency one does not)
    localparam integer NLAT = (BREG != 0) ? 1 : LAT;   // network latency mode (BREG = a 2-edge bank)
    wire [NS-1:0] srv_base = (NLAT == 1) ? srv2 : (NLAT == 2) ? sr_v : srv1;
    reg [NS-1:0] srv3;
    always @(posedge clk or negedge rst_n) if (!rst_n) srv3 <= 0; else srv3 <= srv_base;
    assign sr_rv = (RREG != 0) ? srv3 : srv_base;
    wire [LN-1:0] lb_s [0:N-1];
    for (genvar gs_ = 0; gs_ < N; gs_ = gs_ + 1) begin : g_ls
        wire [LN-1:0] base = (NLAT == 1) ? lb_q2[gs_] : (NLAT == 2) ? ra[gs_*AW +: LN] : lb_q[gs_];
        reg [LN-1:0] delayed;
        always @(posedge clk) delayed <= base;
        assign lb_s[gs_] = (RREG != 0) ? delayed : base;
    end
    // the data network: a lane takes its bank among its candidates (lane 0: any bank)
    genvar gl, gj, gk;
    for (gl = 0; gl < N; gl = gl + 1) begin : g_rd
        if (gl == 0) begin : g_any
            wire [LN-1:0] bs = lb_s[gl] + MUT_XBAR[LN-1:0];
            assign rd[0 +: 32] = b_rd[bs];
        end else begin : g_c
            reg [31:0] dv;
            always @* begin : mx
                integer kk;
                dv = 32'd0;
                for (kk = NCAND - 1; kk >= 0; kk = kk - 1)
                    if (lb_s[gl] == cbank(gl, kk)) dv = b_rd[(cbank(gl, kk) + MUT_XBAR) % N];
            end
            assign rd[32*gl +: 32] = dv;
        end
    end
    for (gk = 0; gk < NS; gk = gk + 1) begin : g_srl
        wire [LN-1:0] sr_base = (NLAT == 1) ? sr_lo2[gk] : (NLAT == 2) ? sr_addr[gk*LWB +: LN] : sr_lo[gk];
        reg [LN-1:0] sr_delayed;
        always @(posedge clk) sr_delayed <= sr_base;
        wire [LN-1:0] sr_s = (RREG != 0) ? sr_delayed : sr_base;
        for (gj = 0; gj < 8; gj = gj + 1) begin : g_sr
            wire [LN-1:0] bj = sr_s + gj;
            assign sr_d[256*gk + 32*gj +: 32] = b_rd[bj];
        end
    end
    // ---- write side: stage (8 words) > lane writes > the single-word STREAM landing (its own group in practice)
    reg  [N-1:0] b_we; reg [RB-1:0] b_wa [0:N-1]; reg [31:0] b_wd [0:N-1];
    reg  wcoll;
    // stage writes: in one sector lane the 8 consecutive words land on 8 distinct banks (N >= 8), so a bank takes at most
    // word off = b - addr[LN-1:0] (mod N, off < 8) of each lane; the HIGHEST lane that hits wins; two hits = wcoll.
    wire [N-1:0] sw_we; wire [RB-1:0] sw_wa [0:N-1]; wire [31:0] sw_wd [0:N-1]; wire [N-1:0] sw_cb;
    for (genvar gbw = 0; gbw < N; gbw = gbw + 1) begin : g_sws
        wire [NS-1:0] h, oh; wire [RB-1:0] rw [0:NS-1]; wire [31:0] dw [0:NS-1];
        for (genvar gsw = 0; gsw < NS; gsw = gsw + 1) begin : g_h
            wire [LWB-1:0] a = sw_addr_col[gbw / (N/NCOL)][gsw*LWB +: LWB];
            wire [LN-1:0] off = LN'(gbw) - a[LN-1:0];
            wire [2:0] o3 = off[2:0];
            assign h[gsw] = sw_v_col[gbw / (N/NCOL)][gsw] && off < LN'(8) && sw_mask_col[gbw / (N/NCOL)][gsw*8 + o3];
            assign rw[gsw] = a[LWB-1:LN] + RB'(LN'(gbw) < a[LN-1:0]);
            assign dw[gsw] = sw_d_col[gbw / (N/NCOL)][gsw*256 + 32*o3 +: 32];
            if (gsw == NS - 1) begin : g_ot assign oh[gsw] = h[gsw]; end
            else begin : g_on assign oh[gsw] = h[gsw] && !(|h[NS-1:gsw+1]); end
        end
        reg [RB-1:0] row; reg [31:0] dat; reg two;
        always @* begin : ao
            integer i_;
            row = {RB{1'b0}}; dat = 32'd0; two = 1'b0;
            for (i_ = 0; i_ < NS; i_ = i_ + 1) begin
                row = row | ({RB{oh[i_]}} & rw[i_]); dat = dat | ({32{oh[i_]}} & dw[i_]);
                if (h[i_] && !oh[i_]) two = 1'b1;
            end
        end
        assign sw_we[gbw] = |h; assign sw_wa[gbw] = row; assign sw_wd[gbw] = dat; assign sw_cb[gbw] = two;
    end
    always @* begin : wsel
        integer wl_, wk_, bw_; reg [LN-1:0] wb_; reg ok_;
        wb_ = {LN{1'b0}}; ok_ = 1'b0;
        for (bw_ = 0; bw_ < N; bw_ = bw_ + 1) begin b_we[bw_] = sw_we[bw_]; b_wa[bw_] = sw_wa[bw_]; b_wd[bw_] = sw_wd[bw_]; end
        wcoll = |sw_cb;
        if (NLW > 0) begin
            if (|sw_v_d && |lw) wcoll = 1'b1;
            for (wl_ = 0; wl_ < NL; wl_ = wl_ + 1)
                if (lw[wl_]) begin
                    wb_ = lwa[wl_*AW +: LN]; ok_ = (wl_ == 0);
                    for (wk_ = 0; wk_ < NROT; wk_ = wk_ + 1) if (cbank(wl_, wk_) == wb_) ok_ = 1'b1;
                    if (!ok_) wcoll = 1'b1;
                    // two lanes on one bank must write the same row (the later lane wins, as a behavioural memory)
                    if (b_we[wb_] && b_wa[wb_] != lwa[wl_*AW + LN +: RB]) wcoll = 1'b1;
                    if (!(|sw_v_d)) begin b_we[wb_] = 1'b1; b_wa[wb_] = lwa[wl_*AW + LN +: RB]; b_wd[wb_] = lwd[32*wl_ +: 32]; end
                end
        end
        if (s1_v) begin
            if (b_we[s1_a[LN-1:0]]) wcoll = 1'b1;
            b_we[s1_a[LN-1:0]] = 1'b1; b_wa[s1_a[LN-1:0]] = s1_a[LWB-1:LN]; b_wd[s1_a[LN-1:0]] = s1_d;
        end
    end
    // ---- fail-closed checks (registered)
    reg [N-1:0] rq_q, lok_q; reg [RB-1:0] lr_q [0:N-1]; reg [RB-1:0] br_q [0:N-1]; reg srv_q, wcoll_q;
    always @(posedge clk) begin
        rq_q <= (|sr_v) ? {N{1'b0}} : rq; lok_q <= lok; srv_q <= ((|sr_v) && |rq) || src; wcoll_q <= wcoll;
        for (l = 0; l < N; l = l + 1) lr_q[l] <= ra[l*AW + LN +: RB];
        for (b = 0; b < N; b = b + 1) br_q[b] <= b_ra[b];
    end
    // FREG = 1 (HBM-REFORM-B10): the same terms, split per bank (exists l: rq && lb == b && row != bank row b, so the
    // compare sits next to bank b's row reg) plus the lane-candidate / srv / wcoll terms, registered (no reset, like the
    // check regs above), then ORed into flt one edge later.
    wire [N+N+1:0] fterm;
    for (genvar gfb = 0; gfb < N; gfb = gfb + 1) begin : g_fb
        reg bad;
        always @* begin : fbc
            integer i_;
            bad = 1'b0;
            for (i_ = 0; i_ < N; i_ = i_ + 1) if (rq_q[i_] && lb_q[i_] == gfb && lr_q[i_] != br_q[gfb]) bad = 1'b1;
        end
        assign fterm[gfb] = bad;
        assign fterm[N + gfb] = rq_q[gfb] && !lok_q[gfb];
    end
    assign fterm[2*N] = srv_q; assign fterm[2*N+1] = wcoll_q;
    reg [N+N+1:0] fq;
    always @(posedge clk) fq <= fterm;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) flt <= 1'b0;
        else if (FREG != 0) begin
            if (|fq) flt <= 1'b1;
        end else begin
            if (srv_q || wcoll_q) flt <= 1'b1;
            for (l = 0; l < N; l = l + 1)
                if (rq_q[l] && (!lok_q[l] || lr_q[l] != br_q[lb_q[l]])) flt <= 1'b1;
`ifdef LMEM_DBG
            if (srv_q) $display("LMEM_DBG %m sr during lane reads / sector-lane conflict");
            if (wcoll_q) $display("LMEM_DBG %m write collision");
            for (l = 0; l < N; l = l + 1)
                if (rq_q[l] && (!lok_q[l] || lr_q[l] != br_q[lb_q[l]]))
                    $display("LMEM_DBG %m read lane %0d bank %0d cand %0d row %0d bank-row %0d", l, lb_q[l], lok_q[l],
                             lr_q[l], br_q[lb_q[l]]);
`endif
        end
    end
    genvar gb;
    for (gb = 0; gb < N; gb = gb + 1) begin : g_bank
        wire k_re, k_we; wire [RB-1:0] k_ra, k_wa; wire [31:0] k_wd;
        if (BREG != 0) begin : g_breg
            reg q_re, q_we; reg [RB-1:0] q_ra, q_wa; reg [31:0] q_wd;
            // no reset: the uncut bank takes every op issued before a reset edge, so the delayed op must land too
            always @(posedge clk) begin q_re <= b_re[gb]; q_we <= b_we[gb]; q_ra <= b_ra[gb]; q_wa <= b_wa[gb]; q_wd <= b_wd[gb]; end
            assign k_re = q_re; assign k_we = q_we; assign k_ra = q_ra; assign k_wa = q_wa; assign k_wd = q_wd;
        end else begin : g_nobreg
            assign k_re = b_re[gb]; assign k_we = b_we[gb]; assign k_ra = b_ra[gb]; assign k_wa = b_wa[gb]; assign k_wd = b_wd[gb];
        end
        wire [31:0] raw_rd;
        if (RREG != 0) begin:g_rreg
            (* keep = 1 *) reg [31:0] q;
            always @(posedge clk) q <= raw_rd;
            assign b_rd[gb] = q;
        end else begin:g_raw
            assign b_rd[gb] = raw_rd;
        end
        ot_hgi_su_lbank #(.RB(RB), .MACRO(MACRO), .LAT(LAT)) u_b (.clk(clk), .re(k_re), .ra(k_ra), .rd(raw_rd),
            .we(k_we), .wa(k_wa), .wd(k_wd));
    end
endmodule
`default_nettype wire
