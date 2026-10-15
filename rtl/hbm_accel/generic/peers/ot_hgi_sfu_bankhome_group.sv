`timescale 1ns/1ps
`default_nettype none
// Original global arbitration semantics, physically only HOME four banks.
// Nonowned words are zero contributions to the registered HOME0 return join.
module ot_hgi_sfu_bankhome_group #(
    parameter integer HOME = 0,
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
    always @* begin : rsel
        integer rj_, sl_; reg [LWB-1:0] sa; reg [LN-1:0] bl;
        sa = {LWB{1'b0}}; bl = {LN{1'b0}};
        for (b = 0; b < N; b = b + 1) begin b_re[b] = 1'b0; b_ra[b] = {RB{1'b0}}; end
        for (l = 0; l < N; l = l + 1) begin
            bl = ra[l*AW +: LN]; lok[l] = (l == 0);
            for (k = 0; k < NCAND; k = k + 1) if (cbank(l, k) == bl) lok[l] = 1'b1;
        end
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
            // lowest-index lane wins a bank (the bank's row); the others must agree (checked below)
            for (l = N - 1; l >= 0; l = l - 1)
                if (rr[l] && lok[l]) begin
                    bl = ra[l*AW +: LN]; b_re[bl] = 1'b1; b_ra[bl] = ra[l*AW + LN +: RB];
                end
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
    always @* begin : wsel
        integer wl_, wj_, wk_, ws_; reg [LWB-1:0] sb; reg [LN-1:0] wb_; reg ok_;
        sb = {LWB{1'b0}}; wb_ = {LN{1'b0}}; ok_ = 1'b0;
        for (b = 0; b < N; b = b + 1) begin b_we[b] = 1'b0; b_wa[b] = {RB{1'b0}}; b_wd[b] = 32'd0; end
        wcoll = 1'b0;
        for (ws_ = 0; ws_ < NS; ws_ = ws_ + 1) if (sw_v[ws_])
            for (wj_ = 0; wj_ < 8; wj_ = wj_ + 1) if (sw_mask[ws_*8 + wj_]) begin
                sb = sw_addr[ws_*LWB +: LWB] + wj_;
                if (b_we[sb[LN-1:0]]) wcoll = 1'b1;          // two sector lanes on one bank: fail closed
                b_we[sb[LN-1:0]] = 1'b1; b_wa[sb[LN-1:0]] = sb[LWB-1:LN]; b_wd[sb[LN-1:0]] = sw_d[ws_*256 + 32*wj_ +: 32];
            end
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
        if (gb / 4 == HOME) begin:g_owned
        ot_hgi_su_lbank #(.RB(RB), .MACRO(MACRO), .LAT(LAT)) u_b (.clk(clk), .re(b_re[gb]), .ra(b_ra[gb]), .rd(b_rd[gb]),
            .we(b_we[gb]), .wa(b_wa[gb]), .wd(b_wd[gb]));
        end else begin:g_remote
            assign b_rd[gb] = 32'd0;
        end
    end
endmodule
`default_nettype wire
