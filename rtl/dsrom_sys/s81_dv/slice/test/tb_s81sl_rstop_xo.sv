`timescale 1ns/1ps
// S81-RTLGAP/RG-HEAD (TOK.DS.BENCH.4.1, 2026-10-21): head XB egress of ot_s81sl_rstop_xo.
// (The six rstop_sid phases run on ot_s81sl_rstop_xo too: tools/s81_slice/rstop_xo_bench.sh builds tb_s81sl_rstop_sid
// against the variant.)  This bench:
//   A  16 real stops, one per strap (same stimulus to all), the egress rules:
//      E1 own flagged XB beat: sid 1 also sends it on ro_w with hops 1 / src 1 / flag + idx + payload kept; every other
//         stop exactly the rstop line injection (E hops 7 - col, W hops col, zero-hop side silent)
//      E2 own UNflagged XB beat: no stop sends anything W beyond the rstop rule (sid 1: ro_w silent)
//      E3 line XB from E with hops 1, flagged: sid 1 sends it on ro_w with hops 1, src kept; every other stop silent W
//      E4 line XB from E with hops 2, flagged: every stop forwards it W with hops 1 (the rstop rule) -- sid 1 sends ONE
//         beat (the forward), not two
//      E5 V-assembled flagged XB (4 fragments on vi): sid 1 also sends it on ro_w with hops 1 / src 1
//      E6 flagged NON-XB (XQ) own beat: no egress
//      E7 two egress sources in one cycle (own flagged + line hops 1 flagged): sticky fault at sid 1 ONLY
//   B  a 16-stop die ring (S / N tier lines of 8 stops, E/W neighbours wired ro -> ri, V rungs between column partners):
//      R1 80 flagged beats (every slice x 5 leaves, idx 5 sid + k, unique payload), one every 40 edges: s_0N ro_w
//         carries each of the 80 exactly once (hops 1, flag, idx, payload, src = the injecting N-line stop); NO beat
//         on the other outward ports (s_0S ro_w, s_7S ro_e, s_7N ro_e); every stop's gather delivers all 80 (unchanged
//         on-die all-gather); 0 faults
//      R2 the same 80 beats unflagged: no egress at all; every stop still gathers all 80
// Verdict line: PASS rstop_xo <checks> / FAIL rstop_xo <bad> of <checks>.
// Mutants (must FAIL): OT_S81SL_RSTOP_MUT_XOOFF, OT_S81SL_RSTOP_MUT_XOALL, OT_S81SL_RSTOP_MUT_XONOFLAG.
module tb_s81sl_rstop_xo;
    localparam integer W = 1104, V = 276;
    localparam [2:0] K_XQ = 3'd1, K_XB = 3'd2;
    reg clk = 1'b0; always #0.5 clk = ~clk;
    reg rst_n = 1'b0;
    integer bad = 0, nchk = 0, s, i, j, c, t;
    task automatic chk(input integer cond, input [8*64-1:0] what);
        begin nchk = nchk + 1; if (!cond) begin bad = bad + 1; if (bad < 40) $display("MISMATCH %0s", what); end end
    endtask
    function automatic [W-1:0] xb_beat(input integer src, input integer idx, input integer flag, input integer seed,
                                      input [2:0] kind);
        reg [W-1:0] b; integer l;
        begin
            b = {W{1'b0}}; b[0] = 1'b1; b[3:1] = kind; b[8:4] = 5'd1; b[12:9] = src[3:0]; b[19:13] = idx[6:0];
            b[20] = flag[0];
            for (l = 0; l < 64; l = l + 1) b[21 + 16 * l +: 16] = 16'(seed * 131 + l * 7 + 16'h3f00);
            xb_beat = b;
        end
    endfunction
    // ================================================================= A: 16 straps, shared stimulus
    reg [W-1:0] ri_w = 0, ri_e = 0, ci_b = 0; reg [V-1:0] vi = 0; reg [4:0] xf_v = 0, xf_s = 0; reg [5*V-1:0] xf = 0;
    reg [2:0] ci_dir = 0;
    wire [W-1:0] ro_e [0:15]; wire [W-1:0] ro_w [0:15]; wire [15:0] flt;
    genvar g;
    generate for (g = 0; g < 16; g = g + 1) begin : g_a
        ot_s81sl_rstop_xo u (.clk(clk), .rst_n(rst_n), .sid(g[3:0]), .ri_w(ri_w), .ri_e(ri_e), .ro_e(ro_e[g]), .ro_w(ro_w[g]),
            .vi(vi), .vo(), .xf_v(xf_v), .xf_s(xf_s), .xf(xf), .nx_wi(), .nx_ei(), .nx_eo(173'd0), .nx_wo(173'd0),
            .g_v(), .g_fam(), .g_idx(), .g_d(), .dl_ev(), .dl_e(), .dl_wv(), .dl_w(), .dl_vv(), .dl_vb(),
            .ci_dir(ci_dir), .ci_b(ci_b), .fault(flt[g]));
    end endgenerate
    integer ne [0:15], nw [0:15]; reg [W-1:0] fe_b [0:15], fw_b [0:15];
    task automatic clr; begin for (s = 0; s < 16; s = s + 1) begin ne[s] = 0; nw[s] = 0; end end endtask
    always @(posedge clk) if (rst_n) for (s = 0; s < 16; s = s + 1) begin
        if (ro_e[s][0]) begin if (ne[s] == 0) fe_b[s] = ro_e[s]; ne[s] = ne[s] + 1; end
        if (ro_w[s][0]) begin if (nw[s] == 0) fw_b[s] = ro_w[s]; nw[s] = nw[s] + 1; end
    end
    task automatic idle(input integer n); begin repeat (n) @(negedge clk); end endtask
    task automatic own_beat(input [W-1:0] b);   // leaf 0's four fragments (fragment 0 carries the header)
        begin
            @(negedge clk); xf_v = 5'b00001; xf_s = 5'b00001; xf = 0; xf[V-1:0] = b[V-1:0];
            @(negedge clk); xf_s = 0; xf[V-1:0] = b[2*V-1:V];
            @(negedge clk); xf[V-1:0] = b[3*V-1:2*V];
            @(negedge clk); xf[V-1:0] = b[4*V-1:3*V];
            @(negedge clk); xf_v = 0; xf = 0;
        end
    endtask
    function automatic integer same_body(input [W-1:0] a, input [W-1:0] b);   // all but hops [8:4] and src [12:9]
        same_body = (a[3:0] == b[3:0]) && (a[W-1:13] == b[W-1:13]);
    endfunction
    // ================================================================= B: the die ring
    reg [4:0] rxf_v [0:15]; reg [4:0] rxf_s [0:15]; reg [5*V-1:0] rxf [0:15];
    wire [W-1:0] r_ro_e [0:15]; wire [W-1:0] r_ro_w [0:15]; wire [V-1:0] r_vo [0:15]; wire [15:0] r_flt;
    wire [2:0] r_gv [0:15]; wire [2:0] r_gf [0:15]; wire [20:0] r_gi [0:15]; wire [3071:0] r_gd [0:15];
    generate for (g = 0; g < 16; g = g + 1) begin : g_r
        localparam integer C = g / 2, T = g % 2;
        wire [W-1:0] riw, rie; wire [V-1:0] rvi;
        if (C == 0) begin : g_w0 assign riw = {W{1'b0}}; end else begin : g_w assign riw = r_ro_e[g - 2]; end
        if (C == 7) begin : g_e0 assign rie = {W{1'b0}}; end else begin : g_e assign rie = r_ro_w[g + 2]; end
        if (T == 1) begin : g_vn assign rvi = r_vo[g - 1]; end else begin : g_vs assign rvi = r_vo[g + 1]; end
        ot_s81sl_rstop_xo u (.clk(clk), .rst_n(rst_n), .sid(g[3:0]), .ri_w(riw), .ri_e(rie), .ro_e(r_ro_e[g]),
            .ro_w(r_ro_w[g]), .vi(rvi), .vo(r_vo[g]), .xf_v(rxf_v[g]), .xf_s(rxf_s[g]), .xf(rxf[g]), .nx_wi(), .nx_ei(),
            .nx_eo(173'd0), .nx_wo(173'd0), .g_v(r_gv[g]), .g_fam(r_gf[g]), .g_idx(r_gi[g]), .g_d(r_gd[g]),
            .dl_ev(), .dl_e(), .dl_wv(), .dl_w(), .dl_vv(), .dl_vb(), .ci_dir(3'd0), .ci_b({W{1'b0}}), .fault(r_flt[g]));
    end endgenerate
    // gather / egress monitors
    integer gcnt [0:15]; reg [79:0] gseen [0:15]; integer gbad = 0;
    integer eg_n = 0, eg_bad = 0, out_other = 0; reg [79:0] eg_seen = 0; integer flagged = 1;
    reg [W-1:0] want [0:79]; integer want_src [0:79];
    integer m, ix;
    always @(posedge clk) if (rst_n) begin
        for (s = 0; s < 16; s = s + 1)
            for (m = 0; m < 3; m = m + 1) if (r_gv[s][m]) begin
                ix = r_gi[s][7 * m +: 7];
                if (!r_gf[s][m] || ix > 79 || gseen[s][ix] || r_gd[s][1024 * m +: 1024] !== want[ix][21 +: 1024]) gbad = gbad + 1;
                else begin gseen[s][ix] = 1'b1; gcnt[s] = gcnt[s] + 1; end
            end
        if (r_ro_w[1][0]) begin
            ix = r_ro_w[1][19:13];
            eg_n = eg_n + 1;
            if (ix > 79 || eg_seen[ix] || r_ro_w[1][8:4] != 5'd1 || r_ro_w[1][3:1] != K_XB || !r_ro_w[1][20] ||
                r_ro_w[1][12:9] != want_src[ix][3:0] || r_ro_w[1][W-1:21] !== want[ix][W-1:21]) begin
                eg_bad = eg_bad + 1; if (eg_bad < 8) $display("EGRESS_BAD idx %0d hops %0d src %0d (want %0d)", ix,
                                                               r_ro_w[1][8:4], r_ro_w[1][12:9], want_src[ix]);
            end else eg_seen[ix] = 1'b1;
        end
        if (r_ro_w[0][0] || r_ro_e[14][0] || r_ro_e[15][0]) out_other = out_other + 1;
    end
    task automatic ring_beat(input integer sl, input integer k, input [W-1:0] b);
        begin
            @(negedge clk); rxf_v[sl] = 5'd1 << k; rxf_s[sl] = 5'd1 << k; rxf[sl] = 0; rxf[sl][k * V +: V] = b[V-1:0];
            @(negedge clk); rxf_s[sl] = 0; rxf[sl][k * V +: V] = b[2*V-1:V];
            @(negedge clk); rxf[sl][k * V +: V] = b[3*V-1:2*V];
            @(negedge clk); rxf[sl][k * V +: V] = b[4*V-1:3*V];
            @(negedge clk); rxf_v[sl] = 0; rxf[sl] = 0;
        end
    endtask
    task automatic ring_pass(input integer fl);
        integer sl, k;
        begin
            for (sl = 0; sl < 16; sl = sl + 1) begin gcnt[sl] = 0; gseen[sl] = 0; end
            eg_n = 0; eg_bad = 0; eg_seen = 0; out_other = 0; gbad = 0;
            for (sl = 0; sl < 16; sl = sl + 1) for (k = 0; k < 5; k = k + 1) begin
                want[5 * sl + k] = xb_beat(sl, 5 * sl + k, fl, 1000 * fl + 5 * sl + k, K_XB);
                // the N-line stop that injects / delivers it at s_0N: an N-tier slice itself, an S-tier slice's V partner
                want_src[5 * sl + k] = (sl % 2) ? sl : sl + 1;
            end
            for (sl = 0; sl < 16; sl = sl + 1) for (k = 0; k < 5; k = k + 1) begin
                ring_beat(sl, k, want[5 * sl + k]); idle(35);
            end
            idle(60);
        end
    endtask
    initial begin
        for (s = 0; s < 16; s = s + 1) begin rxf_v[s] = 0; rxf_s[s] = 0; rxf[s] = 0; end
        idle(4); rst_n = 1'b1; idle(4);
        // ---------------- E1 own flagged XB
        clr; own_beat(xb_beat(0, 37, 1, 5, K_XB)); idle(8);
        for (s = 0; s < 16; s = s + 1) begin
            c = s / 2;
            if (s == 1) chk(nw[s] == 1 && fw_b[s][8:4] == 1 && fw_b[s][12:9] == 1 && same_body(fw_b[s], xb_beat(0, 37, 1, 5, K_XB)),
                            "E1 sid 1 egress (hops 1, src 1, body)");
            else if (c == 0) chk(nw[s] == 0, "E1 col 0 W silent");
            else chk(nw[s] == 1 && fw_b[s][8:4] == c && fw_b[s][12:9] == s, "E1 W rule");
            if (c == 7) chk(ne[s] == 0, "E1 col 7 E silent");
            else chk(ne[s] == 1 && fe_b[s][8:4] == 7 - c && same_body(fe_b[s], xb_beat(0, 37, 1, 5, K_XB)), "E1 E rule");
        end
        // ---------------- E2 own UNflagged XB
        clr; own_beat(xb_beat(0, 37, 0, 6, K_XB)); idle(8);
        for (s = 0; s < 16; s = s + 1) begin
            c = s / 2;
            if (c == 0) chk(nw[s] == 0, "E2 col 0 W silent (no egress unflagged)");
            else chk(nw[s] == 1 && fw_b[s][8:4] == c, "E2 W rule");
        end
        // ---------------- E3 line XB from E, hops 1, flagged
        clr;
        @(negedge clk); ri_e = xb_beat(9, 44, 1, 7, K_XB); ri_e[8:4] = 5'd1;
        @(negedge clk); ri_e = 0; idle(6);
        for (s = 0; s < 16; s = s + 1)
            if (s == 1) chk(nw[s] == 1 && fw_b[s][8:4] == 1 && fw_b[s][12:9] == 9 && same_body(fw_b[s], xb_beat(9, 44, 1, 7, K_XB)),
                            "E3 sid 1 egress of a delivered line beat (src kept)");
            else chk(nw[s] == 0 && ne[s] == 0, "E3 others silent");
        // ---------------- E4 line XB from E, hops 2, flagged: one forward per stop, never two
        clr;
        @(negedge clk); ri_e = xb_beat(9, 45, 1, 8, K_XB); ri_e[8:4] = 5'd2;
        @(negedge clk); ri_e = 0; idle(6);
        for (s = 0; s < 16; s = s + 1)
            chk(nw[s] == 1 && fw_b[s][8:4] == 1 && fw_b[s][12:9] == 9, "E4 forward hops 1 exactly once");
        // ---------------- E5 V-assembled flagged XB
        clr;
        begin : e5
            reg [W-1:0] b; b = xb_beat(3, 51, 1, 9, K_XB);
            @(negedge clk); vi = b[V-1:0];
            @(negedge clk); vi = b[2*V-1:V];
            @(negedge clk); vi = b[3*V-1:2*V];
            @(negedge clk); vi = b[4*V-1:3*V];
            @(negedge clk); vi = 0; idle(8);
            for (s = 0; s < 16; s = s + 1) begin
                c = s / 2;
                if (s == 1) chk(nw[s] == 1 && fw_b[s][8:4] == 1 && fw_b[s][12:9] == 1 && same_body(fw_b[s], b),
                                "E5 sid 1 egress of the V-assembled beat");
                else if (c == 0) chk(nw[s] == 0, "E5 col 0 W silent");
                else chk(nw[s] == 1 && fw_b[s][8:4] == c, "E5 W rule");
            end
        end
        // ---------------- E6 flagged XQ own beat: no egress
        clr; own_beat(xb_beat(0, 38, 1, 10, K_XQ)); idle(8);
        chk(nw[1] == 0, "E6 sid 1: flagged XQ does not egress");
        chk(flt == 16'd0, "E1-E6 no fault");
        // ---------------- B: the die ring
        ring_pass(1);
        for (s = 0; s < 16; s = s + 1) chk(gcnt[s] == 80, "R1 every stop gathers all 80 flagged beats");
        chk(gbad == 0, "R1 gather words exact");
        chk(eg_n == 80 && eg_bad == 0 && &eg_seen, "R1 s_0N ro_w: each of the 80 beats exactly once, exact");
        chk(out_other == 0, "R1 no beat on s_0S ro_w / s_7S ro_e / s_7N ro_e");
        chk(r_flt == 16'd0, "R1 ring: no fault");
        $display("RSTOP_XO R1 egress %0d (bad %0d) gather min %0d other_out %0d", eg_n, eg_bad, gcnt[0], out_other);
        ring_pass(0);
        for (s = 0; s < 16; s = s + 1) chk(gcnt[s] == 80, "R2 every stop gathers all 80 unflagged beats");
        chk(gbad == 0, "R2 gather words exact");
        chk(eg_n == 0 && out_other == 0, "R2 unflagged: no egress / no outward beat");
        chk(r_flt == 16'd0, "R2 ring: no fault");
        $display("RSTOP_XO R2 egress %0d gather min %0d other_out %0d", eg_n, gcnt[0], out_other);
        // ---------------- E7 collision (last: the fault is sticky)
        fork
            own_beat(xb_beat(0, 39, 1, 11, K_XB));
            begin idle(5); ri_e = xb_beat(9, 46, 1, 12, K_XB); ri_e[8:4] = 5'd1; @(negedge clk); ri_e = 0; end
        join
        idle(6);
        chk(flt == 16'h0002, "E7 two egress sources in one cycle: sticky fault at sid 1 only");
        if (flt != 16'h0002) $display("E7 fault vector %h", flt);
        if (bad == 0) $display("PASS rstop_xo %0d checks", nchk);
        else $display("FAIL rstop_xo %0d of %0d checks", bad, nchk);
        $finish;
    end
endmodule
