`timescale 1ns/1ps
// HBMc/QHUB4 10-22: exact lockstep of the HC quarter hub ot_hbm_hc_qhub_static LAND form (kits hbm_hcq_hub_c11a/b)
// against the c10 form (LAND 0 = the c10p40/b RTL bit for bit), both at the c10 kit parameters (SAFE 2, DRLY 2, CHX 11,
// RD_CAPTURE 39, GATHER_PHASE 39 / PERIOD 40, DONE_LAT 35, TARGET_SCAN_BOUNDARY 1).  Same random stimulus on every
// input; the bank ring answers the LAND hub DF edges later (its inputs are DF edges later), so s_i reaches the LAND hub
// DF edges after the c10 hub.  Every edge, every output port is compared against the c10 port DELAYED by its class:
//   bank-face  bd_*, wc_*, xb_v*, xb_beat*, xb_d0..7          DF  = LAND bit 1
//   subtree    ps_v, ps, ps_f                                  DPS = 2 * LAND bit 0 + LAND bit 1
//   gathered   gathered_mix_v/row/pos/data, gather_done        DG  = LAND bit 2
//   all other  ports                                           0
// Random fp32 chunk sums (biased exponents: cancellation, carry, subnormal, inf/nan), random task valids, random
// programme / descriptor / launch traffic for hc_<q>, one in-flight reset.  hc_<q> (ot_hbm_hc_q_static, unchanged) is
// left running, but its x_wave beat / face-control outputs and its gathered-mix outputs are FORCED in both hubs to the
// same random values every edge, so the hub glue that LAND changes (bank-face beat registers, gathered pin stage, the
// centre's x control copy) sees dense traffic (random hub stimulus alone never starts a residual / gather stream).
// +define+LAND=<n> (default 7), +define+LMUT=<n> (7 = landed valid hop skipped: must FAIL).
`ifndef LAND
`define LAND 7
`endif
`ifndef LMUT
`define LMUT 0
`endif
module tb_hbm_hc_qhub_land;
    localparam integer LAND = `LAND;
    localparam integer DF = ((LAND & 2) != 0) ? 1 : 0, DPS = 2 * (LAND & 1) + DF, DG = ((LAND & 4) != 0) ? 1 : 0;
    reg clk = 0, rst_n = 0; always #1 clk = ~clk;
    // ---------------------------------------------------------------- stimulus
    reg [7:0] tgt = 8'd37;
    reg cfg_v = 0; reg [7:0] cfg_target = 0; reg [11:0] cfg_addr = 0; reg [255:0] cfg_data = 0;
    reg desc_v = 0; reg [11:0] desc_base = 0; reg [12:0] desc_limit = 0; reg [15:0] desc_loops = 0; reg launch_v = 0;
    reg [2055:0] lg_rr = 0; reg [7:0] lg_w_done = 0;
    reg result_v = 0; reg [2:0] result_position = 0; reg [767:0] result = 0;
    reg d_v = 0, d_ss = 0; reg [6:0] d_nv = 0; reg [9:0] d_wa = 0, d_xa = 0;
    reg i_v = 0, i_kind = 0; reg [1:0] i_slot = 0; reg [4:0] i_lo = 0, i_w = 0; reg [11:0] i_cnt = 0; reg [9:0] i_word = 0;
    reg [2048:0] s_i = 0; reg wf_w = 0, wf_e = 0; reg [2:0] wf_n = 0, wf_s = 0;
    reg [2048:0] s_d [0:1];                  // s_i to the LAND hub: DF edges later (the ring runs DF edges later)
    always @(posedge clk) begin s_d[0] <= s_i; s_d[1] <= s_d[0]; end
    wire [2048:0] s_b = (DF != 0) ? s_d[0] : s_i;
    // ---------------------------------------------------------------- the two hubs
`define OT_QHUB_PORTS(P, SI) \
        .clk(clk), .rst_n(rst_n), .clk_t({4{clk}}), .tgt(tgt), .cfg_v(cfg_v), .cfg_target(cfg_target), .cfg_addr(cfg_addr), \
        .cfg_data(cfg_data), .desc_v(desc_v), .desc_base(desc_base), .desc_limit(desc_limit), .desc_loops(desc_loops), \
        .launch_v(launch_v), .configured(P``_cfgd), .lg_rq(P``_lg_rq), .lg_wq(P``_lg_wq), .lg_rr(lg_rr), .lg_w_done(lg_w_done), \
        .residual_done(P``_rdone), .gathered_mix_v(P``_g[0]), .gathered_mix_row(P``_g[5:1]), .gathered_mix_pos(P``_g[8:6]), \
        .gathered_mix_data(P``_g[40:9]), .gather_done(P``_g[41]), .result_v(result_v), .result_position(result_position), \
        .result(result), .program_active(P``_pa), .program_done(P``_pd), .hcq_fault(P``_hf), \
        .d_v(d_v), .d_ss(d_ss), .d_nv(d_nv), .d_wa(d_wa), .d_xa(d_xa), .i_v(i_v), .i_kind(i_kind), .i_slot(i_slot), \
        .i_lo(i_lo), .i_w(i_w), .i_cnt(i_cnt), .i_word(i_word), .ps_v(P``_p[0]), .ps(P``_p[32:1]), .ps_f(P``_p[33]), \
        .eng_fault(P``_ef), .rstb_w(P``_rb[0]), .rstb_n(P``_rb[3:1]), .rstb_e(P``_rb[4]), .rstb_s(P``_rb[7:5]), \
        .bd_v(P``_f[0]), .bd_ss(P``_f[1]), .bd_nv(P``_f[8:2]), .bd_wa(P``_f[18:9]), .bd_xa(P``_f[28:19]), .s_i(SI), \
        .wf_w(wf_w), .wf_e(wf_e), .wf_n(wf_n), .wf_s(wf_s), \
        .wc_w(P``_f[41:29]), .wc_n(P``_f[54:42]), .wc_e(P``_f[67:55]), .wc_s(P``_f[80:68]), \
        .xb_v(P``_f[81]), .xb_beat(P``_f[83:82]), .xb_v_n(P``_f[84]), .xb_v_e(P``_f[85]), .xb_v_s(P``_f[86]), \
        .xb_beat_n(P``_f[88:87]), .xb_beat_e(P``_f[90:89]), .xb_beat_s(P``_f[92:91]), \
        .xb_d0(P``_f[93+0*256 +: 256]), .xb_d1(P``_f[93+1*256 +: 256]), .xb_d2(P``_f[93+2*256 +: 256]), \
        .xb_d3(P``_f[93+3*256 +: 256]), .xb_d4(P``_f[93+4*256 +: 256]), .xb_d5(P``_f[93+5*256 +: 256]), \
        .xb_d6(P``_f[93+6*256 +: 256]), .xb_d7(P``_f[93+7*256 +: 256])
    localparam integer NF = 93 + 2048;
    wire a_cfgd, a_rdone, a_pa, a_pd, a_hf, a_ef; wire [135:0] a_lg_rq; wire [2247:0] a_lg_wq; wire [41:0] a_g;
    wire [33:0] a_p; wire [7:0] a_rb; wire [NF-1:0] a_f;
    wire b_cfgd, b_rdone, b_pa, b_pd, b_hf, b_ef; wire [135:0] b_lg_rq; wire [2247:0] b_lg_wq; wire [41:0] b_g;
    wire [33:0] b_p; wire [7:0] b_rb; wire [NF-1:0] b_f;
    ot_hbm_hc_qhub_static #(.DRLY(2), .CHX(11), .SAFE(2), .RD_CAPTURE(39), .GATHER_PHASE(39), .GATHER_PERIOD(40),
        .DONE_LAT(35), .TARGET_SCAN_BOUNDARY(1)) u_a (`OT_QHUB_PORTS(a, s_i));
    ot_hbm_hc_qhub_static #(.DRLY(2), .CHX(11), .SAFE(2), .RD_CAPTURE(39), .GATHER_PHASE(39), .GATHER_PERIOD(40),
        .DONE_LAT(35), .TARGET_SCAN_BOUNDARY(1), .LAND(LAND), .LMUT(`LMUT)) u_b (`OT_QHUB_PORTS(b, s_b));
    // ---------------------------------------------------------------- hc_<q> beat / gathered outputs forced (both hubs)
    reg [2047:0] fx = 0; reg [4:0] ffv = 0; reg [9:0] ffb = 0; reg [41:0] fg = 0;
    initial begin
        force u_a.xd = fx; force u_b.xd = fx; force u_a.xfv = ffv; force u_b.xfv = ffv; force u_a.xfb = ffb; force u_b.xfb = ffb;
        force u_a.gm_v_i = fg[0]; force u_b.gm_v_i = fg[0]; force u_a.gm_r_i = fg[5:1]; force u_b.gm_r_i = fg[5:1];
        force u_a.gm_p_i = fg[8:6]; force u_b.gm_p_i = fg[8:6]; force u_a.gm_d_i = fg[40:9]; force u_b.gm_d_i = fg[40:9];
        force u_a.gd_i = fg[41]; force u_b.gd_i = fg[41];
    end
    // ---------------------------------------------------------------- c10 outputs delayed by class
    localparam integer DMAX = 4;
    reg [NF-1:0] af_d [0:DMAX]; reg [33:0] ap_d [0:DMAX]; reg [41:0] ag_d [0:DMAX];
    always @* begin af_d[0] = a_f; ap_d[0] = a_p; ag_d[0] = a_g; end
    always @(posedge clk) for (integer k = 1; k <= DMAX; k = k + 1) begin
        af_d[k] <= af_d[k-1]; ap_d[k] <= ap_d[k-1]; ag_d[k] <= ag_d[k-1];
    end
    wire [NF-1:0] ef = af_d[DF]; wire [33:0] ep = ap_d[DPS]; wire [41:0] eg = ag_d[DG];
    // ---------------------------------------------------------------- random helpers
    function automatic [31:0] rnd_fp;
        input integer k;
        reg [31:0] r; reg [7:0] ex;
        begin
            r = $urandom;
            case (r[3:0])
                4'd0: ex = 8'd0;
                4'd1: ex = 8'hff;
                4'd2: ex = 8'hfe;
                4'd3: ex = 8'd1;
                default: ex = 8'd120 + 8'(r[8:4] & 5'd15);
            endcase
            rnd_fp = {r[31], ex, r[30:9] ^ {14'd0, 9'(k)}};
            if (r[13:10] == 4'd0) rnd_fp[30:0] = 31'd0;
        end
    endfunction
    integer cyc = 0, checks = 0, bad = 0, nps = 0, nxb = 0, ngm = 0, nbd = 0, nwc = 0;
    reg [NF-1:0] pf; reg [41:0] pg;
    wire quiet = (cyc < 40) || (cyc >= 9990 && cyc < 10040);      // reset windows (initial and in-flight)
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 8) rst_n <= 1;
        if (cyc == 10000) rst_n <= 0;
        if (cyc == 10010) rst_n <= 1;
        // hc_<q> traffic: programme writes (target = tgt half the time), descriptors, launches, LG returns, results
        cfg_v <= ($urandom % 4) == 0; cfg_target <= ($urandom % 2) ? tgt : 8'($urandom);
        cfg_addr <= 12'($urandom % 64); for (integer k = 0; k < 8; k = k + 1) cfg_data[k*32 +: 32] <= $urandom;
        desc_v <= ($urandom % 64) == 0; desc_base <= 12'($urandom % 16); desc_limit <= 13'($urandom % 64);
        desc_loops <= 16'($urandom % 4); launch_v <= ($urandom % 96) == 0;
        for (integer k = 0; k < 65; k = k + 1) lg_rr[k*32 +: 32] <= $urandom;
        for (integer b = 0; b < 8; b = b + 1) lg_rr[b*257 + 256] <= ($urandom % 3) == 0;
        lg_w_done <= 8'($urandom); result_v <= ($urandom % 8) == 0; result_position <= 3'($urandom);
        for (integer k = 0; k < 24; k = k + 1) result[k*32 +: 32] <= $urandom;
        // centre: descriptors (task valids), ingest events, chunk sums; no task within 12 edges of a reset edge
        d_v <= (($urandom % 3) != 0) && !quiet; d_ss <= $urandom; d_nv <= 7'($urandom); d_wa <= 10'($urandom); d_xa <= 10'($urandom);
        i_v <= (($urandom % 16) == 0) && !quiet; i_kind <= $urandom; i_slot <= 2'($urandom); i_lo <= 5'($urandom % 8);
        i_w <= 5'($urandom % 20); i_cnt <= 12'($urandom % 8 + 1); i_word <= 10'($urandom);
        for (integer k = 0; k < 64; k = k + 1) s_i[k*32 +: 32] <= rnd_fp(k);
        s_i[2048] <= ($urandom % 64) == 0;
        for (integer k = 0; k < 64; k = k + 1) fx[k*32 +: 32] <= $urandom;
        ffv <= 5'($urandom); ffb <= 10'($urandom); fg <= {10'($urandom), $urandom};
        {wf_w, wf_e} <= 2'd0; wf_n <= 3'd0; wf_s <= 3'd0;
        // compare
        if (rst_n && !quiet) begin
            checks <= checks + 1;
            if ({b_cfgd, b_lg_rq, b_lg_wq, b_rdone, b_pa, b_pd, b_hf, b_ef, b_rb} !==
                {a_cfgd, a_lg_rq, a_lg_wq, a_rdone, a_pa, a_pd, a_hf, a_ef, a_rb}) begin
                bad <= bad + 1; if (bad < 6) $display("MISMATCH same cyc=%0d", cyc);
            end
            if (b_f !== ef) begin bad <= bad + 1; if (bad < 6) $display("MISMATCH bank-face cyc=%0d", cyc); end
            if (b_p !== ep) begin bad <= bad + 1; if (bad < 6) $display("MISMATCH subtree cyc=%0d b=%h e=%h", cyc, b_p, ep); end
            if (b_g !== eg) begin bad <= bad + 1; if (bad < 6) $display("MISMATCH gathered cyc=%0d", cyc); end
            if (a_p[0]) nps <= nps + 1;
            if (a_f[2140:93] != pf[2140:93]) nxb <= nxb + 1;
            if (a_f[0]) nbd <= nbd + 1;
            if (a_f[41:29] != pf[41:29]) nwc <= nwc + 1;
            if (a_g[41:1] != pg[41:1]) ngm <= ngm + 1;
        end
        pf <= a_f; pg <= a_g;
        if (cyc == 20000) begin
            $display("QHUB_LAND activity ps_v=%0d bd_v=%0d xb_d_changes=%0d wc_changes=%0d gathered_changes=%0d", nps, nbd, nxb, nwc, ngm);
            if (bad == 0 && checks > 15000 && nps > 1000 && nxb > 1000 && nwc > 1000 && ngm > 1000) $display("QHUB_LAND PASS LAND=%0d LMUT=%0d DF=%0d DPS=%0d DG=%0d checks=%0d",
                LAND, `LMUT, DF, DPS, DG, checks);
            else $display("QHUB_LAND FAIL LAND=%0d LMUT=%0d bad=%0d checks=%0d", LAND, `LMUT, bad, checks);
            $finish;
        end
    end
endmodule
