`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_s81hd_spr (S81-HEAD HD-TILE 10-21; SPEC.md section 2): spine return node of the S81 release head die.  Captures
// the three bests of a position -- i (spine above / U-turn), iw / ie (W / E row-pair chain ends) -- in any order and,
// when all three are present, fires ONCE (cleared by i.go) the max under the ot_rom_argmax_rows key (FP32 order,
// -0 = +0, lowest row id on ties) with flt = OR of the three.  The x part of o is i.x forwarded two registered cycles
// (N-face pin register, S-face output register; with i.go / i.xv); the x / go / xv of iw / ie are not used (the chain
// ends' copies of the stream).
// Compare: keys (ot_s81hd_key, 2 stages) on the held bests, then two registered levels (pair (iw, ie), then (pair, i)).
// Census (<= 32 load pins a driver; a mapped select / enable costs 2 pins a bit): hold enables = 5 kept rv copies a
// port (<= 11 bits each), selects = kept copies per <= 8 bits.
// Pins: every input lands in a flop, every output leaves a flop.  Reset: control / valid bits only.
// ---------------------------------------------------------------------------
module ot_s81hd_spr (
    input  wire         ck,
    input  wire         rst_n,
    input  wire [564:0] i,
    input  wire [564:0] iw,
    input  wire [564:0] ie,
    output wire [564:0] o
);
    // pin registers of the stream (i only)
    reg [511:0] x_q;
    reg         go_q, xv_q;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin go_q <= 1'b0; xv_q <= 1'b0; end
        else begin go_q <= i[512]; xv_q <= i[513]; end
    always @(posedge ck) x_q <= i[511:0];
    // S-face output register of the stream (second stage): spr_m route 1 failed reg -> out o[512] -467 ps (the N-face
    // pin flop drove the S-face pin 648 um away in one cycle)
    reg [511:0] xo_q;
    reg         goo_q, xvo_q;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin goo_q <= 1'b0; xvo_q <= 1'b0; end
        else begin goo_q <= go_q; xvo_q <= xv_q; end
    always @(posedge ck) xo_q <= x_q;
    wire [564:0] ip [0:2];
    assign ip[0] = i; assign ip[1] = iw; assign ip[2] = ie;
    // per port: pin register, 5 kept rv copies, raw hold {flt, bits, row}, key of the held bits
    wire [49:0] h [0:2];
    wire [31:0] hk [0:2];
    wire [2:0]  rvs;
    genvar p, g;
    generate for (p = 0; p < 3; p = p + 1) begin : g_p
        (* keep *) reg [4:0] rv_q;          // [0] row[8:0] [1] row[16:9] + flt [2] bits[10:0] [3] bits[21:11] [4] bits[31:22] + state
        reg [49:0] r_q;                     // {flt, bits[31:0], row[16:0]}
        reg [49:0] hq;
        always @(posedge ck or negedge rst_n)
            if (!rst_n) rv_q <= 5'd0;
            else rv_q <= {5{ip[p][514]}};
        always @(posedge ck) begin
            r_q <= ip[p][564:515];
            if (rv_q[0]) hq[8:0]   <= r_q[8:0];
            if (rv_q[1]) begin hq[16:9] <= r_q[16:9]; hq[49] <= r_q[49]; end
            if (rv_q[2]) hq[27:17] <= r_q[27:17];
            if (rv_q[3]) hq[38:28] <= r_q[38:28];
            if (rv_q[4]) hq[48:39] <= r_q[48:39];
        end
        assign h[p] = hq;
        assign rvs[p] = rv_q[4];
        ot_s81hd_key u_k (.ck(ck), .x(hq[48:17]), .key(hk[p]));
    end endgenerate
    // capture state: have -> 2 cycles for the key -> ready; fire once, cleared by i.go
    reg [2:0] have, hd1, hd2;
    reg       fired, s1_v, s2_v, s3_v, o_rv;
`ifdef OT_S81HD_MUT_SPR_EARLY
    wire ready = hd2[0] & hd2[2] & ~fired & ~go_q;                   // MUTANT: fires without the W chain best
`else
    wire ready = (&hd2) & ~fired & ~go_q;
`endif
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin have <= 3'd0; hd1 <= 3'd0; hd2 <= 3'd0; fired <= 1'b0; s1_v <= 1'b0; s2_v <= 1'b0; s3_v <= 1'b0; o_rv <= 1'b0; end
        else begin
            have  <= rvs | (have & {3{~go_q}});
            hd1   <= have & {3{~go_q}};
            hd2   <= hd1 & {3{~go_q}};
            fired <= ready | (fired & ~go_q);
            s1_v <= ready; s2_v <= s1_v; s3_v <= s2_v; o_rv <= s3_v;
        end
    // v better than u: greater key, or equal key and lower row
    function automatic better(input [31:0] kv, input [16:0] rv, input [31:0] ku, input [16:0] ru);
        better = kv > ku || (kv == ku && rv < ru);
    endfunction
    // select groups: row [5:0] [11:6] [16:12] (3), bits / key 4 x 8
    // level 1: pair = max(iw, ie) -> {flt-or, bits, row} + its key
    (* keep *) reg [10:0] sa_q;             // [2:0] row groups, [6:3] bits bytes, [10:7] key bytes
    reg [49:0] pr;
    reg [31:0] pk;
    always @(posedge ck) sa_q <= {11{better(hk[2], h[2][16:0], hk[1], h[1][16:0])}};
    integer b;
    always @(posedge ck) begin
        for (b = 0; b < 17; b = b + 1) pr[b] <= sa_q[b < 6 ? 0 : (b < 12 ? 1 : 2)] ? h[2][b] : h[1][b];
        for (b = 0; b < 32; b = b + 1) begin
            pr[17 + b] <= sa_q[3 + b / 8] ? h[2][17 + b] : h[1][17 + b];
            pk[b]      <= sa_q[7 + b / 8] ? hk[2][b] : hk[1][b];
        end
        pr[49] <= h[0][49] | h[1][49] | h[2][49];
    end
    // level 2: max(pair, i)
    (* keep *) reg [6:0] sb_q;              // [2:0] row groups, [6:3] bits bytes
    reg [49:0] o_r;
    always @(posedge ck) sb_q <= {7{better(hk[0], h[0][16:0], pk, pr[16:0])}};
    always @(posedge ck) begin
        for (b = 0; b < 17; b = b + 1) o_r[b] <= sb_q[b < 6 ? 0 : (b < 12 ? 1 : 2)] ? h[0][b] : pr[b];
        for (b = 0; b < 32; b = b + 1) o_r[17 + b] <= sb_q[3 + b / 8] ? h[0][17 + b] : pr[17 + b];
        o_r[49] <= pr[49];
    end
    // fire: ready at c -> sa_q (c) -> pr (c+1) -> sb_q (c+2) -> o_r (c+3); o_rv aligned
    assign o = {o_r[49], o_r[48:17], o_r[16:0], o_rv, xvo_q, goo_q, xo_q};
endmodule
