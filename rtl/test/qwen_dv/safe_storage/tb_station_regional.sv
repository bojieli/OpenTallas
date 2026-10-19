`timescale 1ns/1ps
// QW-SLICE 10-19: the 8-region station (qfd_dv_redstn2_rg, all ck_r on one clock) against the R8/R9 monolith
// (qfd_dv_redstn2, gsafe) under constrained-random stimulus, two resets.  Every data/control output must match on
// every edge; fault may only rise late by the landed ring bound (<= FLT_LAG edges) and never early.
// MUT (both sides, station mutants): 3 bt_word+1, 14 kcm1 ignored, 16 skew-S one edge short, 17 h9 bypass off.
// RMUT (regional side only, witnesses): 1 = region 5 lanes take region 4's bt_q slice; 2 = fault ring hop 3->1 cut.
// PIN (0/1): regional PIN_IN = BT_LAT = PIN; the bt table is modelled (one-edge read of a hashed clean table) on both
// sides, so with PIN=1 every regional output equals the monolith output PIN edges earlier.
module tb_station_regional #(parameter integer MUT=0, RMUT=0, NCYC=20000, PIN=0);
reg ck=0; always #5 ck=~ck;
integer cycle=0;
reg rst_n=0, quiet=1;
reg cfg_v=0; reg [1:0] cfg_mode=0; reg cfg_wsrc=0; reg [7:0] cfg_nwords=0; reg [8:0] cfg_sbase=0; reg [7:0] cfg_kcm1=0;
reg [1027:0] rs_s=0, rs_n=0; reg [513:0] nb_i=0; reg [255:0] bt_q=0, bt_q_g=0;
localparam integer FLT_LAG = 32;
function automatic [31:0] fpr(input integer clean);   // finite fp32 (exponent 100..163); rare specials if !clean
    reg [31:0] x; begin x = $random; x[30:23] = 8'd100 + (x[30:23] & 8'h3f); if (!clean && (($random & 63) == 0)) x[30:23] = 8'hff; fpr = x; end
endfunction
// Phase 1 (first reset): protocol-legal mode-0 traffic, valid pattern of period SKEW (hi half = lo half 14 edges
// later), configuration only in a 5-edge valid-free window, clean data: the station must NOT fault until one NaN is
// injected into lane 6 (region 3) at edge INJ; fault must then reach the region-0 output through the landed ring.
// Phase 2 (second reset): unconstrained random traffic, all modes, specials, colliding configuration.
localparam integer INJ = NCYC/4;
localparam [13:0] PAT = 14'b10110110100000;
reg inj_done = 0;
reg [14:0] lo_hist = 0; reg active = 0; integer ph = 0;   // far (hi) valid = near (lo) valid SKEW=14 edges earlier: bit 14 (bit 0 = this edge)
always @(negedge ck) begin
    cycle = cycle + 1;
    rst_n = !((cycle < 6) || (cycle >= NCYC/2 && cycle < NCYC/2 + 6));
    quiet = (cycle < 60) || (cycle >= NCYC/2 - 40 && cycle < NCYC/2 + 60);
    for (integer l = 0; l < 16; l = l + 1) begin
        rs_s[32*l +: 32] = fpr(cycle < NCYC/2); rs_s[514+32*l +: 32] = fpr(cycle < NCYC/2);
        rs_n[32*l +: 32] = fpr(cycle < NCYC/2); rs_n[514+32*l +: 32] = fpr(cycle < NCYC/2);
        nb_i[32*l +: 32] = fpr(cycle < NCYC/2);
    end
    if (cycle < NCYC/2) begin
        ph = cycle % 14;
        active = (cycle >= 60 && cycle < NCYC/2 - 80);
        cfg_v = (cycle == 40) || (active && ph == 1 && (cycle % 224) < 14);
        cfg_mode = 0; cfg_wsrc = (cycle/8)%2; cfg_nwords = 8'd255; cfg_sbase = (cycle/16)%512; cfg_kcm1 = 0;
        lo_hist = {lo_hist[13:0], active && PAT[ph]};
        rs_s[512] = active && PAT[ph]; rs_n[512] = active && PAT[ph];
        rs_s[1026] = lo_hist[14]; rs_n[1026] = lo_hist[14];
        rs_s[513] = 0; rs_s[1027] = 0; rs_n[513] = 0; rs_n[1027] = 0; nb_i[513:512] = 0;
        if (cycle >= INJ && lo_hist[14] && !inj_done) begin rs_s[514+32*6 +: 32] = 32'h7fc00000; inj_done = 1; end
    end else if (quiet) begin
        cfg_v = 0; rs_s = 0; rs_n = 0; nb_i = 0;
    end else begin
        cfg_v = (($random & 255) == 0);
        if (cfg_v) begin cfg_mode = $random; cfg_wsrc = $random; cfg_nwords = 1 + ($random & 63); cfg_sbase = $random; cfg_kcm1 = $random & 3; end
        begin : vbits
            reg v; v = (($random & 3) != 0);
            rs_s[512] = v; rs_s[1026] = v; rs_n[512] = v; rs_n[1026] = v;
            nb_i[512] = (($random & 7) == 0);
            rs_s[513] = (($random & 4095) == 0); rs_s[1027] = 0; rs_n[513] = 0; rs_n[1027] = 0; nb_i[513] = 0;
        end
    end
end
function automatic [255:0] bt_row(input [8:0] w);
    reg [255:0] x; reg [31:0] h; begin
        for (integer l = 0; l < 16; l = l + 1) begin
            h = (w * 32'h9e3779b1) ^ (l * 32'h85ebca6b); h = h ^ (h >> 13); h = h * 32'hc2b2ae35;
            x[16*l +: 16] = {h[15], 8'd120 + {4'd0, h[3:0]}, h[10:4]};
        end
        bt_row = x;
    end
endfunction
always @(posedge ck) begin bt_q <= bt_row(m_bt_word); bt_q_g <= bt_row(g_bt_word); end
// monolith
wire [513:0] m_nb_o; wire m_bt_re; wire [8:0] m_bt_word; wire m_r_v; wire [7:0] m_r_idx; wire m_r_last; wire [511:0] m_r_d; wire m_fault;
qfd_dv_redstn2 #(.MUT(MUT)) u_m (.ck(ck), .rst_n(rst_n), .cfg_v(cfg_v), .cfg_mode(cfg_mode), .cfg_wsrc(cfg_wsrc),
    .cfg_nwords(cfg_nwords), .cfg_sbase(cfg_sbase), .cfg_kcm1(cfg_kcm1), .rs_s(rs_s), .rs_n(rs_n), .nb_i(nb_i), .nb_o(m_nb_o),
    .bt_re(m_bt_re), .bt_word(m_bt_word), .bt_q(bt_q), .r_v(m_r_v), .r_idx(m_r_idx), .r_last(m_r_last), .r_d(m_r_d), .fault(m_fault));
// regional (per-region copies of every control input, one clock)
wire [28:0] c = {cfg_v, cfg_mode, cfg_wsrc, cfg_nwords, cfg_sbase, cfg_kcm1};
wire [255:0] bt_q_r = (RMUT == 1) ? {bt_q_g[255:192], bt_q_g[159:128], bt_q_g[159:0]} : bt_q_g;
wire [513:0] g_nb_o; wire g_bt_re; wire [8:0] g_bt_word; wire g_r_v; wire [7:0] g_r_idx; wire g_r_last; wire [511:0] g_r_d; wire g_fault;
qfd_dv_redstn2_rg #(.MUT(MUT),.PIN_IN(PIN),.BT_LAT(PIN)) u_g (.ck_r({8{ck}}), .rst_n_r({8{rst_n}}), .cfg_r({8{c}}),
    .rs_s_lo(rs_s[511:0]), .rs_s_hi(rs_s[1025:514]), .rs_n_lo(rs_n[511:0]), .rs_n_hi(rs_n[1025:514]),
    .rs_s_c({8{rs_s[1027:1026], rs_s[513:512]}}), .rs_n_c({8{rs_n[1027:1026], rs_n[513:512]}}),
    .nb_d(nb_i[511:0]), .nb_c({8{nb_i[513:512]}}), .nb_od(g_nb_o[511:0]), .nb_oc(g_nb_o[513:512]),
    .bt_re(g_bt_re), .bt_word(g_bt_word), .bt_q(bt_q_r), .r_v(g_r_v), .r_idx(g_r_idx), .r_last(g_r_last), .r_d(g_r_d), .fault(g_fault));
generate if (RMUT == 2) begin : g_cut
    initial begin #1; force u_g.fb[3] = 4'd0; force u_g.fv[3] = 4'd0; end
end endgenerate
// fault: sticky in both; regional may lag by <= FLT_LAG (+PIN) edges and never lead.
localparam integer OW = 514 + 1 + 9 + 1 + 8 + 1 + 512;
wire [OW-1:0] m_out = {m_nb_o, m_bt_re, m_bt_word, m_r_v, m_r_idx, m_r_last, m_r_d};
wire [OW-1:0] g_out = {g_nb_o, g_bt_re, g_bt_word, g_r_v, g_r_idx, g_r_last, g_r_d};
reg [OW-1:0] m_out_d = 0;
reg [FLT_LAG+1:0] m_hist = 0;
integer mism = 0, rv_n = 0, flt_m_n = 0, nb_n = 0, bt_n = 0;
always @(posedge ck) begin
    #1;
    if (!rst_n) m_hist = 0; else m_hist = {m_hist[FLT_LAG:0], m_fault};
    if (rst_n && cycle > 12) begin
        if ((PIN ? m_out_d : m_out) !== g_out) begin
            mism = mism + 1;
            if (mism <= 5) $display("REGIONAL_MISMATCH edge%0d", cycle);
            if (mism == 5) $fatal(1, "REGIONAL_STATION_MISMATCH");
        end
        if (g_fault && !m_hist[PIN]) $fatal(1, "REGIONAL_FAULT_EARLY edge%0d", cycle);
        if (m_hist[FLT_LAG] && !g_fault) $fatal(1, "REGIONAL_FAULT_LATE edge%0d (> %0d edges)", cycle, FLT_LAG);
    end
    m_out_d = m_out;
    if (rst_n && m_fault && !m_hist[1] && flt_m_n == 0)
        $display("FAULT_SOURCE edge%0d mono in_bad%0d fp_bad%0d cfg_sched%0d", cycle, u_m.in_bad, u_m.fp_bad, u_m.cfg_schedule_fault);
    if (cycle < INJ && rst_n && m_fault) $fatal(1, "PHASE1_UNEXPECTED_FAULT edge%0d (stimulus not protocol-legal)", cycle);
    if (cycle == NCYC/2 - 2 && !(m_fault && g_fault)) $fatal(1, "PHASE1_INJECTED_FAULT_MISSING mono%0d regional%0d", m_fault, g_fault);
    if (m_r_v) rv_n = rv_n + 1;
    if (m_bt_re) bt_n = bt_n + 1;
    if (m_nb_o[512]) nb_n = nb_n + 1;
    if (m_fault && !m_hist[1]) flt_m_n = flt_m_n + 1;
end
initial begin
    repeat (NCYC) @(negedge ck);
    if (rv_n < 20 || bt_n < 20) $fatal(1, "REGIONAL_COVERAGE_LOW r_v%0d bt_re%0d", rv_n, bt_n);
    $display("STATION_REGIONAL_EQ PASS PIN%0d MUT%0d edges%0d tworesets r_v%0d bt_re%0d nb_v%0d fault_rises%0d all outputs exact, fault lag<=%0d",
        PIN, MUT, NCYC, rv_n, bt_n, nb_n, flt_m_n, FLT_LAG);
    $finish;
end
endmodule
