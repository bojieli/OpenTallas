`timescale 1ns/1ps
// FAM-S81-LEPE-4 11-22 XG-1: XMID equivalence bench for the ring stop variants (DUT = `TB_XMID_DUT, default
// ot_s81sl_rstop).  Pairs of stops with the same strap get the same sparse random traffic on every input port
// (line beats from W / E with random kind / hops, V fragments, own leaf fragments, xfin NX, control-plane injects);
// XMID 1 outputs (every output port, fault included) must equal the XMID 0 outputs of the previous edge, every edge.
// Verdict: PASS rstop_xmid <dut> <edges> / FAIL rstop_xmid <dut> <bad> of <checks>.
// Mutant (must FAIL): +define+OT_S81SL_RSTOP_MUT_XMIDSKIP (ci_b skips the face stage).
`ifndef TB_XMID_DUT
`define TB_XMID_DUT ot_s81sl_rstop
`endif
module tb_s81sl_rstop_xmid;
    localparam integer W = 1104, V = 276, NP = 4, N = 6000;
    localparam integer OW = 2*W + V + 2*173 + 3 + 3 + 21 + 3072 + 1 + W + 1 + W + 1 + V + 1;
    reg clk = 1'b0; always #0.5 clk = ~clk;
    reg rst_n = 1'b0;
    reg [W-1:0] ri_w [0:NP-1], ri_e [0:NP-1], ci_b [0:NP-1]; reg [V-1:0] vi [0:NP-1];
    reg [4:0] xf_v [0:NP-1], xf_s [0:NP-1]; reg [5*V-1:0] xf [0:NP-1]; reg [172:0] nx_eo [0:NP-1], nx_wo [0:NP-1];
    reg [2:0] ci_dir [0:NP-1];
    wire [OW-1:0] o0 [0:NP-1], o1 [0:NP-1];
    localparam [15:0] SIDS = {4'd14, 4'd9, 4'd5, 4'd0};
    genvar g, x;
    generate for (g = 0; g < NP; g = g + 1) begin : g_p
        for (x = 0; x < 2; x = x + 1) begin : g_x
            wire [W-1:0] roe, row, dle, dlw; wire [V-1:0] vo, dlvb; wire [172:0] nwi, nei;
            wire [2:0] gv, gf; wire [20:0] gi; wire [3071:0] gd; wire dlev, dlwv, dlvv, flt;
            `TB_XMID_DUT #(.XMID(x)) u (.clk(clk), .rst_n(rst_n), .sid(SIDS[4*g +: 4]), .ri_w(ri_w[g]), .ri_e(ri_e[g]),
                .ro_e(roe), .ro_w(row), .vi(vi[g]), .vo(vo), .xf_v(xf_v[g]), .xf_s(xf_s[g]), .xf(xf[g]), .nx_wi(nwi), .nx_ei(nei),
                .nx_eo(nx_eo[g]), .nx_wo(nx_wo[g]), .g_v(gv), .g_fam(gf), .g_idx(gi), .g_d(gd), .dl_ev(dlev), .dl_e(dle),
                .dl_wv(dlwv), .dl_w(dlw), .dl_vv(dlvv), .dl_vb(dlvb), .ci_dir(ci_dir[g]), .ci_b(ci_b[g]), .fault(flt));
            if (x == 0) assign o0[g] = {roe, row, vo, nwi, nei, gv, gf, gi, gd, dlev, dle, dlwv, dlw, dlvv, dlvb, flt};
            else        assign o1[g] = {roe, row, vo, nwi, nei, gv, gf, gi, gd, dlev, dle, dlwv, dlw, dlvv, dlvb, flt};
        end
    end endgenerate
    reg [OW-1:0] o0d [0:NP-1];
    integer i, p, t, bad = 0, nchk = 0, nact = 0, seed = 7;
    function automatic [W-1:0] rbeat(input integer pct);
        reg [W-1:0] b; integer k;
        begin
            b = 0;
            if (($urandom % 100) < pct) begin
                for (k = 0; k < W; k = k + 32) b[k +: 32] = $urandom;
                b[0] = 1'b1; b[3:1] = $urandom % 4; b[8:4] = $urandom % 8;
            end
            rbeat = b;
        end
    endfunction
    always @(posedge clk) for (p = 0; p < NP; p = p + 1) o0d[p] <= o0[p];
    initial begin
        for (p = 0; p < NP; p = p + 1) begin ri_w[p] = 0; ri_e[p] = 0; ci_b[p] = 0; vi[p] = 0; xf_v[p] = 0; xf_s[p] = 0; xf[p] = 0; nx_eo[p] = 0; nx_wo[p] = 0; ci_dir[p] = 0; end
        void'($urandom(seed));
        repeat (6) @(negedge clk); rst_n = 1'b1; repeat (8) @(negedge clk);
        for (t = 0; t < N; t = t + 1) begin
            @(negedge clk);
            for (p = 0; p < NP; p = p + 1) begin
                ri_w[p] = rbeat(8); ri_e[p] = rbeat(8);
                vi[p] = rbeat(5); vi[p][3:1] = $urandom % 4;
                xf_v[p] = (($urandom % 100) < 6) ? (5'd1 << ($urandom % 5)) : 5'd0; xf_s[p] = xf_v[p] & $urandom;
                for (i = 0; i < 5*V; i = i + 32) xf[p][i +: 32] = $urandom;
                nx_eo[p] = (($urandom % 100) < 4) ? {1'b1, 4'($urandom), 8'($urandom), 160'({$urandom, $urandom, $urandom, $urandom, $urandom})} : 173'd0;
                nx_wo[p] = (($urandom % 100) < 4) ? {1'b1, 4'($urandom), 8'($urandom), 160'({$urandom, $urandom, $urandom, $urandom, $urandom})} : 173'd0;
                ci_dir[p] = (($urandom % 100) < 4) ? 3'(1 << ($urandom % 3)) : 3'd0; ci_b[p] = ci_dir[p] != 0 ? rbeat(100) : rbeat(3);
            end
        end
        for (p = 0; p < NP; p = p + 1) begin ri_w[p] = 0; ri_e[p] = 0; ci_b[p] = 0; vi[p] = 0; xf_v[p] = 0; nx_eo[p] = 0; nx_wo[p] = 0; ci_dir[p] = 0; end
        repeat (16) @(negedge clk);
        if (nact < 1000) begin bad = bad + 1; $display("MISMATCH bench activity too low: %0d active edges", nact); end
        if (bad == 0) $display("PASS rstop_xmid %s %0d checks %0d active", `"`TB_XMID_DUT`", nchk, nact);
        else $display("FAIL rstop_xmid %s %0d of %0d checks", `"`TB_XMID_DUT`", bad, nchk);
        $finish;
    end
    always @(posedge clk) if (rst_n) begin
        #0.1;
        for (p = 0; p < NP; p = p + 1) begin
            nchk = nchk + 1;
            if (o0d[p] !== o1[p]) begin bad = bad + 1; if (bad < 12) $display("MISMATCH pair %0d edge %0t", p, $time); end
            if (|o0d[p][OW-1:OW-2*W]) nact = nact + 1;
        end
    end
endmodule
