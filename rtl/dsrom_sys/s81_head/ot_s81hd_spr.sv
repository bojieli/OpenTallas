`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_s81hd_spr (S81-HEAD HD-TILE 10-21; SPEC.md section 2): spine return node of the S81 release head die.  Captures
// the three bests of a position -- i (spine above / U-turn), iw / ie (W / E row-pair chain ends) -- in any order and,
// when all three are present, fires ONCE (cleared by i.go) the max under the ot_rom_argmax_rows key (FP32 order,
// -0 = +0, lowest row id on ties) with flt = OR of the three.  The x part of o is i.x forwarded one registered cycle
// (with i.go / i.xv); the x / go / xv of iw / ie are not used (the chain ends' copies of the stream).
// Compare: two registered levels (pair (iw, ie), then (pair, i)); selects are kept copies (<= 32 loads).
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
    // pin registers
    reg [511:0] x_q;
    reg         go_q, xv_q;
    wire [564:0] ip [0:2];
    assign ip[0] = i; assign ip[1] = iw; assign ip[2] = ie;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin go_q <= 1'b0; xv_q <= 1'b0; end
        else begin go_q <= i[512]; xv_q <= i[513]; end
    always @(posedge ck) x_q <= i[511:0];
    // per port: pin register, 3 kept rv copies ([0] row + flt, [1] bits[15:0], [2] bits[31:16] + state), hold
    wire [49:0] h [0:2];
    wire [2:0]  rvs;
    genvar p;
    generate for (p = 0; p < 3; p = p + 1) begin : g_p
        (* keep *) reg [2:0] rv_q;
        reg [49:0] r_q;                     // {flt, bits, row}
        reg [49:0] hq;
        always @(posedge ck or negedge rst_n)
            if (!rst_n) rv_q <= 3'd0;
            else rv_q <= {3{ip[p][514]}};
        always @(posedge ck) begin
            r_q <= ip[p][564:515];
            if (rv_q[0]) begin hq[16:0] <= r_q[16:0]; hq[49] <= r_q[49]; end
            if (rv_q[1]) hq[32:17] <= r_q[32:17];
            if (rv_q[2]) hq[48:33] <= r_q[48:33];
        end
        assign h[p] = hq;
        assign rvs[p] = rv_q[2];
    end endgenerate
    reg [2:0]  have;
    reg        fired;
`ifdef OT_S81HD_MUT_SPR_EARLY
    wire ready = have[0] & have[2] & ~fired & ~go_q;                 // MUTANT: fires without the W chain best
`else
    wire ready = (&have) & ~fired & ~go_q;
`endif
    reg  s1_v, s2_v;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin have <= 3'd0; fired <= 1'b0; s1_v <= 1'b0; s2_v <= 1'b0; end
        else begin
            have <= rvs | (have & {3{~go_q}});
            fired <= ready | (fired & ~go_q);
            s1_v <= ready;
            s2_v <= s1_v;
        end
    function automatic [31:0] okey(input [31:0] x);
        reg [31:0] c;
        begin
            c = (x == 32'h8000_0000) ? 32'd0 : x;
            okey = c[31] ? ~c : (c | 32'h8000_0000);
        end
    endfunction
    // v better than u: greater key, or equal key and lower row
    function automatic better(input [49:0] v, input [49:0] u);
        better = okey(v[48:17]) > okey(u[48:17]) || (okey(v[48:17]) == okey(u[48:17]) && v[16:0] < u[16:0]);
    endfunction
    // level 1: pair = max(iw, ie) (held values are stable from `have` until the next go)
    (* keep *) reg [2:0] sa_q;
    reg [49:0] pr;
    always @(posedge ck) sa_q <= {3{better(h[2], h[1])}};
    always @(posedge ck) begin
        pr[16:0]  <= sa_q[0] ? h[2][16:0]  : h[1][16:0];
        pr[32:17] <= sa_q[1] ? h[2][32:17] : h[1][32:17];
        pr[48:33] <= sa_q[2] ? h[2][48:33] : h[1][48:33];
        pr[49]    <= h[0][49] | h[1][49] | h[2][49];
    end
    // level 2: max(pair, i); pr is valid from 2 edges after the last capture
    (* keep *) reg [2:0] sb_q;
    reg [49:0] o_r;
    reg        o_rv;
    always @(posedge ck) sb_q <= {3{better(h[0], pr)}};
    always @(posedge ck) begin
        o_r[16:0]  <= sb_q[0] ? h[0][16:0]  : pr[16:0];
        o_r[32:17] <= sb_q[1] ? h[0][32:17] : pr[32:17];
        o_r[48:33] <= sb_q[2] ? h[0][48:33] : pr[48:33];
        o_r[49]    <= pr[49];
    end
    // fire: ready at c -> sa_q (c) -> pr (c+1) -> sb_q (c+2) -> o_r (c+3); o_rv aligned
    reg s3_v;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin s3_v <= 1'b0; o_rv <= 1'b0; end
        else begin s3_v <= s2_v; o_rv <= s3_v; end
    assign o = {o_r[49], o_r[48:17], o_r[16:0], o_rv, xv_q, go_q, x_q};
endmodule
