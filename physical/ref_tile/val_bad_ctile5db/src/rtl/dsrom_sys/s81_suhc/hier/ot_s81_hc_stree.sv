`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// ot_s81_hc_stree (s81-suhc-hier-1011, 2026-10-11): one tile's share of the norm's per-vector sum-of-squares tree of
// the hierarchical S81 HC slab -- the golden pairwise tree over NL = 4 NS leaves (leaf j*NS + s = bank j's partial of
// sub-tile s, itself the aligned subtree of that sub-tile's chunks), heap-numbered (node n covers leaves
// (n << k) - NL .. + 2^k - 1, k its level).  The sub-tiles sit in 3 column chains (chain c = sub-tiles B_c .. B_c + L_c
// - 1; L = NP, NS - 2 NP, NP: the short chain in the centre).  A node whose leaves all lie in one chain's range of one
// bank is computed by that chain's root (OWN = c, from the chain's partial packet: slot p = sub-tile B_c + p); every
// other node by the combine tile (OWN = 3).  A chain node whose parent is not the chain's is EXPORTED (port ex, in
// increasing heap order); the combine tile IMPORTS them (port im: chain 0's, then 1's, then 2's), so the combine tile
// holds only the final rungs and the result is the golden tree's, bit for bit.
// Schedule: leaves valid with v; a level-k node fires LA (k - 1) cycles after v (chain roots: v = the packet's arrival;
// combine: v = the packet's arrival + the seam latency, the exports travelling the same seam), the root (combine) is
// valid LT LA after v.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_hc_stree #(
    parameter integer NS = 32, NP = 11, LA = 4, OWN = 3
) (
    input  wire                   clk,
    input  wire                   rst_n,
    input  wire                   v,
    input  wire [NP*128-1:0]      pk,             // chain root: the partial packet (slot p, bank j at 128 p + 32 j)
    input  wire [NIM*32-1:0]      im,             // combine: imported chain nodes
    output wire [NEX*32-1:0]      ex,             // chain root: exported nodes
    output wire                   r_v,            // combine: the vector's sum
    output wire [31:0]            r,
    output wire                   fault
);
    localparam integer NL = 4 * NS;
    localparam integer LT = $clog2(NL);
    localparam integer L0 = NP, L1 = (NS - 2 * NP > 0) ? NS - 2 * NP : 0, L2 = NP;
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
    function automatic integer imoff(input integer c);
        integer t, cc;
        begin t = 0; for (cc = 0; cc < c; cc = cc + 1) t = t + necnt(cc); imoff = t; end
    endfunction
    localparam integer NEX_ = (OWN < 3) ? necnt(OWN) : 0;
    localparam integer NEX  = (NEX_ > 0) ? NEX_ : 1;
    localparam integer NIM_ = (OWN == 3) ? necnt(0) + necnt(1) + necnt(2) : 0;
    localparam integer NIM  = (NIM_ > 0) ? NIM_ : 1;

    wire [LT*LA:0] vl;
    ot_hdc_vline #(.D(LT * LA)) u_v (.clk(clk), .rst_n(rst_n), .v(v), .vd(vl));
    wire [31:0]   val [1:2*NL-1];
    wire [2*NL-1:0] f;
    assign f[0] = 1'b0;
    genvar n;
    generate
        for (n = 1; n < 2 * NL; n = n + 1) begin : g_n
            localparam integer K = lev(n);
            localparam integer O = owner(n);
            if (O == OWN) begin : g_own
                if (n >= NL) begin : g_leaf                       // a chain's leaf: bank j, sub-tile s = slot s - B
                    localparam integer J = (n - NL) / NS, S = (n - NL) % NS;
                    localparam integer B = (OWN == 0) ? B0 : (OWN == 1) ? B1 : B2;
                    assign val[n] = pk[128 * (S - B) + 32 * J +: 32];
                    assign f[n] = 1'b0;
                end else begin : g_add
                    ot_dsrom_qadd #(.LAT(LA)) u_a (clk, rst_n, vl[LA * (K - 1)], val[2 * n], val[2 * n + 1], val[n], f[n]);
                end
                if (OWN < 3 && expd(n, OWN)) begin : g_ex
                    assign ex[32 * exidx(n, OWN) +: 32] = val[n];
                end
            end else if (OWN == 3 && expd(n, O)) begin : g_im
                assign val[n] = im[32 * (imoff(O) + exidx(n, O)) +: 32];
                assign f[n] = 1'b0;
            end else begin : g_none
                assign val[n] = 32'd0;
                assign f[n] = 1'b0;
            end
        end
        if (OWN == 3) begin : g_root
            assign r_v = vl[LT * LA];
            assign r = val[1];
        end else begin : g_nr
            assign r_v = 1'b0;
            assign r = 32'd0;
        end
        if (NEX_ == 0) begin : g_nex
            assign ex = 32'd0;
        end
    endgenerate
    assign fault = |f;
endmodule
