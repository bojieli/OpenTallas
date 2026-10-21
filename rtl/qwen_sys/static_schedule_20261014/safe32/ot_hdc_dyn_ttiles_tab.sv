`timescale 1ns/1ps
// QW-H16V 10-20: the 16-entry DYN_TTILES table (split_log2 = 0..15) of ot_hdc_dyn_ttiles, log depth.
// Bit-identical per entry to ot_hdc_dyn_ttiles #(W,G,NW) with .split_log2(ds):
//   rounds[ds] = invalid[ds] ? 0 : ((pos >> (WT+GT-ds)) / ODD) + 1        (NW-bit wrap, as the original)
// Exact identity floor(floor(x / 2^s) / ODD) = floor(floor(x / ODD) / 2^s): ONE quotient q = (pos >> WT) / ODD is shared
// and each entry is the constant shift q >> (GT-ds) plus one.  For ODD = 3 the quotient is the mod-3 suffix scan
// (Kogge-Stone, log2 levels) instead of the yosys array divider (h16t: 40-level ripple, -345 ps TT); increments are
// Kogge-Stone prefix-AND.  Every scan level is a (* keep *) wire so gate mapping cannot fold it back into a chain.
module ot_hdc_dyn_ttiles_q #(
    parameter integer W=16, G=4, NW=18
) (
    input wire [NW-1:0] pos,
    output wire [NW-1:0] quot              // (pos >> log2(W)) / ODD, zero-extended
);
    function automatic integer trailing_zeros(input integer value);
        integer n;
        begin
            n=0;
            while ((value & 1)==0 && value>0) begin
                value=value>>1; n=n+1;
            end
            trailing_zeros=n;
        end
    endfunction
    localparam integer WT=trailing_zeros(W);
    localparam integer GT=trailing_zeros(G);
    localparam integer ODD=G>>GT;
    localparam integer XN=(NW>WT) ? NW-WT : 1;
    localparam integer L=(XN>1) ? $clog2(XN) : 1;
    initial if (NW <= WT) $error("ot_hdc_dyn_ttiles_tab needs NW > log2(W)");
    wire [XN-1:0] x = pos >> WT;
    wire [XN-1:0] q;
    genvar l, k;
    generate if (ODD == 1) begin : g_q1
        assign q = x;
    end else if (ODD == 3) begin : g_q3
        // v_k = x_k * (2^k mod 3) in {0,1,2} (2-bit code); S_j = sum_{k>=j} v_k mod 3 (suffix scan);
        // r_j = (x >> j) mod 3 = S_j * 2^j mod 3 (j odd: 1 <-> 2); quotient bit q_i = 2*r_{i+1} + x_i >= 3.
        (* keep *) wire [2*XN*(L+1)-1:0] s;
        for (k = 0; k < XN; k = k + 1) begin : g_v
            assign s[2*k +: 2] = x[k] ? ((k % 2 == 0) ? 2'd1 : 2'd2) : 2'd0;
        end
        for (l = 0; l < L; l = l + 1) begin : g_l
            for (k = 0; k < XN; k = k + 1) begin : g_k
                wire [1:0] a = s[2*XN*l + 2*k +: 2];
                if (k + (1 << l) < XN) begin : g_add
                    wire [1:0] b = s[2*XN*l + 2*(k + (1 << l)) +: 2];
                    // a + b mod 3 on codes {0,1,2}
                    assign s[2*XN*(l+1) + 2*k +: 2] =
                        (a == 2'd0) ? b : (b == 2'd0) ? a : (a == b) ? {a[0], a[1]} : 2'd0;
                end else begin : g_pass
                    assign s[2*XN*(l+1) + 2*k +: 2] = a;
                end
            end
        end
        for (k = 0; k < XN; k = k + 1) begin : g_qb
            if (k == XN - 1) begin : g_top
                assign q[k] = 1'b0 | (x[k] & 1'b0);                // r_XN = 0: 2*0 + x < 3
            end else begin : g_mid
                wire [1:0] sj = s[2*XN*L + 2*(k+1) +: 2];
                wire [1:0] rj = ((k + 1) % 2 == 0) ? sj : {sj[0], sj[1]};
                assign q[k] = rj[1] | (rj[0] & x[k]);
            end
        end
    end else begin : g_qn
        assign q = x / ODD;
    end endgenerate
    assign quot = q;                      // zero-extended
endmodule

// The 16 entries from the shared quotient (quot = ot_hdc_dyn_ttiles_q(pos)): rounds[ds] = invalid ? 0 : (quot >> (GT-ds)) + 1.
module ot_hdc_dyn_ttiles_tab #(
    parameter integer W=16, G=4, NW=18
) (
    input wire [NW-1:0] quot,
    output wire [16*NW-1:0] rounds,
    output wire [15:0] invalid
);
    function automatic integer trailing_zeros(input integer value);
        integer n;
        begin
            n=0;
            while ((value & 1)==0 && value>0) begin
                value=value>>1; n=n+1;
            end
            trailing_zeros=n;
        end
    endfunction
    localparam integer WT=trailing_zeros(W);
    localparam integer GT=trailing_zeros(G);
    genvar ds;
    wire [NW-1:0] q = quot;
    // entries
    generate for (ds = 0; ds < 16; ds = ds + 1) begin : g_e
        localparam integer BAD = ((W != (1 << WT)) || ds > GT || ds > WT + GT) ? 1 : 0;
        localparam integer SH = (BAD != 0) ? 0 : GT - ds;
        assign invalid[ds] = (BAD != 0);
        if (BAD != 0) begin : g_bad
            assign rounds[ds*NW +: NW] = {NW{1'b0}};
        end else begin : g_ok
            wire [NW-1:0] a = q >> SH;
            wire [NW-1:0] y;
            ot_hdc_inc_ks #(.W(NW)) u_inc (.a(a), .y(y));
            assign rounds[ds*NW +: NW] = y;
        end
    end endgenerate
endmodule
