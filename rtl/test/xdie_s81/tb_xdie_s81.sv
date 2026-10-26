`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// TOKEN-XDIE-S81 (2026-10-18): multi-die collective co-sim of the DeepSeek ROM S81 p4l array, one TP4 group.
//
// N = 4 dies = the production TP group (TP4: a_allgather / router_allgather / rows / topk / cand / Engram rows
// all-gathers, out / combine all-reduce = reduce-scatter + all-gather, argmax merge, stage hop).  Each die = its 4
// cross-die endpoints (end slices s_0S, s_7S, s_0N, s_7N of the p4l plan; xdie_s81_ep = current RTL ring stop + lep +
// 2 lane tiles + 2 PHY macros per the plan: S ports lane 0 ot_pdie_ucie / lane 1 ot_pdie_serdes, N ports 2 x serdes).
// Fabric (MODELLED, the only off-chip part): one-tier multi-plane switch, static circuits, one switch chip per crossing:
//   die d ES (s_7S) <-> die d+1 WS (s_0S)     (d -> d+1 and d+1 -> d)
//   die d EN (s_7N) <-> die d+2 WN (s_0N)     (d -> d+2 and d+2 -> d)
// so every die reaches its 3 TP peers in ONE crossing.  Every lane direction = xdie_s81_chan, D cycles; with the PHY
// macros' own PMA model latency the modelled off-die leg is 2 x PLAT + D = 453 cycles = 377.5 ns (PHY/FEC 100 +
// Tomahawk-Ultra 250 + 2 x 3 m twinax 27.6 = 377.6 ns, tools/dshbm_1m_coll.py).  The KP4 FEC digital and the link layer
// are RTL and are measured ON TOP of the 377.6 ns budget (which already contains FEC): conservative.
//
// Stimulus = the compiler's static calendar (tools/xdie_s81/gen_golden.py -> stim.hex): each line
//   {deadline 32, issue cycle 32, dp 8 (die * 4 + port), beat 1104}
// is driven on that endpoint's INWARD line input at exactly its issue cycle (no ready exists on the line: static).  The
// beat is a line beat (bit 0 valid, kind CTL, hops 3, slice mask 0: no slice acts on it; forwarding is kind-blind) whose
// payload [1087:64] carries 128 B of the golden collective data, [1095:1088] the collective instance id.
// Checks (verdict "PASS xdie_s81" / "FAIL xdie_s81: <why>"):
//   exact     every beat lands once, in order, at the circuit peer's inward output, bit-exact (hops - 2)
//   static    land cycle <= the compiled deadline (when the calendar gives one, deadline != 0); a die's AG phase of an
//             all-reduce is issued at its compiled cycle whatever happened on the link
//   faults    no lep / lane / PHY fault, all lanes live; flow control exists only inside the lane tiles (off-die)
// One "LAND" line per beat: LAND <coll> <src dp> <dst dp> <k> <issue> <land> <deadline> (tools/xdie_s81/record.py).
// ---------------------------------------------------------------------------------------------------------------------
module tb_xdie_s81 #(
    parameter integer D_CH = 445,
    parameter integer CHB = 0,          // lane tile ch_b strap: 0 = UCIe timeout basis (p4l plan strap), 1 = board basis
    parameter integer LOVR = 0, parameter integer CHB_OVR = 400, parameter integer CRED_OVR = 512, parameter integer SEQW_OVR = 10,
    parameter integer LSRAM = 1,
    parameter integer DMUT = 0,
    parameter integer LATE_MUT = 0,     // bench schedule mutant: extra channel cycles on die 1 ES lane 1 (late landing)
    parameter integer ERRP = 0,         // pad bit errors on every SerDes lane: one bit every ERRP cycles (0 = none)
    parameter integer FORCE_UCIE = 0,   // diagnostic only: every lane ot_pdie_ucie (no KP4)
    parameter integer NSMAX = 16384,
    parameter integer MAXCYC = 400000
);
    localparam integer ND = 4, NP = 4, NE = ND * NP;
    reg clk = 0; always #0.4167 clk = ~clk;
    reg rst_n = 0;
    integer cyc = 0;
    always @(posedge clk) cyc <= cyc + 1;

    // ---- endpoints
    reg  [1103:0] ri [0:NE-1];
    wire [1103:0] ro [0:NE-1];
    wire [543:0]  ptx0 [0:NE-1]; wire [543:0] ptx1 [0:NE-1];
    wire [543:0]  prx0 [0:NE-1]; wire [543:0] prx1 [0:NE-1];
    wire [NE-1:0] flt; wire [2*NE-1:0] lv;
    // port p: 0 = WS (s_0S, lepw), 1 = ES (s_7S, lepe_nh), 2 = WN (s_0N, lepw), 3 = EN (s_7N, lepe + host plane)
    function automatic integer peer(input integer e);
        integer d, p;
        begin
            d = e / NP; p = e % NP;
            case (p)
                0: peer = ((d + ND - 1) % ND) * NP + 1;
                1: peer = ((d + 1) % ND) * NP + 0;
                2: peer = ((d + 2) % ND) * NP + 3;
                default: peer = ((d + 2) % ND) * NP + 2;
            endcase
        end
    endfunction
    genvar ge;
    generate for (ge = 0; ge < NE; ge = ge + 1) begin : g_e
        localparam integer P = ge % NP;
        localparam integer PR = (P == 0) ? (((ge / NP) + ND - 1) % ND) * NP + 1 :
                                (P == 1) ? (((ge / NP) + 1) % ND) * NP + 0 :
                                (P == 2) ? (((ge / NP) + 2) % ND) * NP + 3 : (((ge / NP) + 2) % ND) * NP + 2;
        xdie_s81_ep #(.SIDE(P % 2), .HOST(P == 3 ? 1 : 0), .PHY0((P < 2 || FORCE_UCIE != 0) ? 0 : 1), .PHY1(FORCE_UCIE != 0 ? 0 : 1), .DMUT(DMUT),
            .LOVR(LOVR), .CHB_OVR(CHB_OVR), .CRED_OVR(CRED_OVR), .SEQW_OVR(SEQW_OVR), .LSRAM(LSRAM)) u_ep (
            .clk(clk), .rst_n(rst_n), .sid(4'((P % 2 ? 14 : 0) + (P >= 2 ? 1 : 0))), .ch_b(CHB[0]),
            .ri_n(ri[ge]), .ro_n(ro[ge]), .pma_tx0(ptx0[ge]), .pma_tx1(ptx1[ge]), .pma_rx0(prx0[ge]), .pma_rx1(prx1[ge]),
            .fault(flt[ge]), .live(lv[2*ge +: 2]));
        // link-layer statistics (hierarchical reads of ot_s81ph_link_ep's counters; no logic is added to the DUT)
        wire [31:0] to0, to1, rt0, rt1;
        if (LOVR != 0) begin : g_sl
            assign to0 = u_ep.g_lo.u_ln0.u_ep.st_timeouts; assign to1 = u_ep.g_lo.u_ln1.u_ep.st_timeouts;
            assign rt0 = u_ep.g_lo.u_ln0.u_ep.st_retx_flits; assign rt1 = u_ep.g_lo.u_ln1.u_ep.st_retx_flits;
        end else if (P % 2 == 0) begin : g_sw
            assign to0 = u_ep.g_lw.u_ln0.u.u_ep.st_timeouts; assign to1 = u_ep.g_lw.u_ln1.u.u_ep.st_timeouts;
            assign rt0 = u_ep.g_lw.u_ln0.u.u_ep.st_retx_flits; assign rt1 = u_ep.g_lw.u_ln1.u.u_ep.st_retx_flits;
        end else begin : g_se
            assign to0 = u_ep.g_le.u_ln0.u.u_ep.st_timeouts; assign to1 = u_ep.g_le.u_ln1.u.u_ep.st_timeouts;
            assign rt0 = u_ep.g_le.u_ln0.u.u_ep.st_retx_flits; assign rt1 = u_ep.g_le.u_ln1.u.u_ep.st_retx_flits;
        end
        // receive channels: from the circuit peer's pads (lane k -> lane k)
        xdie_s81_chan #(.W(544), .D(D_CH), .ERRP((P >= 2 && FORCE_UCIE == 0) ? ERRP : 0)) u_c0 (.clk(clk), .d(ptx0[PR]), .q(prx0[ge]));
        xdie_s81_chan #(.W(544), .D(D_CH + ((LATE_MUT != 0 && PR == 1 * NP + 1) ? LATE_MUT : 0)), .ERRP(FORCE_UCIE == 0 ? ERRP : 0)) u_c1 (.clk(clk), .d(ptx1[PR]), .q(prx1[ge]));
    end endgenerate

    // ---- static calendar
    reg [1175:0] stim [0:NSMAX-1];
    integer ns = 0, si = 0;
    reg [1103:0] sent [0:NE-1][0:4095];
    integer      s_is [0:NE-1][0:4095];
    integer      s_dl [0:NE-1][0:4095];
    integer      nsent [0:NE-1];
    integer      nrecv [0:NE-1];
    integer bad = 0, late = 0, extra = 0, nland = 0, maxlate = -1000000, e2, k2;
    reg go = 0;
    initial begin
        for (e2 = 0; e2 < NE; e2 = e2 + 1) begin nsent[e2] = 0; nrecv[e2] = 0; ri[e2] = 0; end
        if (!$value$plusargs("NS=%d", ns)) ns = 0;
        $readmemh("stim.hex", stim);
        repeat (8) @(posedge clk); rst_n = 1;
        go = 1;
    end
    // drive on the negedge before the issue cycle's posedge (as the slice benches): beat at cycle c is sampled at edge c
    integer e3; reg [1175:0] w;
    always @(negedge clk) if (go) begin
        for (e3 = 0; e3 < NE; e3 = e3 + 1) ri[e3] = 1104'd0;
        while (si < ns && stim[si][1143:1112] == cyc + 1) begin
            w = stim[si];
            e3 = w[1111:1104];
            if (ri[e3][0]) begin bad = bad + 1; $display("FAIL xdie_s81: calendar issues two beats on dp %0d at cycle %0d", e3, cyc + 1); end
            ri[e3] = w[1103:0];
            sent[e3][nsent[e3]] = w[1103:0]; s_is[e3][nsent[e3]] = cyc + 1; s_dl[e3][nsent[e3]] = w[1175:1144];
            nsent[e3] = nsent[e3] + 1;
            si = si + 1;
        end
    end
    // ---- landing checks
    function automatic [1103:0] hopsm2(input [1103:0] b); begin hopsm2 = b; hopsm2[8:4] = b[8:4] - 5'd2; end endfunction
    integer e, s, k;
    always @(posedge clk) if (go) begin
        for (e = 0; e < NE; e = e + 1) if (ro[e][0]) begin
            s = peer(e); k = nrecv[e];
            if (k >= nsent[s]) begin
                extra = extra + 1;
                if (extra < 6) $display("FAIL xdie_s81: unexpected beat at dp %0d cycle %0d", e, cyc);
            end else begin
                if (ro[e] !== hopsm2(sent[s][k])) begin
                    bad = bad + 1;
                    if (bad < 6) $display("MISMATCH dst %0d src %0d k %0d cyc %0d got %h exp %h", e, s, k, cyc, ro[e][1103:1040], sent[s][k][1103:1040]);
                end
                if (s_dl[s][k] != 0) begin
                    if (cyc - s_dl[s][k] > maxlate) maxlate = cyc - s_dl[s][k];
                    if (cyc > s_dl[s][k]) begin
                        late = late + 1;
                        if (late < 6) $display("LATE dst %0d src %0d k %0d land %0d deadline %0d", e, s, k, cyc, s_dl[s][k]);
                    end
                end
                $display("LAND %0d %0d %0d %0d %0d %0d %0d", ro[e][1095:1088], s, e, k, s_is[s][k], cyc, s_dl[s][k]);
            end
            nrecv[e] = nrecv[e] + 1; nland = nland + 1;
        end
    end
    // ---- end of run
    integer ff, lvc, tot;
    reg [NE-1:0] fseen = 0;
    always @(posedge clk) fseen <= fseen | flt;
    initial begin
        wait (go);
        while (nland < ns && cyc < MAXCYC) @(posedge clk);
        repeat (2000) @(posedge clk);
        lvc = 0; for (e2 = 0; e2 < 2 * NE; e2 = e2 + 1) lvc = lvc + lv[e2];
        $display("XDIE_LINK timeouts %0d retx_flits %0d (all 32 lanes; go-back-N ACK timeouts and replayed flits)",
            g_e[0].to0+g_e[0].to1+g_e[1].to0+g_e[1].to1+g_e[2].to0+g_e[2].to1+g_e[3].to0+g_e[3].to1+g_e[4].to0+g_e[4].to1+g_e[5].to0+g_e[5].to1+g_e[6].to0+g_e[6].to1+g_e[7].to0+g_e[7].to1
           +g_e[8].to0+g_e[8].to1+g_e[9].to0+g_e[9].to1+g_e[10].to0+g_e[10].to1+g_e[11].to0+g_e[11].to1+g_e[12].to0+g_e[12].to1+g_e[13].to0+g_e[13].to1+g_e[14].to0+g_e[14].to1+g_e[15].to0+g_e[15].to1,
            g_e[0].rt0+g_e[0].rt1+g_e[1].rt0+g_e[1].rt1+g_e[2].rt0+g_e[2].rt1+g_e[3].rt0+g_e[3].rt1+g_e[4].rt0+g_e[4].rt1+g_e[5].rt0+g_e[5].rt1+g_e[6].rt0+g_e[6].rt1+g_e[7].rt0+g_e[7].rt1
           +g_e[8].rt0+g_e[8].rt1+g_e[9].rt0+g_e[9].rt1+g_e[10].rt0+g_e[10].rt1+g_e[11].rt0+g_e[11].rt1+g_e[12].rt0+g_e[12].rt1+g_e[13].rt0+g_e[13].rt1+g_e[14].rt0+g_e[14].rt1+g_e[15].rt0+g_e[15].rt1);
        $display("XDIE_STATS beats %0d landed %0d mismatches %0d late %0d maxlate %0d extra %0d faults %b live %0d/%0d last_cycle %0d",
            ns, nland, bad, late, maxlate, extra, fseen, lvc, 2 * NE, cyc);
        if (ns > 0 && nland == ns && bad == 0 && late == 0 && extra == 0 && fseen == 0 && lvc == 2 * NE)
            $display("PASS xdie_s81: %0d beats of the TP4 calendar landed bit-exact, in order, by their compiled deadlines, no fault", ns);
        else
            $display("FAIL xdie_s81: landed %0d/%0d mismatches %0d late %0d extra %0d faults %b live %0d/%0d", nland, ns, bad, late, extra, fseen, lvc, 2 * NE);
        $finish;
    end
endmodule
