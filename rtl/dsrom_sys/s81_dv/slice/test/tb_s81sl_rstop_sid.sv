`timescale 1ns/1ps
// S81-LBGAP G2 (2026-10-18): the slice-id convention of ot_s81sl_rstop on all 16 straps of the die.
// sid = 2 * col + tier (tier 0 = S, 1 = N): die.v u_s_<c><S|N>, svc_rs_embed.py sid(rc), ot_s81sl_xr slice mask bit,
// dv_layer_compile.py.  16 real ring stops (one per strap value) get the same stimulus; per stop the bench checks
//   P1 own beat (4 fragments of leaf 0, XQ): E line hops 7 - col, W line hops col, a zero-hop side carries nothing;
//      src = sid on both sides
//   P2 control-plane line beat with hops 0 (ci_dir E | W): line defaults E 7 - col, W col, src = sid
//   P3 xfin eo NX: on the snake end that carries the E side on V (S col 7, N col 0) it leaves on vo (kind NX); else on
//      the physical line side (S: E port, N: W port); src = sid
//   P4 xfin wo NX: V end (S col 0, N col 7) -> vo; else S: W port, N: E port
//   P5 NX arriving on V: delivered on nx_ei at the E-side V end, nx_wi at the W-side V end, nowhere else
//   P6 NX arriving from the physical W neighbour: snake-forward (nx_wi) on S, backward (nx_ei) on N; column 0 (no W
//      neighbour: that xfin side is the V end) delivers nothing from the line
// Prints RSTOP_SID <sid> col tier hE hW ... per stop.  +define+OT_S81SL_RSTOP_MUT_TIERCOL (the old {tier, col} decode)
// must FAIL.
module tb_s81sl_rstop_sid;
    localparam integer W = 1104, V = 276;
    localparam [2:0] K_CTL = 3'd0, K_XQ = 3'd1, K_NX = 3'd3;
    reg clk = 1'b0; always #0.5 clk = ~clk;
    reg rst_n = 1'b0;
    reg [W-1:0] ri_w = 0, ri_e = 0, ci_b = 0; reg [V-1:0] vi = 0; reg [4:0] xf_v = 0, xf_s = 0; reg [5*V-1:0] xf = 0;
    reg [172:0] nx_eo = 0, nx_wo = 0; reg [2:0] ci_dir = 0;
    wire [W-1:0] ro_e [0:15]; wire [W-1:0] ro_w [0:15]; wire [V-1:0] vo [0:15];
    wire [172:0] nx_wi [0:15]; wire [172:0] nx_ei [0:15]; wire [15:0] flt;
    genvar g;
    generate for (g = 0; g < 16; g = g + 1) begin : g_s
        ot_s81sl_rstop u (.clk(clk), .rst_n(rst_n), .sid(g[3:0]), .ri_w(ri_w), .ri_e(ri_e), .ro_e(ro_e[g]), .ro_w(ro_w[g]),
            .vi(vi), .vo(vo[g]), .xf_v(xf_v), .xf_s(xf_s), .xf(xf), .nx_wi(nx_wi[g]), .nx_ei(nx_ei[g]), .nx_eo(nx_eo),
            .nx_wo(nx_wo), .g_v(), .g_fam(), .g_idx(), .g_d(), .dl_ev(), .dl_e(), .dl_wv(), .dl_w(), .dl_vv(), .dl_vb(),
            .ci_dir(ci_dir), .ci_b(ci_b), .fault(flt[g]));
    end endgenerate
    // ---- per-stop window capture: first valid beat on each output during a phase
    reg se [0:15], sw [0:15], sv [0:15], swi [0:15], sei [0:15];
    reg [12:0] he [0:15], hw [0:15]; reg [3:0] ve_k [0:15];
    integer s, bad = 0, nchk = 0;
    task automatic clr; begin for (s = 0; s < 16; s = s + 1) begin se[s] = 0; sw[s] = 0; sv[s] = 0; swi[s] = 0; sei[s] = 0; end end endtask
    always @(posedge clk) if (rst_n) for (s = 0; s < 16; s = s + 1) begin
        if (ro_e[s][0] && !se[s]) begin se[s] = 1; he[s] = ro_e[s][12:0]; end
        if (ro_w[s][0] && !sw[s]) begin sw[s] = 1; hw[s] = ro_w[s][12:0]; end
        if (vo[s][0] && vo[s][3:1] == K_NX && !sv[s]) sv[s] = 1;
        if (nx_wi[s][172]) swi[s] = 1;
        if (nx_ei[s][172]) sei[s] = 1;
    end
    function automatic integer col_of(input integer i); col_of = i / 2; endfunction
    function automatic integer tier_of(input integer i); tier_of = i % 2; endfunction
    task automatic chk(input integer i, input integer cond, input [8*40-1:0] what);
        begin nchk = nchk + 1; if (!cond) begin bad = bad + 1; if (bad < 30) $display("MISMATCH sid %0d: %0s", i, what); end end
    endtask
    task automatic idle(input integer n); begin repeat (n) @(negedge clk); end endtask
    integer c, t, e;
    initial begin
        idle(4); rst_n = 1'b1; idle(4);
        // ---------------- P1 own beat: leaf 0 fragments 0..3 (fragment 0 = {.., kind XQ, valid})
        clr;
        @(negedge clk); xf_v = 5'b00001; xf_s = 5'b00001; xf = 0; xf[0] = 1'b1; xf[3:1] = K_XQ; xf[8:4] = 5'd1;
        @(negedge clk); xf_s = 0; xf = {5*V{1'b0}} | 276'h5a;
        @(negedge clk); xf = 276'h6b;
        @(negedge clk); xf = 276'h7c;
        @(negedge clk); xf_v = 0; xf = 0;
        idle(8);
        for (s = 0; s < 16; s = s + 1) begin
            c = col_of(s); t = tier_of(s);
            if (7 - c == 0) chk(s, !se[s], "P1 E zero-hop side sent");
            else chk(s, se[s] && he[s][8:4] == 7 - c && he[s][12:9] == s && he[s][3:1] == K_XQ, "P1 E hops/src");
            if (c == 0) chk(s, !sw[s], "P1 W zero-hop side sent");
            else chk(s, sw[s] && hw[s][8:4] == c && hw[s][12:9] == s && hw[s][3:1] == K_XQ, "P1 W hops/src");
            $display("RSTOP_SID %0d col %0d tier %0s own_E %0s own_W %0s", s, c, t ? "N" : "S",
                     se[s] ? $sformatf("%0d", he[s][8:4]) : "-", sw[s] ? $sformatf("%0d", hw[s][8:4]) : "-");
        end
        // ---------------- P2 control-plane line beat, hops 0 -> line defaults
        clr;
        @(negedge clk); ci_dir = 3'b011; ci_b = 0; ci_b[0] = 1'b1; ci_b[3:1] = K_CTL; ci_b[8:4] = 5'd0;
        @(negedge clk); ci_dir = 0; ci_b = 0;
        idle(6);
        for (s = 0; s < 16; s = s + 1) begin
            c = col_of(s);
            chk(s, se[s] && he[s][8:4] == 7 - c && he[s][12:9] == s, "P2 E default hops");
            chk(s, sw[s] && hw[s][8:4] == c && hw[s][12:9] == s, "P2 W default hops");
        end
        // ---------------- P3 xfin eo NX
        clr;
        @(negedge clk); nx_eo = 0; nx_eo[172] = 1'b1; nx_eo[171:168] = 4'd2; nx_eo[167:160] = 8'h3c; nx_eo[31:0] = 32'hfeed;
        @(negedge clk); nx_eo = 0;
        idle(6);
        for (s = 0; s < 16; s = s + 1) begin
            c = col_of(s); t = tier_of(s); e = t ? (c == 0) : (c == 7);
            if (e) chk(s, sv[s] && !se[s] && !sw[s], "P3 eo at V end not on V");
            else if (!t) chk(s, se[s] && !sw[s] && !sv[s] && he[s][3:1] == K_NX && he[s][12:9] == s && he[s][8:4] == 2, "P3 eo S not on E port");
            else chk(s, sw[s] && !se[s] && !sv[s] && hw[s][3:1] == K_NX && hw[s][12:9] == s && hw[s][8:4] == 2, "P3 eo N not on W port");
        end
        // ---------------- P4 xfin wo NX
        clr;
        @(negedge clk); nx_wo = 0; nx_wo[172] = 1'b1; nx_wo[171:168] = 4'd3; nx_wo[31:0] = 32'hbeef;
        @(negedge clk); nx_wo = 0;
        idle(6);
        for (s = 0; s < 16; s = s + 1) begin
            c = col_of(s); t = tier_of(s); e = t ? (c == 7) : (c == 0);
            if (e) chk(s, sv[s] && !se[s] && !sw[s], "P4 wo at V end not on V");
            else if (!t) chk(s, sw[s] && !se[s] && !sv[s] && hw[s][3:1] == K_NX && hw[s][12:9] == s, "P4 wo S not on W port");
            else chk(s, se[s] && !sw[s] && !sv[s] && he[s][3:1] == K_NX && he[s][12:9] == s, "P4 wo N not on E port");
        end
        // ---------------- P5 NX arriving on V
        clr;
        @(negedge clk); vi = 0; vi[0] = 1'b1; vi[3:1] = K_NX; vi[7:4] = 4'd1;
        @(negedge clk); vi = 0;
        idle(6);
        for (s = 0; s < 16; s = s + 1) begin
            c = col_of(s); t = tier_of(s);
            chk(s, sei[s] == (t ? (c == 0) : (c == 7)), "P5 V NX -> nx_ei");
            chk(s, swi[s] == (t ? (c == 7) : (c == 0)), "P5 V NX -> nx_wi");
        end
        // ---------------- P6 NX from the physical W neighbour (hops 1)
        clr;
        @(negedge clk); ri_w = 0; ri_w[0] = 1'b1; ri_w[3:1] = K_NX; ri_w[8:4] = 5'd1;
        @(negedge clk); ri_w = 0;
        idle(6);
        for (s = 0; s < 16; s = s + 1) begin
            c = col_of(s); t = tier_of(s);
            chk(s, swi[s] == (!t && c != 0) && sei[s] == (t && c != 0), "P6 line-W NX side");
        end
        idle(2);
        if (flt != 16'd0) begin bad = bad + 1; $display("MISMATCH fault %h", flt); end
        if (bad == 0) $display("PASS rstop_sid 16 stops %0d checks", nchk);
        else $display("FAIL rstop_sid %0d of %0d checks", bad, nchk);
        $finish;
    end
endmodule
