`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// ot_s81_hc_ccr (s81-suhc-hier-1011 comb v2, 2026-10-11): the centre-chain return root of the HC combine region (hard
// tile, bottom row, S face to ctile_22).  Captures the centre chain's return (ch_rv / ch_rd = the flat comb's crv /
// crd flops), runs the centre chain's subtree (ot_s81_hc_stree OWN 1) and pads its exports, the return valids (+ the
// subtree fault) and the row's PI byte RP-1 stages (the last stage is the output flop; the consumer's capture is
// stage RP, as the flat comb's u_pex / u_prv).  The crd capture flop is an output: the return pad ot_s81_hc_cpad
// continues it.  Lockstep: register counts identical to the flat comb.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_hc_ccr #(
    parameter integer NG = 256, D = 5120, NCOL = 3, GS = 8, S_RD = 2, S_WR = 8, S_RT = 4, ML = 5, AL = 4,
    // Defaults = the PRODUCTION (HIER3, CSPLIT) core tuple the hard view s81hc_ccrh2_ref was routed at (HALF 1, RLY 2,
    // RF 4, DW 6, RET_EXTRA 0): the hard-pad parent (ot_s81_hc_ccr_align under OT_S81_HC_PAD_HARD) instantiates this
    // module with no parameters, so the defaults ARE the hard configuration.  (Until s81hc-1013 r6 they were the
    // retired HIER1 tuple HALF 0 / RLY 1 / RF 1 / DW 5, and the hard-pad composition ran to TMAX.)
    parameter integer MUT = 0, AMUT = 0, RF = 4, RT = 1, RW = 2, YD = 16, HALF = 1, RLY = 2, DW = 6, RET_EXTRA = 0,
    // HC-COMB-3 2026-10-16: OREG 1 = crd_o is a second register (crd = W-pin capture, crd_q = E-pin launch); the pad
    // split (ot_s81_hc_cpad_split / _roots20) is one return stage shorter, so the centre return depth is unchanged.
    parameter integer OREG = 1
) (
    input  wire                 sk, srs,
    input  wire [RVW-1:0]       ch_rv,
    input  wire [RDW-1:0]       ch_rd,
    output wire [RDW-1:0]       crd_o,         // stage 0 (the capture), on to ot_s81_hc_cpad
    output wire [RVW-1:0]       crv_o,         // stage RP-1
    output wire [7:0]           cpi_o,         // stage RP-1: the row's PI byte
    output wire [NE1*32-1:0]    ex1_o          // stage RP-1: the subtree exports
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
    localparam integer RP = RT + 2 + PAD + RET_EXTRA * (NP - L1) * (HALF ? 2 : 1);                         // return: relay + send + capture + padding
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
    reg [RVW-1:0] crv;
    reg [RDW-1:0] crd;
    always @(posedge sk or negedge rs_n) if (!rs_n) crv <= 0; else crv <= ch_rv;
    always @(posedge sk) crd <= ch_rd;
    generate if (OREG) begin : g_oreg
        reg [RDW-1:0] crd_q;
        always @(posedge sk) crd_q <= crd;
        assign crd_o = crd_q;
    end else begin : g_noreg
        assign crd_o = crd;
    end endgenerate
    wire [NE1*32-1:0] ex1;
    wire              tf1;
    ot_s81_hc_stree #(.NS(NS), .NP(NP), .LA(AL), .OWN(1)) u_tree1 (.clk(sk), .rst_n(rs_n), .v(crv[S_RT]),
        .pk(crd[P_D +: NP * 128]), .im(32'd0), .ex(ex1), .r_v(), .r(), .fault(tf1));
    wire [RVW-1:0] crv_f = {crv[RVW-1], crv[RVW-2] | tf1, crv[RVW-3:0]};
    ot_hdc_delay #(.W(RVW), .D(RP - 1), .RESET(1)) u_prv (.clk(sk), .rst_n(rs_n), .d(crv_f), .q(crv_o));
    ot_hdc_delay #(.W(8), .D(RP - 1)) u_ppi (.clk(sk), .rst_n(rs_n), .d(crd[P_PI +: 8]), .q(cpi_o));
    ot_hdc_delay #(.W(NE1 * 32), .D(RP - 1)) u_pex (.clk(sk), .rst_n(rs_n), .d(ex1), .q(ex1_o));
endmodule
