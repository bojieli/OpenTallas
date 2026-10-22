`timescale 1ps/1ps
`default_nettype none
// S81-LAND bench: a source-synchronous die lane (gated forwarded clock at hop 0, N relay stations, each hop delaying
// clock and data by DH ps) lands through ot_s81_land into a block root ck = source clock + LR ps.
// dL = (N + 1) * DH - LR.  Plusargs: N DH LR K R0 G SLIP (gate opens SLIP edges after the calendar's G) CYC.
// PO-SUBMIT (10-19, COORD 0jz): RL = kit reset landing stages (ref_tile reset_landing / OT_RST_LAND: rs__ot_rl0 -> rs__ot_rl1,
// plain ck flops in front of the core, modelled here between the regional reset leaf and the tile).  The core's release
// moves from R0 to R0 + RL; the re-derived die calendar opens the hop-0 gate RL edges later too (GS = gate shift,
// default RL), so K = E + G - R0 and the data latency are unchanged.  GS != RL = an uncompensated calendar (mutant).
// Prints: OT_LAND n=.. dh=.. lr=.. dl=.. k=.. pred=<compile-time latency> meas=<measured latency or -1> mism=.. fault=..
// Latency = ck edges from the source launch edge of a word to the ck edge that registers it in o.
module tb_s81_land;
`ifndef TB_D
`define TB_D 4
`endif
`ifndef TB_KW
`define TB_KW 3
`endif
`ifndef TB_NMAX
`define TB_NMAX 16
`endif
    localparam integer W = `TB_W, T = 834, NMAX = `TB_NMAX;   // LANDFIX-SQ: TB_D / TB_KW / TB_NMAX for the long-lane tile
    integer N, DH, LR, K, R0, G, SLIP, CYC, RL, GS;
    reg cks = 1'b0, ck = 1'b0;
    integer n = -1, m = -1;
    initial begin
        if (!$value$plusargs("N=%d", N)) N = 4;
        if (!$value$plusargs("DH=%d", DH)) DH = 115;
        if (!$value$plusargs("LR=%d", LR)) LR = 100;
        if (!$value$plusargs("K=%d", K)) K = 3;
        if (!$value$plusargs("R0=%d", R0)) R0 = 4;
        if (!$value$plusargs("G=%d", G)) G = 6;
        if (!$value$plusargs("SLIP=%d", SLIP)) SLIP = 0;
        if (!$value$plusargs("CYC=%d", CYC)) CYC = 160;
        if (!$value$plusargs("RL=%d", RL)) RL = 0;
        if (!$value$plusargs("GS=%d", GS)) GS = RL;
    end
    always #(T / 2) cks = ~cks;
    always @(cks) ck <= #(LR) cks;                       // block root: same PLL, insertion LR
    function [W-1:0] f(input integer s);                  // the word the source launches at its edge s
        integer j; reg [31:0] h;
        begin h = s * 32'h9E3779B1 + 32'h7F4A7C15; for (j = 0; j < W; j = j + 1) begin f[j] = h[j % 32] ^ (j[0] & s[0]); if (j % 32 == 31) h = h * 32'h85EBCA6B + 1; end end
    endfunction
    // ---------------------------------------------------------------- source: data on cks, hop-0 clock gate opened at G
    reg [W-1:0] sd = {W{1'b0}};
    reg en_q = 1'b0, en_l = 1'b0;
    always @(posedge cks) begin n = n + 1; sd <= #20 f(n); en_q <= (n >= G + GS + SLIP - 1); end
    always @(cks or en_q) if (!cks) en_l = en_q;          // ICG latch (transparent low)
    wire fck0 = cks & en_l;
    // ---------------------------------------------------------------- relay chain: c[k+1] = c[k] + DH, y[k] = x[k] + DH
    reg [NMAX + 1:0] c = {(NMAX + 2){1'b0}};
    reg [(NMAX + 2) * W - 1:0] x = {((NMAX + 2) * W){1'b0}}, y = {((NMAX + 2) * W){1'b0}};
    integer q;
    always @* c[0] = fck0;
    always @* x[W-1:0] = sd;
    genvar h;
    generate for (h = 0; h <= NMAX; h = h + 1) begin : g_hop
        wire ch = c[h]; wire [W-1:0] xh = x[h * W +: W];
        always @(ch) c[h + 1] <= #(DH) ch;
        always @(xh) y[h * W +: W] <= #(DH) xh;
        wire ch1 = c[h + 1]; wire [W-1:0] yh = y[h * W +: W];
        always @(posedge ch1) x[(h + 1) * W +: W] <= #20 yh;   // station h (flop-first relay, clk->q 20 ps)
    end endgenerate
    reg ck_f; reg [W-1:0] li;
    always @* begin ck_f = c[N + 1]; li = y[N * W +: W]; end
    // ---------------------------------------------------------------- block regional reset: released at ck edge R0 - 1
    reg rs = 1'b1;
    initial #1 rs = 1'b0;                                // power-on reset assert (async clear of both pointers)
    always @(posedge ck) begin m = m + 1; if (m == R0 - 1) rs <= #10 1'b1; end
    // kit reset landing (RL plain ck flops, assert and release both delayed RL edges); RL 0 = rs straight to the tile
    reg [7:0] rl = 8'd0;
    always @(posedge ck) rl <= #10 {rl[6:0], rs};
    wire rs_t = (RL == 0) ? rs : rl[RL - 1];
    wire [W-1:0] o; wire fault;
    wire [`TB_KW-1:0] kk = K;
`ifdef TB_TOP
    // S81-DIE7/LAND (10-18): the hardened tile's own top (dsfd_dvland_<W>[l] wrapper, the kit top) instead of the core
    `TB_TOP dut (.ck_f(ck_f), .i(li), .ck(ck), .rs(rs_t), .k(kk), .o(o), .fault(fault));
`else
    ot_s81_land #(.W(W), .D(`TB_D), .KW(`TB_KW)) dut (.ck_f(ck_f), .i(li), .ck(ck), .rs(rs_t), .k(kk), .o(o), .fault(fault));
`endif
    // ---------------------------------------------------------------- checker (samples o half a period after each ck edge)
    integer pred, mism, chk, L, best, okL;
    reg [W-1:0] hist [0:4095];
    integer mh [0:4095];
    integer nh = 0;
    always @(negedge ck) if (m >= 0) begin hist[nh] = o; mh[nh] = m; nh = nh + 1; end
    initial begin
        mism = 0; chk = 0;
        #(T * 2);
        pred = (R0 + RL) + K - (G + RL) + 1 + N;           // compiler's calendar: release and gate both + RL
        #(T * (CYC));
        for (q = 0; q < nh; q = q + 1)
            if (mh[q] >= R0 + RL + K && mh[q] - pred >= G + RL - 1) begin chk = chk + 1; if (hist[q] !== f(mh[q] - pred)) mism = mism + 1; end
        best = -1;
        for (L = 0; L < 120 && best < 0; L = L + 1) begin
            okL = 1;
            for (q = nh - 64; q < nh; q = q + 1) if (hist[q] !== f(mh[q] - L)) okL = 0;
            if (okL) best = L;
        end
        $display("OT_LAND w=%0d n=%0d dh=%0d lr=%0d dl=%0d k=%0d rl=%0d gs=%0d slip=%0d pred=%0d meas=%0d chk=%0d mism=%0d fault=%0d",
                 W, N, DH, LR, (N + 1) * DH - LR, K, RL, GS, SLIP, pred, best, chk, mism, fault);
        $finish;
    end
endmodule
`default_nettype wire
