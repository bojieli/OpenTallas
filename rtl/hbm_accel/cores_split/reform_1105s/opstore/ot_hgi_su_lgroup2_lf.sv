// HBM-REFORM-B9 (2026-11-05): tile-local log-depth form of ot_hgi_su_lgroup2 for the part 27 opstore group tiles.
// Same ports, parameters, registers and function as ot_hgi_su_lgroup2 (rtl/hbm_accel/generic/peers/ot_hgi_su_unit.sv);
// only the two combinational selects (lane read row per bank, stage write per bank) are rewritten as one-hot priority
// selects. Cause: the sequential "last assignment wins" loops synthesised as 64-deep OA211/AO21 chains to the SRAM
// wd_in (CTS setup -1622 ps on opsa_group0). Requires N >= 8 (8 consecutive stage words on distinct banks); N = 16 here.
`timescale 1ns/1ps
`default_nettype none
module ot_hgi_su_lgroup2_lf #(
    parameter integer N = 16, M = 8, LWB = 17, AW = 24,
    parameter integer NLW = 0,             // lane write ports (GO: N)
    parameter integer MACRO = 1,
    parameter integer MUT_XBAR = 0,        // bench mutant: identity lanes take the neighbouring bank's word
    parameter integer LAT = 0,             // bench mutant: bank read latency 1 = +1 edge, 2 = -1 edge (see ot_hgi_su_lbank)
    parameter integer NS = 1               // sector lanes: NS independent 8-word stage writes / drain reads an edge
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
    assign sr_rv = (LAT == 1) ? srv2 : (LAT == 2) ? sr_v : srv1;
    wire [LN-1:0] lb_s [0:N-1];
    for (genvar gs_ = 0; gs_ < N; gs_ = gs_ + 1) begin : g_ls
        assign lb_s[gs_] = (LAT == 1) ? lb_q2[gs_] : (LAT == 2) ? ra[gs_*AW +: LN] : lb_q[gs_];
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
        wire [LN-1:0] sr_s = (LAT == 1) ? sr_lo2[gk] : (LAT == 2) ? sr_addr[gk*LWB +: LN] : sr_lo[gk];
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
            wire [LWB-1:0] a = sw_addr[gsw*LWB +: LWB];
            wire [LN-1:0] off = LN'(gbw) - a[LN-1:0];
            wire [2:0] o3 = off[2:0];
            assign h[gsw] = sw_v[gsw] && off < LN'(8) && sw_mask[gsw*8 + o3];
            assign rw[gsw] = a[LWB-1:LN] + RB'(LN'(gbw) < a[LN-1:0]);
            assign dw[gsw] = sw_d[gsw*256 + 32*o3 +: 32];
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
            if (|sw_v && |lw) wcoll = 1'b1;
            for (wl_ = 0; wl_ < NL; wl_ = wl_ + 1)
                if (lw[wl_]) begin
                    wb_ = lwa[wl_*AW +: LN]; ok_ = (wl_ == 0);
                    for (wk_ = 0; wk_ < NROT; wk_ = wk_ + 1) if (cbank(wl_, wk_) == wb_) ok_ = 1'b1;
                    if (!ok_) wcoll = 1'b1;
                    // two lanes on one bank must write the same row (the later lane wins, as a behavioural memory)
                    if (b_we[wb_] && b_wa[wb_] != lwa[wl_*AW + LN +: RB]) wcoll = 1'b1;
                    if (!(|sw_v)) begin b_we[wb_] = 1'b1; b_wa[wb_] = lwa[wl_*AW + LN +: RB]; b_wd[wb_] = lwd[32*wl_ +: 32]; end
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
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) flt <= 1'b0;
        else begin
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
        ot_hgi_su_lbank #(.RB(RB), .MACRO(MACRO), .LAT(LAT)) u_b (.clk(clk), .re(b_re[gb]), .ra(b_ra[gb]), .rd(b_rd[gb]),
            .we(b_we[gb]), .wa(b_wa[gb]), .wd(b_wd[gb]));
    end
endmodule
`default_nettype wire
