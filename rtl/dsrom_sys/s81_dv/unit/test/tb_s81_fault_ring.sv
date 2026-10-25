`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81/PORTFIX-FLT (2026-10-25, S81 DECISION 4): end-to-end bench of the die fault network.
//   unit fault (1-cycle pulse on a stop's f input = a unit's sticky fault rising)
//     -> ot_s81_frs ring stops (sid ring: 16 C-slice stops; vid ring: 16 svc stops, two of them ot_s81_frs0)
//     -> dsdv_hostb_seqhost_mux (REAL: dsdv_seq_host_mux core + HOSTB source; ring ends land, sticky die fault word)
//     -> t_host status field -> ot_s81sl_lep (REAL host plane, HOST_EN 1) -> 2 lanes + UCIe PMA -> host-side endpoint
//     -> decoded THOST frames (behavioural host codec of tb_s81sl_lep_host).
// Checks (each phase):
//   LAT   the fault bit of t_host rises EXACTLY 4 + (15 - k) edges after the edge that captured the pulse at stop k
//         (stop hop 1, 15 - k downstream hops, ring-end pin flop, sticky word, word register; the stop's sticky bit is
//         the capture edge itself).  Own fault -> sid bit via the ring head: 16 + 3 edges after the own bit.
//   STICK the ring end stays 1 on every edge after it rose (the stop holds the fault, not the pulse).
//   SEP   a vid fault leaves the sid bit 0 (rings and word fields are separate).
//   HOST  the last THOST frame the host decodes carries the expected {fault, sid, vid, own} bits.
//   RESET a die reset (control state) clears the word, the stops and the rings; the host sees a frame with them 0.
//   OWN   the unit's own fault (HOSTB landing fault: a legacy host word while HBE is selected) sets own, and via the
//         ring heads also sid / vid after a full ring traversal.
// Mutants (must FAIL): FRS_MUT 1 stop not sticky (STICK), 2 ring OR dropped (LAT), 3 local fault dropped (LAT);
//   FMUT 1 ring heads not driven (OWN), 2 own bit dropped from the word (OWN), 3 sid / vid fields swapped (SEP / HOST).
// Verdict: "PASS fault_ring ..." or "FAIL fault_ring ...".
// ---------------------------------------------------------------------------------------------------------------------
module tb_s81_fault_ring #(parameter integer FRS_MUT = 0, parameter integer FMUT = 0, parameter integer WAIT = 8000);
    localparam integer NS = 16;
    reg clk = 0; always #0.4167 clk = ~clk;
    reg rst_n = 0;          // lep / lanes / host endpoint
    reg rst_f = 0;          // die fault network + seqhost (the reset wavefront of the control state)
    integer cyc = 0;
    always @(posedge clk) cyc <= cyc + 1;
    // ---------------- seqhost (REAL die master) + rings
    reg select_hbe = 0; reg [514:0] f_host = 0;
    wire [76:0] t_host; wire [53:0] t_kd;
    wire sid_ro, vid_ro, sid_ri, vid_ri;
    wire [275:0] vo_s, vo_n; wire [32:0] s_j; wire [291:0] s_hw_w, s_hw_e; wire cw_v; wire [9:0] cw_a; wire [255:0] cw_d;
    wire [33:0] mc0, mc1, mc2, mc3; wire [10:0] mr0, mr1, mr2, mr3; wire [52:0] egks; wire armed;
    dsdv_hostb_seqhost_mux #(.HOSTB_ENABLE(1), .STATIC_KS6(0), .FMUT(FMUT)) u_sh (.ck(clk), .rst_n(rst_f), .tap_k(8'h00),
        .sink_k(8'h00), .vi_s(276'd0), .vo_s(vo_s), .vi_n(276'd0), .vo_n(vo_n), .select_hbe(select_hbe), .hbe_f_host(515'd0),
        .starter_f_ks(53'd0), .hbe_ks_slot(3'd0), .engram_f_ks(egks), .hb_starter_armed(armed), .f_host(f_host),
        .t_host(t_host), .f_lf(4'b0101), .f_ks(53'd0), .t_kd(t_kd), .sid_ri(sid_ri), .vid_ri(vid_ri), .sid_ro(sid_ro),
        .vid_ro(vid_ro), .s_j(s_j), .s_jd_w(2'b00), .s_jd_e(2'b00), .s_hw_w(s_hw_w), .s_hw_e(s_hw_e), .s_hc_w(9'd0),
        .s_hc_e(9'd0), .st_rg_w(2'b01), .st_rg_e(2'b01), .cw_v(cw_v), .cw_a(cw_a), .cw_d(cw_d), .mu_c_7n(mc0), .mu_c_7s(mc1),
        .mu_c_0n(mc2), .mu_c_0s(mc3), .mu_rc_7n(mr0), .mu_rc_7s(mr1), .mu_rc_0n(mr2), .mu_rc_0s(mr3), .mu_rt_7n(32'd0),
        .mu_rt_0n(32'd0));
    reg [2*NS-1:0] sf = 0;     // sid stop unit faults (2 a stop: e.g. the slice fault + a feeder lane)
    reg [3*NS-1:0] vf = 0;     // vid stop unit faults (3 a stop: e.g. irg + svc entry + etap)
    wire [NS:0] sr, vr;
    assign sr[0] = sid_ro; assign vr[0] = vid_ro; assign sid_ri = sr[NS]; assign vid_ri = vr[NS];
    genvar g;
    generate for (g = 0; g < NS; g = g + 1) begin : g_st
        ot_s81_frs #(.NL(2), .MUT(FRS_MUT)) u_s (.ck(clk), .rst_n(rst_f), .f(sf[2*g +: 2]), .fi(sr[g]), .fo(sr[g+1]));
        if (g == 1 || g == 9) begin : g_v0   // svc partitions with no local fault source
            ot_s81_frs0 u_v (.ck(clk), .rst_n(rst_f), .fi(vr[g]), .fo(vr[g+1]));
        end else begin : g_v
            ot_s81_frs #(.NL(3), .MUT(FRS_MUT)) u_v (.ck(clk), .rst_n(rst_f), .f(vf[3*g +: 3]), .fi(vr[g]), .fo(vr[g+1]));
        end
    end endgenerate
    // ---------------- s_7N lep (REAL host plane) + lanes + PHY, host-side endpoint (as tb_s81sl_lep_host)
    wire [1103:0] a_ri; wire a_f; wire [514:0] a_fh; wire [3:0] f_lf; wire [52:0] a_fks;
    wire a0v, a0r, a1v, a1r, ai0v, ai0r, ai1v, ai1r; wire [552:0] a0d, a1d, ai0d, ai1d; wire [2:0] af0, af1; wire [1:0] arxv;
    wire h0r, h1r, hi0v, hi1v; wire [552:0] hi0d, hi1d; wire [2:0] hf0, hf1;
    wire [511:0] atx0, atx1, htx0, htx1, arx0, arx1, hrx0, hrx1; wire [1:0] ast0, ast1, hst0, hst1;
    wire [512:0] pa0, pa1, ph0, ph1; wire ta0, ta1, th0, th1;
    ot_s81sl_lep la (.clk(clk), .rst_n(rst_n), .ro(1104'd0), .ri(a_ri),
        .lo0_v(a0v), .lo0_r(a0r), .lo0_d(a0d), .lo1_v(a1v), .lo1_r(a1r), .lo1_d(a1d),
        .li0_v(ai0v), .li0_r(ai0r), .li0_d(ai0d), .li1_v(ai1v), .li1_r(ai1r), .li1_d(ai1d), .rxv(arxv),
        .sl_f(1'b0), .l0_f(af0), .l1_f(af1), .l0_st(ast0), .l1_st(ast1),
        .t_host(t_host), .t_kd(54'd0), .f_host(a_fh), .f_lf(f_lf), .f_ks(a_fks), .fault(a_f));
    dsfd_coll_lane_w #(.LCR(1)) a_l0 (.ck(clk), .rs(rst_n), .chb(1'b0), .rx({ast0[0], ast0[1], arx0, arxv[0]}), .tx(atx0), .tf(),
        .lo_v(a0v), .lo_r(a0r), .lo_d(a0d), .li_v(ai0v), .li_r(ai0r), .li_d(ai0d), .flt(af0));
    dsfd_coll_lane_w #(.LCR(1)) a_l1 (.ck(clk), .rs(rst_n), .chb(1'b0), .rx({ast1[0], ast1[1], arx1, arxv[1]}), .tx(atx1), .tf(),
        .lo_v(a1v), .lo_r(a1r), .lo_d(a1d), .li_v(ai1v), .li_r(ai1r), .li_d(ai1d), .flt(af1));
    dsfd_coll_lane_e h_l0 (.ck(clk), .rs(rst_n), .chb(1'b0), .rx({hst0[0], hst0[1], hrx0, rst_n}), .tx(htx0), .tf(),
        .lo_v(1'b0), .lo_r(h0r), .lo_d(553'd0), .li_v(hi0v), .li_r(1'b1), .li_d(hi0d), .flt(hf0));
    dsfd_coll_lane_e h_l1 (.ck(clk), .rs(rst_n), .chb(1'b0), .rx({hst1[0], hst1[1], hrx1, rst_n}), .tx(htx1), .tf(),
        .lo_v(1'b0), .lo_r(h1r), .lo_d(553'd0), .li_v(hi1v), .li_r(1'b1), .li_d(hi1d), .flt(hf1));
    ot_pdie_ucie #(.PMA_LAT(2)) ua0 (.clk(clk), .rst(rst_n), .tx(atx0), .rx(arx0), .st(ast0), .pma_tx(pa0), .pma_tck(ta0), .pma_rx(ph0), .pma_rck(th0));
    ot_pdie_ucie #(.PMA_LAT(2)) uh0 (.clk(clk), .rst(rst_n), .tx(htx0), .rx(hrx0), .st(hst0), .pma_tx(ph0), .pma_tck(th0), .pma_rx(pa0), .pma_rck(ta0));
    ot_pdie_ucie #(.PMA_LAT(6)) ua1 (.clk(clk), .rst(rst_n), .tx(atx1), .rx(arx1), .st(ast1), .pma_tx(pa1), .pma_tck(ta1), .pma_rx(ph1), .pma_rck(th1));
    ot_pdie_ucie #(.PMA_LAT(6)) uh1 (.clk(clk), .rst(rst_n), .tx(htx1), .rx(hrx1), .st(hst1), .pma_tx(ph1), .pma_tck(th1), .pma_rx(pa1), .pma_rck(ta1));
    // host endpoint: reassemble frames (flit pair), keep the last THOST status word
    reg [552:0] r0 [0:8191]; reg [552:0] r1 [0:8191]; integer rn0 = 0, rn1 = 0, rk = 0, nth = 0, bad = 0;
    reg [1103:0] fx; reg [11:0] hst = 12'd0; reg hst_v = 0;
    always @(posedge clk) begin
        if (hi0v) begin r0[rn0 % 8192] = hi0d; rn0 = rn0 + 1; end
        if (hi1v) begin r1[rn1 % 8192] = hi1d; rn1 = rn1 + 1; end
        while (rk < rn0 && rk < rn1) begin
            fx = {r1[rk % 8192][551:0], r0[rk % 8192][551:0]};
            if (!fx[0] && fx[3:1] == 3'd3) begin
                hst = fx[4 + 65 +: 12]; hst_v = 1; nth = nth + 1;
                $display("HOST THOST %0d status %03h {alive %b fault %b sid %b vid %b own %b wf %b}", cyc, hst, hst[11], hst[10],
                         hst[9], hst[8], hst[7], hst[6]);
            end else if (!fx[0] && fx[3:1] != 3'd4) begin bad = bad + 1; $display("ERR unexpected frame type %0d", fx[3:1]); end
            rk = rk + 1;
        end
    end
    // ---------------- checks
    integer e_cap, e_bit, lat, nphase = 0;
    // STICK monitors: once a ring end is 1 it must stay 1 until rst_f
    reg sid_seen = 0, vid_seen = 0;
    always @(posedge clk) begin
        if (!rst_f) begin sid_seen <= 0; vid_seen <= 0; end
        else begin
            if (sid_ri) sid_seen <= 1; else if (sid_seen) begin bad = bad + 1; if (bad < 8) $display("ERR STICK sid ring end fell at %0d", cyc); end
            if (vid_ri) vid_seen <= 1; else if (vid_seen) begin bad = bad + 1; if (bad < 8) $display("ERR STICK vid ring end fell at %0d", cyc); end
        end
    end
    // pulse one unit fault at stop k (ring 0 = sid, 1 = vid) for one cycle; return the capture edge index
    task automatic pulse(input integer ring, input integer k, input integer b);
        begin
            @(negedge clk);
            if (ring == 0) sf[2*k + b] = 1'b1; else vf[3*k + b] = 1'b1;
            @(posedge clk); #0.01; e_cap = cyc;
            @(negedge clk);
            if (ring == 0) sf[2*k + b] = 1'b0; else vf[3*k + b] = 1'b0;
        end
    endtask
    // wait for t_host[bit] and check the latency from the capture edge
    task automatic expect_bit(input integer bitn, input integer want, input string what);
        integer t0;
        begin
            t0 = cyc;
            do begin @(posedge clk); #0.01; end while (t_host[bitn] !== 1'b1 && cyc < t0 + 200);
            lat = cyc - e_cap;
            if (t_host[bitn] !== 1'b1) begin bad = bad + 1; $display("ERR LAT %s: t_host[%0d] never rose", what, bitn); end
            else if (lat != want) begin bad = bad + 1; $display("ERR LAT %s: t_host[%0d] rose %0d edges after capture, want %0d", what, bitn, lat, want); end
            else $display("OK  LAT %s: t_host[%0d] %0d edges after capture", what, bitn, lat);
        end
    endtask
    task automatic expect_host(input [3:0] w, input string what);   // {fault, sid, vid, own}
        begin
            repeat (400) @(posedge clk);
            if (!hst_v || hst[10:7] !== w) begin bad = bad + 1; $display("ERR HOST %s: last THOST {fault,sid,vid,own} %b want %b", what, hst[10:7], w); end
            else $display("OK  HOST %s: last THOST {fault,sid,vid,own} %b (frames %0d)", what, hst[10:7], nth);
            if (t_host[74:72] !== w[2:0]) begin bad = bad + 1; $display("ERR WORD %s: t_host[74:72] %b want %b", what, t_host[74:72], w[2:0]); end
        end
    endtask
    initial begin
        repeat (8) @(posedge clk); rst_n = 1; rst_f = 1;
        repeat (WAIT) @(posedge clk);
        if (f_lf !== 4'b0101) begin bad = bad + 1; $display("ERR lanes not live f_lf %b", f_lf); end
        if (t_host[74:72] !== 3'b000 || sid_ri || vid_ri) begin bad = bad + 1; $display("ERR idle word %b rings %b%b", t_host[74:72], sid_ri, vid_ri); end
        // phase 1: vid unit fault at stop 4 -> vid bit only
        pulse(1, 4, 2); expect_bit(73, 4 + (NS - 1 - 4), "vid stop 4");
        repeat (50) @(posedge clk);
        if (t_host[74] !== 1'b0) begin bad = bad + 1; $display("ERR SEP vid fault set the sid bit"); end
        expect_host(4'b1010, "vid stop 4");
        // phase 2: sid unit fault at stop 11 -> + sid bit
        pulse(0, 11, 1); expect_bit(74, 4 + (NS - 1 - 11), "sid stop 11");
        expect_host(4'b1110, "sid stop 11");
        // phase 3: die reset (control state) clears word, stops and rings; the host is told
        @(negedge clk); rst_f = 0; repeat (10) @(posedge clk); @(negedge clk); rst_f = 1;
        repeat (60) @(posedge clk);
        if (sid_ri || vid_ri || t_host[75:72] !== 4'b0000) begin bad = bad + 1; $display("ERR RESET rings %b%b word %b", sid_ri, vid_ri, t_host[75:72]); end
        expect_host(4'b0000, "after reset");
        // phase 4: the unit's own fault (HOSTB landing: legacy host word while HBE selected) -> own, then via the ring
        // heads sid and vid after a full ring (head flop + 16 stops + end pin flop + sticky + word)
        @(negedge clk); select_hbe = 1; f_host = 515'd1; @(posedge clk); @(negedge clk); f_host = 515'd0;
        e_cap = cyc;
        do begin @(posedge clk); #0.01; end while (t_host[72] !== 1'b1 && cyc < e_cap + 200);
        if (t_host[72] !== 1'b1) begin bad = bad + 1; $display("ERR OWN own bit never rose"); end
        else $display("OK  OWN own bit after %0d edges (HOSTB landing fault -> own sticky -> word)", cyc - e_cap);
        e_cap = cyc;
        expect_bit(74, NS + 3, "own via sid ring head");
        if (t_host[73] !== 1'b1) begin bad = bad + 1; $display("ERR OWN vid bit not set via its ring head"); end
        expect_host(4'b1111, "own + both rings");
        $display("FAULT_RING_STATS thost_frames %0d bad %0d lep_fault %0d", nth, bad, a_f);
        if (bad == 0 && !a_f) $display("PASS fault_ring: unit -> stop -> ring -> seqhost word -> THOST frame, LAT / STICK / SEP / RESET / OWN / HOST");
        else $display("FAIL fault_ring: %0d errors", bad);
        $finish;
    end
    initial begin #(0.8333 * (WAIT + 20000)); $display("FAIL fault_ring: TIMEOUT"); $finish; end
endmodule
