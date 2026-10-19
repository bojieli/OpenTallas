`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// XDIE-S81-2 (2026-10-19): S81 multi-die collective co-sim on the CURRENT die RTL (G8R2 bind p4m, 0e6b9b710) with the
// die's lane legs, plus the MULTI-USER case of the MU-S81 calendar (copy A / B, user-tagged stage hop windows).
// Successor of rtl/test/xdie_s81/tb_xdie_s81.sv (gate_g5, 7e61eeb2e): same 4-die TP4 group, same fabric model, same
// stimulus format and LAND line (tools/xdie_s81_2/record.py reads both).
//   N = 4 dies x 4 end-slice endpoints (xdie_s81_2_ep: rstop + lep + lane tiles + lane legs + PHY macros).
//   Fabric (MODELLED, the only off-chip part): one-tier multi-plane switch, static circuits, one switch chip a crossing:
//     pair A (lanes 0/1, the TP4 circuits):  d.ES <-> (d+1).WS,  d.EN <-> (d+2).WN
//     pair B (lanes 2/3, MU only = the copy-B static circuit, a different peer die):  d.WS <-> (d+1).ES,  d.WN <-> (d+1).EN
//   each lane direction a fixed delay D_CH so that 2 x PMA model + D = 453 cycles = 377.5 ns (377.6 ns budget).
// Calendar (static, compiler-issued; tools/xdie_s81_2/gen_golden.py): stim.hex {deadline 32, issue 32, dp 8, beat 1104};
// mu.hex {cycle 32, dp 8, 6'b0, mu_c 34} = the MU TX tag-window commands (die: dsdv_seq_host_mu -> lep mu_c).
// Bench-only mirror bits of an MU beat (never read by the DUT; inside the beat payload area [63:13]): [13] tagged,
// [23:14] user, [44:24] pos, [45] copy B.  Checks:
//   every beat lands bit-exact (hops - 2: two ring stops) at the endpoint of its circuit (pair from [45]), in order per
//   (source, pair), by its compiled deadline; the lep's mu_rt carries {1, user, pos} with every tagged beat and 0 with
//   every other beat (tags stripped from ri: the full-beat compare); no lep / lane / PHY / landing fault; all lanes live.
// Run-time plusargs (one build serves several runs): +NS= +NM= +ERRP=n (pad bit errors every n cycles on every lane)
// +LATE=n (die 1 ES lane 1 n cycles late: schedule mutant) +CHB=0|1 (lane tile ch_b strap; die straps 1).
// ---------------------------------------------------------------------------------------------------------------------
module tb_xdie_s81_2 #(
    parameter integer D_CH = 445,
    parameter integer MU = 0,
    parameter integer LEG = 1,
    parameter integer DMUT = 0,
    parameter integer NSMAX = 32768,
    parameter integer NMMAX = 1024,
    parameter integer QD = 4096,
    parameter integer MAXCYC = 400000
);
    localparam integer ND = 4, NP = 4, NE = ND * NP, NL = (MU != 0) ? 4 : 2;
    reg clk = 0; always #0.4167 clk = ~clk;
    reg rst_n = 0;
    integer cyc = 0;
    always @(posedge clk) cyc <= cyc + 1;
    integer errp = 0, latec = 0, chb = 1;

    // ---- circuits
    function automatic integer peer_a(input integer e);
        integer d, p;
        begin
            d = e / NP; p = e % NP;
            case (p)
                0: peer_a = ((d + ND - 1) % ND) * NP + 1;
                1: peer_a = ((d + 1) % ND) * NP + 0;
                2: peer_a = ((d + 2) % ND) * NP + 3;
                default: peer_a = ((d + 2) % ND) * NP + 2;
            endcase
        end
    endfunction
    function automatic integer peer_b(input integer e);
        integer d, p;
        begin
            d = e / NP; p = e % NP;
            case (p)
                0: peer_b = ((d + 1) % ND) * NP + 1;          // d.WS <-> (d+1).ES
                1: peer_b = ((d + ND - 1) % ND) * NP + 0;
                2: peer_b = ((d + 1) % ND) * NP + 3;          // d.WN <-> (d+1).EN
                default: peer_b = ((d + ND - 1) % ND) * NP + 2;
            endcase
        end
    endfunction

    // ---- endpoints
    reg  [1103:0] ri [0:NE-1];
    wire [1103:0] ro [0:NE-1];
    wire [1103:0] lri [0:NE-1];
    wire [31:0]   mrt [0:NE-1];
    reg  [33:0]   muc [0:NE-1];
    wire [4*544-1:0] ptx [0:NE-1]; wire [4*544-1:0] prx [0:NE-1];
    wire [NE-1:0] flt; wire [4*NE-1:0] lv;
    wire [31:0] to_l [0:4*NE-1]; wire [31:0] rt_l [0:4*NE-1];
    genvar ge, gl;
    generate for (ge = 0; ge < NE; ge = ge + 1) begin : g_e
        localparam integer P = ge % NP;
        localparam integer DA = (P == 0) ? (((ge / NP) + ND - 1) % ND) * NP + 1 :
                                (P == 1) ? (((ge / NP) + 1) % ND) * NP + 0 :
                                (P == 2) ? (((ge / NP) + 2) % ND) * NP + 3 : (((ge / NP) + 2) % ND) * NP + 2;
        localparam integer DB = (P == 0) ? (((ge / NP) + 1) % ND) * NP + 1 :
                                (P == 1) ? (((ge / NP) + ND - 1) % ND) * NP + 0 :
                                (P == 2) ? (((ge / NP) + 1) % ND) * NP + 3 : (((ge / NP) + ND - 1) % ND) * NP + 2;
        xdie_s81_2_ep #(.SIDE(P % 2), .HOST((P == 3 && MU == 0) ? 1 : 0), .MU(MU), .LEG(LEG), .DMUT(DMUT)) u_ep (
            .clk(clk), .rst_n(rst_n), .sid(4'((P % 2 ? 14 : 0) + (P >= 2 ? 1 : 0))), .ch_b(chb[0]),
            .ri_n(ri[ge]), .ro_n(ro[ge]), .pma_tx(ptx[ge]), .pma_rx(prx[ge]), .mu_c(muc[ge]), .mu_rt(mrt[ge]),
            .lep_ri(lri[ge]), .fault(flt[ge]), .live(lv[4*ge +: 4]));
        for (gl = 0; gl < 4; gl = gl + 1) begin : g_c
            localparam integer SRC = (gl < 2) ? DA : DB;
            if (gl < NL) begin : g_on
                // receive channel: from the circuit peer's pads (lane k -> lane k); LATE on die 1 ES lane 1 (as gate_g5)
                xdie2_chan #(.W(544), .D(D_CH)) u_ch (.clk(clk), .errp(errp), .extra((SRC == 1 * NP + 1 && gl == 1) ? latec : 0),
                    .d(ptx[SRC][544*gl +: 544]), .q(prx[ge][544*gl +: 544]));
                // link-layer statistics (hierarchical reads of ot_s81ph_link_ep's counters; no logic added to the DUT)
                if (P % 2 == 0) begin : g_sw
                    assign to_l[4*ge+gl] = u_ep.g_l[gl].g_w.u_ln.u.u_ep.st_timeouts;
                    assign rt_l[4*ge+gl] = u_ep.g_l[gl].g_w.u_ln.u.u_ep.st_retx_flits;
                end else begin : g_se
                    assign to_l[4*ge+gl] = u_ep.g_l[gl].g_e.u_ln.u.u_ep.st_timeouts;
                    assign rt_l[4*ge+gl] = u_ep.g_l[gl].g_e.u_ln.u.u_ep.st_retx_flits;
                end
            end else begin : g_off
                assign prx[ge][544*gl +: 544] = '0; assign to_l[4*ge+gl] = 0; assign rt_l[4*ge+gl] = 0;
            end
        end
    end endgenerate

    // ---- static calendar
    reg [1175:0] stim [0:NSMAX-1];
    reg [79:0]   mcmd [0:NMMAX-1];
    integer ns = 0, si = 0, nm = 0, mi = 0;
    reg [1103:0] sent [0:NE-1][0:1][0:QD-1];
    integer      s_is [0:NE-1][0:1][0:QD-1];
    integer      s_dl [0:NE-1][0:1][0:QD-1];
    integer      nsent [0:NE-1][0:1];
    integer      nrecv [0:NE-1][0:1];
    integer bad = 0, late = 0, extra = 0, nland = 0, maxlate = -1000000, tagbad = 0, ntag = 0, ntag_exp = 0, e2, k2;
    reg go = 0;
    initial begin
        for (e2 = 0; e2 < NE; e2 = e2 + 1) begin
            nsent[e2][0] = 0; nsent[e2][1] = 0; nrecv[e2][0] = 0; nrecv[e2][1] = 0; ri[e2] = 0; muc[e2] = 0;
        end
        if (!$value$plusargs("NS=%d", ns)) ns = 0;
        if (!$value$plusargs("NM=%d", nm)) nm = 0;
        if (!$value$plusargs("ERRP=%d", errp)) errp = 0;
        if (!$value$plusargs("LATE=%d", latec)) latec = 0;
        if (!$value$plusargs("CHB=%d", chb)) chb = 1;
        $readmemh("stim.hex", stim);
        if (nm > 0) $readmemh("mu.hex", mcmd);
        $display("XDIE2_CFG MU %0d LEG %0d DMUT %0d NS %0d NM %0d ERRP %0d LATE %0d CHB %0d", MU, LEG, DMUT, ns, nm, errp, latec, chb);
        repeat (8) @(posedge clk); rst_n = 1;
        go = 1;
    end
    // drive on the negedge before the issue cycle's posedge: a beat / command at cycle c is sampled at edge c
    integer e3, pr; reg [1175:0] w;
    always @(negedge clk) if (go) begin
        for (e3 = 0; e3 < NE; e3 = e3 + 1) begin ri[e3] = 1104'd0; muc[e3] = 34'd0; end
        while (mi < nm && mcmd[mi][79:48] == cyc + 1) begin
            muc[mcmd[mi][47:40]] = mcmd[mi][33:0];
            mi = mi + 1;
        end
        while (si < ns && stim[si][1143:1112] == cyc + 1) begin
            w = stim[si];
            e3 = w[1111:1104];
            pr = (MU != 0 && w[45]) ? 1 : 0;
            if (ri[e3][0]) begin bad = bad + 1; $display("FAIL xdie_s81_2: calendar issues two beats on dp %0d at cycle %0d", e3, cyc + 1); end
            ri[e3] = w[1103:0];
            if (nsent[e3][pr] >= QD) begin bad = bad + 1; $display("FAIL xdie_s81_2: queue depth"); end
            else begin
                sent[e3][pr][nsent[e3][pr]] = w[1103:0]; s_is[e3][pr][nsent[e3][pr]] = cyc + 1; s_dl[e3][pr][nsent[e3][pr]] = w[1175:1144];
                nsent[e3][pr] = nsent[e3][pr] + 1;
            end
            if (w[13]) ntag_exp = ntag_exp + 1;
            si = si + 1;
        end
    end
    // ---- landing checks
    function automatic [1103:0] hopsm2(input [1103:0] b); begin hopsm2 = b; hopsm2[8:4] = b[8:4] - 5'd2; end endfunction
    integer e, s, k, p2;
    reg [31:0] texp;
    always @(posedge clk) if (go) begin
        for (e = 0; e < NE; e = e + 1) begin
            // MU tag on the lep's ri (the receiving stage's seq_host reads it with the beat)
            if (lri[e][0]) begin
                texp = lri[e][13] ? {1'b1, lri[e][23:14], lri[e][44:24]} : 32'd0;
                if (MU != 0 && mrt[e] !== texp) begin
                    tagbad = tagbad + 1;
                    if (tagbad < 6) $display("TAGBAD dp %0d cyc %0d mu_rt %h exp %h", e, cyc, mrt[e], texp);
                end
                if (MU != 0 && mrt[e][31]) ntag = ntag + 1;
            end else if (mrt[e] !== 32'd0) begin
                tagbad = tagbad + 1;
                if (tagbad < 6) $display("TAGBAD dp %0d cyc %0d mu_rt %h without a beat", e, cyc, mrt[e]);
            end
            if (ro[e][0]) begin
                s = ro[e][12:9];
                p2 = (s == peer_a(e)) ? 0 : (MU != 0 && s == peer_b(e)) ? 1 : -1;
                if (p2 < 0) begin
                    extra = extra + 1;
                    if (extra < 6) $display("FAIL xdie_s81_2: beat from dp %0d is not on a circuit of dp %0d (cycle %0d)", s, e, cyc);
                end else begin
                    k = nrecv[s][p2];
                    if (k >= nsent[s][p2]) begin
                        extra = extra + 1;
                        if (extra < 6) $display("FAIL xdie_s81_2: unexpected beat at dp %0d from %0d pair %0d cycle %0d", e, s, p2, cyc);
                    end else begin
                        if (ro[e] !== hopsm2(sent[s][p2][k])) begin
                            bad = bad + 1;
                            if (bad < 6) $display("MISMATCH dst %0d src %0d pair %0d k %0d cyc %0d got %h exp %h", e, s, p2, k, cyc,
                                                  ro[e][1103:1040], sent[s][p2][k][1103:1040]);
                        end
                        if (s_dl[s][p2][k] != 0) begin
                            if (cyc - s_dl[s][p2][k] > maxlate) maxlate = cyc - s_dl[s][p2][k];
                            if (cyc > s_dl[s][p2][k]) begin
                                late = late + 1;
                                if (late < 6) $display("LATE dst %0d src %0d pair %0d k %0d land %0d deadline %0d", e, s, p2, k, cyc, s_dl[s][p2][k]);
                            end
                        end
                        $display("LAND %0d %0d %0d %0d %0d %0d %0d", ro[e][1095:1088], s, e, k, s_is[s][p2][k], cyc, s_dl[s][p2][k]);
                    end
                    nrecv[s][p2] = nrecv[s][p2] + 1;
                end
                nland = nland + 1;
            end
        end
    end
    // ---- end of run
    integer lvc, tto, trt;
    reg [NE-1:0] fseen = 0;
    always @(posedge clk) fseen <= fseen | flt;
    initial begin
        wait (go);
        while (nland < ns && cyc < MAXCYC) @(posedge clk);
        repeat (2000) @(posedge clk);
        lvc = 0; for (e2 = 0; e2 < 4 * NE; e2 = e2 + 1) lvc = lvc + lv[e2];
        tto = 0; trt = 0; for (e2 = 0; e2 < 4 * NE; e2 = e2 + 1) begin tto = tto + to_l[e2]; trt = trt + rt_l[e2]; end
        $display("XDIE_LINK timeouts %0d retx_flits %0d (all %0d lanes; go-back-N ACK timeouts and replayed flits)", tto, trt, NL * NE);
        $display("XDIE_MU tagged_expected %0d tagged_seen %0d tag_errors %0d", ntag_exp, ntag, tagbad);
        $display("XDIE_STATS beats %0d landed %0d mismatches %0d late %0d maxlate %0d extra %0d faults %b live %0d/%0d last_cycle %0d",
            ns, nland, bad, late, maxlate, extra, fseen, lvc, NL * NE, cyc);
        if (ns > 0 && nland == ns && bad == 0 && late == 0 && extra == 0 && fseen == 0 && lvc == NL * NE && tagbad == 0 && ntag == ntag_exp)
            $display("PASS xdie_s81: %0d beats of the TP4 calendar landed bit-exact, in order, by their compiled deadlines, no fault%s",
                     ns, MU != 0 ? ", every MU tag delivered" : "");
        else
            $display("FAIL xdie_s81: landed %0d/%0d mismatches %0d late %0d extra %0d faults %b live %0d/%0d tags %0d/%0d tag_errors %0d",
                     nland, ns, bad, late, extra, fseen, lvc, NL * NE, ntag, ntag_exp, tagbad);
        $finish;
    end
endmodule
