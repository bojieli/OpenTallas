`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// ot_s81_hc_cntree (s81-suhc-hier-1011 comb v2, 2026-10-11): the norm sum tree of the HC combine region (hard tile,
// middle row).  Stage 1 captures the outer chain roots' return valid (bit S_RT), PI byte and exported subtree nodes
// (w / e); the centre chain's arrive already padded from ot_s81_hc_ccr (captured here = stage RP).  Stage 2 is the
// merged return / imported nodes register (the flat comb's hroot rv / rd / imq pin flops), then the final rungs
// (ot_s81_hc_stree OWN 3), the PI line and the vector levels.  ngo (job go, clears the vector levels) comes from
// ot_s81_hc_cseq (+1 vs the flat comb, far ahead of the first vector sum); ss_v / ss / the tree fault are output flops.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_hc_cntree #(
    parameter integer NG = 256, D = 5120, NCOL = 3, GS = 8, S_RD = 2, S_WR = 8, S_RT = 4, ML = 5, AL = 4,
    parameter integer MUT = 0, AMUT = 0, RF = 1, RT = 1, RW = 2, YD = 16, HALF = 0, RLY = 1, DW = 3 + RW
) (
    input  wire                 sk, srs,
    input  wire                 w_rvt, e_rvt,   // w_rv[S_RT] / e_rv[S_RT]
    input  wire [7:0]           w_pi, e_pi,     // w_rd[P_PI +: 8] / e_rd[P_PI +: 8]
    input  wire [NE0*32-1:0]    w_ex,
    input  wire [NE2*32-1:0]    e_ex,
    input  wire                 c_rvt,          // centre (ot_s81_hc_ccr), stage RP-1 at the pin
    input  wire [7:0]           c_pi,
    input  wire [NE1*32-1:0]    c_ex,
    input  wire                 ngo_i,
    output reg                  ss_v,
    output reg  [31:0]          ss,
    output reg                  tflt
);
    // the comb's geometry (identical to ot_s81_hc_comb; defaults = the hardened NG 256 HIER=1 configuration)
    localparam integer NS = NG / GS;
    localparam integer NP = (NS + NCOL - 1) / NCOL;
    localparam integer L1 = (NS - 2 * NP > 0) ? NS - 2 * NP : 0;
    localparam integer FVW = S_RD + 5, RVW = S_RT + 4;
    localparam integer YW  = NP * GS * 32;
    localparam integer FDD = (S_RD * 512 > YW) ? S_RD * 512 : YW;
    localparam integer O_D = 5 + S_RD * 16 + 20 + 6 + 8 + 32 + 1, FSW = O_D + S_RD * 512, FDW = O_D + FDD;
    localparam integer P_T = 0, P_I = S_RT, P_Q = P_I + 8 * S_RT, P_PI = P_Q + 16 * S_RT, P_D = P_PI + 8,
                       RDW = P_D + 512 * S_RT;
    localparam integer WSL = 1 + 14 + 16 + 512;
    localparam integer YS1 = (L1 > 0) ? L1 * GS * 32 : 1;
    localparam integer HOP = 2 + RLY;                             // registers a sub-tile hop (each bus)
    localparam integer PAD = HOP * (NP - L1) * (HALF ? 2 : 1);    // the centre chain is short by NP - L1 octets
    localparam integer FP = 2 + RF + PAD;                         // forward: send + capture + RF + padding
    localparam integer RP = RT + 2 + PAD;                         // return: relay + send + capture + padding
    reg [1:0] rsr;                                                // tile-local reset relay (2 flops at the pin)
    always @(posedge sk) rsr <= {rsr[0], srs};
    wire rs_n = rsr[1];
    localparam integer NL = 4 * NS;
    localparam integer LT = $clog2(NL);
    localparam integer L0 = NP, L2 = NP;
    localparam integer B0 = 0, B1 = NP, B2 = NP + L1;
    function automatic integer lev(input integer n);
        integer t;
        begin t = 0; while ((n >> (t + 1)) > 0) t = t + 1; lev = LT - t; end
    endfunction
    function automatic integer owner(input integer n);
        integer k, sz, s0;
        begin
            k = lev(n); sz = 1 << k; s0 = ((n << k) - NL) % NS;
            owner = 3;
            if (sz <= NS) begin
                if (L0 > 0 && s0 >= B0 && s0 + sz <= B0 + L0) owner = 0;
                else if (L1 > 0 && s0 >= B1 && s0 + sz <= B1 + L1) owner = 1;
                else if (L2 > 0 && s0 >= B2 && s0 + sz <= B2 + L2) owner = 2;
            end
        end
    endfunction
    function automatic integer expd(input integer n, input integer c);
        expd = (owner(n) == c) && (c != 3) && (n == 1 || owner(n / 2) != c);
    endfunction
    function automatic integer exidx(input integer n, input integer c);
        integer m, t;
        begin t = 0; for (m = 1; m < n; m = m + 1) t = t + expd(m, c); exidx = t; end
    endfunction
    function automatic integer necnt(input integer c);
        necnt = exidx(2 * NL, c);
    endfunction
    localparam integer NE0_ = necnt(0), NE1_ = necnt(1), NE2_ = necnt(2);
    localparam integer NE0 = (NE0_ > 0) ? NE0_ : 1, NE1 = (NE1_ > 0) ? NE1_ : 1, NE2 = (NE2_ > 0) ? NE2_ : 1;
    localparam integer NIM_ = NE0_ + NE1_ + NE2_, NIM = (NIM_ > 0) ? NIM_ : 1;
    localparam integer N  = 4 * NG;
    localparam integer NV = D / N;
    localparam integer LA = AL;
    // ---------------------------------------------------------------- captures (stage 1 outer, stage RP centre)
    reg                wrv, erv, crv;
    reg  [7:0]         wpi, epi, cpi;
    reg  [NE0*32-1:0]  wex;
    reg  [NE2*32-1:0]  eex;
    reg  [NE1*32-1:0]  cex;
    reg                ngo;
    always @(posedge sk or negedge rs_n)
        if (!rs_n) begin wrv <= 1'b0; erv <= 1'b0; crv <= 1'b0; ngo <= 1'b0; end
        else begin wrv <= w_rvt; erv <= e_rvt; crv <= c_rvt; ngo <= ngo_i; end
    always @(posedge sk) begin wpi <= w_pi; epi <= e_pi; cpi <= c_pi; wex <= w_ex; eex <= e_ex; cex <= c_ex; end
    // ---------------------------------------------------------------- merged (stage 2)
    wire [NIM*32-1:0] m_im;
    generate
        if (NIM_ > 0) begin : g_im
            if (NE0_ > 0) begin : g0 assign m_im[0 +: NE0_ * 32] = wex[NE0_ * 32 - 1:0]; end
            if (NE1_ > 0) begin : g1 assign m_im[NE0_ * 32 +: NE1_ * 32] = cex[NE1_ * 32 - 1:0]; end
            if (NE2_ > 0) begin : g2 assign m_im[(NE0_ + NE1_) * 32 +: NE2_ * 32] = eex[NE2_ * 32 - 1:0]; end
        end else begin : g_noim
            assign m_im = 32'd0;
        end
    endgenerate
    reg              rv;
    reg  [7:0]       pi;
    reg [NIM*32-1:0] imq;
    always @(posedge sk or negedge rs_n) if (!rs_n) rv <= 1'b0; else rv <= wrv | erv | ((L1 > 0) ? crv : 1'b0);
    always @(posedge sk) begin pi <= wpi | epi | ((L1 > 0) ? cpi : 8'd0); imq <= m_im; end
    // ---------------------------------------------------------------- final rungs + vector levels
    wire [7:0] tvi;
    ot_hdc_delay #(.W(8), .D(LT * LA)) u_tvi (.clk(sk), .rst_n(rs_n), .d(pi), .q(tvi));
    wire        vsum_v, tf;
    wire [31:0] vsum;
    ot_s81_hc_stree #(.NS(NS), .NP(NP), .LA(LA), .OWN(3)) u_tree (.clk(sk), .rst_n(rs_n), .v(rv),
        .pk({NP*128{1'b0}}), .im(imq), .ex(), .r_v(vsum_v), .r(vsum), .fault(tf));
    genvar n;
    localparam integer NVP = (NV <= 1) ? 1 : (1 << $clog2(NV));
    localparam integer LAV = (LA >= 5) ? LA : LA + 1;
    wire [31:0] nv_ [1:2*NVP-1];
    wire        nd [1:2*NVP-1];
    wire        np [1:2*NVP-1];
    wire [NVP:0] nf;
    assign nf[0] = 1'b0;
    assign nf[NVP] = 1'b0;
    generate
        for (n = NVP; n < 2 * NVP; n = n + 1) begin : g_leaf
            reg [31:0] val;
            reg        vld;
            wire       hit = vsum_v && tvi == n - NVP;
            always @(posedge sk or negedge rs_n)
                if (!rs_n) vld <= 1'b0;
                else if (ngo) vld <= 1'b0;
                else if (hit) vld <= 1'b1;
            always @(posedge sk) if (hit) val <= vsum;
            assign np[n] = hit;
            assign nd[n] = vld || hit;
            assign nv_[n] = vld ? val : vsum;
        end
        for (n = 1; n < NVP; n = n + 1) begin : g_vn
            localparam integer H = $clog2(NVP) - ($clog2(n + 1) - 1);
            if ((((2 * n + 1) << (H - 1)) - NVP) < NV) begin : g_add
                reg st, vld;
                reg [31:0] val;
                wire [LAV:0] av;
                wire [31:0] s;
                wire fire = nd[2 * n] && nd[2 * n + 1] && !st && !ngo;
                ot_hdc_vline #(.D(LAV)) u_v (.clk(sk), .rst_n(rs_n), .v(fire), .vd(av));
                ot_dsrom_qadd #(.LAT(LAV)) u_a (sk, rs_n, fire, nv_[2 * n], nv_[2 * n + 1], s, nf[n]);
                always @(posedge sk or negedge rs_n) begin
                    if (!rs_n) begin st <= 1'b0; vld <= 1'b0; end
                    else if (ngo) begin st <= 1'b0; vld <= 1'b0; end
                    else begin
                        if (fire) st <= 1'b1;
                        if (av[LAV]) vld <= 1'b1;
                    end
                end
                always @(posedge sk) if (av[LAV]) val <= s;
                assign np[n] = av[LAV];
                assign nd[n] = vld || av[LAV];
                assign nv_[n] = vld ? val : s;
            end else begin : g_pass
                assign nv_[n] = nv_[2 * n];
                assign nd[n] = nd[2 * n];
                assign np[n] = np[2 * n];
                assign nf[n] = 1'b0;
            end
        end
    endgenerate
    always @(posedge sk or negedge rs_n)
        if (!rs_n) begin ss_v <= 1'b0; tflt <= 1'b0; end
        else begin ss_v <= np[1] && !ngo; tflt <= tf || (|nf); end
    always @(posedge sk) ss <= nv_[1];
endmodule
