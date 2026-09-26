`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Reducer of the V4.1 vector stream unit: lane-parallel, and exact under the
// arithmetic contract R-ARITH (tools/hdc_golden_v41.csum, HDC_V41_ARITH=chunk8).
//
// THE CONTRACT.  A sum over a segment of n elements (in element order) is cut
// into contiguous chunks of 8.  Each chunk is summed sequentially from +0, and
// the chunk sums are added by a pairwise tree padded with +0 to a power of two.
//
// WHY THE LANES REPRODUCE IT.  The controller lays a segment out so that its
// element j sits at lane (j mod S) of the segment's slot, where S = 2^ls >= 8
// is the slot size: vector v of a spanning segment holds elements v*S ..
// v*S + S-1.  Chunk c of the segment is therefore lanes 8c' .. 8c'+7 of one
// vector, and the chunk sums of a slot form an ALIGNED subtree of the tree
// over the vector's N/8 chunk sums.
//   * Lanes past the segment's end carry +0.  x + (+0) = x exactly, because
//     every zero result is +0, so the padding changes nothing.
//   * A packed slot (S >= the segment length) is its segment's padded tree,
//     read at tree level log2(S/8).  A larger S only adds +0 leaves.
//   * A spanning segment (nv > 1 vectors of S = the vector width) adds its
//     vector sums, in time, by a streaming binary counter.  Level t holds a
//     left operand until its right sibling arrives.  The segment's LAST item
//     combines with a held operand or passes (its sibling is the +0 padding).
//     So every level sums aligned pairs, and the result is the tree over the
//     vector sums padded to 2^ceil(log2 nv).  That is exactly the golden's
//     top ceil(log2 nv) levels; IEEE addition commutes, so a+b = b+a.
// MAX uses the same structure with max for +, and pads with -inf.
//
// Pipeline, from the retiring vector (every stage one vector a cycle):
//   IN     1  the out values and the lanes' liveness
//   SQ     3  out*out (red_sq), else a delay
//   CHAIN 21  per chunk, 7 chained ops, lane 8c+j delayed 3(j-1)
//   TREE   3  per level, log2(N/8) levels; packed results are tapped at level lt
//   TIME   3  per level, L = ceil(log2 nv) levels, for spanning segments only
//   OUT    1  result register: NR = N/8 result slots, slot k at rbase + (k << rsh)
// A packed result leaves at 26 + 3 lt after the retire; a spanning segment's
// result leaves 26 + 3 lt + 3 L after its last vector retires.  Different taps
// and different L merge at the result port.  The controller orders results
// across ops there (checkpoint R), and orders spanning ops at the TIME input
// (checkpoint T).
// ---------------------------------------------------------------------------
module ot_hdc_v41x_vred_op (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire        mx,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output wire [31:0] y,
    output wire        fault
);
    function automatic [31:0] okey(input [31:0] x);
        okey = x[31] ? ~x : {1'b1, x[30:0]};
    endfunction
    wire [31:0] ys, ym;
    wire mxd;
    ot_hdc_qadd u_add (clk, rst_n, v && !mx, a, b, ys, fault);
    ot_hdc_delay #(.W(33), .D(3)) u_m (.clk(clk), .rst_n(rst_n), .d({mx, (okey(a) >= okey(b)) ? a : b}),
                                      .q({mxd, ym}));
    assign y = mxd ? ym : ys;
endmodule

module ot_hdc_v41x_vec_red #(
    parameter integer N  = 64,          // lanes, a power of two >= 8
    parameter integer LV = 6,           // time levels: spanning segments of up to 2^LV vectors
    parameter integer AW = 24,
    parameter integer MW = 64           // meta carried with an item (opaque here, returned with its result)
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire            v_in,        // a retiring vector of a reducing op
    input  wire [N*32-1:0] x_in,
    input  wire [N-1:0]    live_in,
    input  wire            mx_in,       // MAX (else SUM)
    input  wire            sq_in,
    input  wire [3:0]      lt_in,       // tap level: log2(S/8)
    input  wire            span_in,     // the segment spans vectors: go through TIME
    input  wire [2:0]      l_in,        // TIME levels of the segment
    input  wire            last_in,     // the segment's last vector
    input  wire [7:0]      nres_in,     // packed: result slots 0 .. nres-1 hold segments
    input  wire            rnd_in,
    input  wire [AW-1:0]   rbase_in,
    input  wire [4:0]      rsh_in,
    input  wire [MW-1:0]   meta_in,
    output reg  [N/8-1:0]  o_we,
    output reg  [N/8*AW-1:0] o_addr,
    output reg  [N/8*32-1:0] o_data,
    output reg  [MW-1:0]   o_meta,
    output reg             o_ev,        // a result event (any slot)
    output wire            busy,
    output reg             fault
);
    localparam integer NC = N / 8;
    localparam integer LC = $clog2(NC);          // tree levels
    localparam integer TAG = 1 + 4 + 1 + 3 + 1 + 8 + 1 + AW + 5 + MW;
    function automatic [31:0] bf16(input [31:0] x);
        bf16 = (x + 32'h7FFF + {31'd0, x[16]}) & 32'hFFFF0000;
    endfunction

    // -- IN ---------------------------------------------------------------------------------
    reg  [N*32-1:0] i_x;
    reg  [N-1:0]    i_live;
    reg             i_v, i_sq;
    reg  [TAG-1:0]  i_t;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) i_v <= 1'b0; else i_v <= v_in;
    end
    always @(posedge clk) begin
        i_x <= x_in; i_live <= live_in; i_sq <= sq_in;
        i_t <= {mx_in, lt_in, span_in, l_in, last_in, nres_in, rnd_in, rbase_in, rsh_in, meta_in};
    end
    wire i_mx = i_t[TAG-1];
    // -- SQ, then the padding -----------------------------------------------------------------
    wire [N*32-1:0] xsq, xd;
    wire [N-1:0]    fsq;
    genvar l;
    generate for (l = 0; l < N; l = l + 1) begin : g_sq
        ot_hdc_qmul u_sq (clk, rst_n, i_v && i_sq && i_live[l], i_x[32*l +: 32], i_x[32*l +: 32], xsq[32*l +: 32],
                          fsq[l]);
    end endgenerate
    wire [N-1:0]   q_live;
    wire [TAG-1:0] q_t;
    wire           q_sq;
    ot_hdc_delay #(.W(N*32 + N + TAG + 1), .D(3)) u_sqd (.clk(clk), .rst_n(rst_n),
        .d({i_x, i_live, i_t, i_sq}), .q({xd, q_live, q_t, q_sq}));
    wire [3:0] vq;
    ot_hdc_vline #(.D(3)) u_vq (.clk(clk), .rst_n(rst_n), .v(i_v), .vd(vq));
    wire q_mx = q_t[TAG-1];
    wire [N*32-1:0] c_x;
    generate for (l = 0; l < N; l = l + 1) begin : g_pad
        assign c_x[32*l +: 32] = !q_live[l] ? (q_mx ? 32'hFF800000 : 32'd0) :
                                 q_sq ? xsq[32*l +: 32] : xd[32*l +: 32];
    end endgenerate
    wire c_v = vq[3];

    // -- CHAIN: chunk c = lanes 8c .. 8c+7, sequential ------------------------------------------
    wire [NC*32-1:0] chunk;
    wire [NC*7-1:0]  fch;
    wire [21:0]      vch, mxl;
    ot_hdc_vline #(.D(21)) u_vch (.clk(clk), .rst_n(rst_n), .v(c_v), .vd(vch));
    ot_hdc_vline #(.D(21)) u_mxl (.clk(clk), .rst_n(rst_n), .v(c_v && q_mx), .vd(mxl));
    genvar c, j;
    generate for (c = 0; c < NC; c = c + 1) begin : g_chunk
        wire [32*8-1:0] acc;
        assign acc[31:0] = c_x[32*(8*c) +: 32];
        for (j = 1; j < 8; j = j + 1) begin : g_step
            wire [31:0] xj;
            ot_hdc_delay #(.W(32), .D(3 * (j - 1))) u_xd (.clk(clk), .rst_n(rst_n),
                .d(c_x[32*(8*c + j) +: 32]), .q(xj));
            ot_hdc_v41x_vred_op u_op (.clk(clk), .rst_n(rst_n), .v(vch[3 * (j - 1)]), .mx(mxl[3 * (j - 1)]),
                .a(acc[32*(j-1) +: 32]), .b(xj), .y(acc[32*j +: 32]), .fault(fch[7*c + j - 1]));
        end
        assign chunk[32*c +: 32] = acc[32*7 +: 32];
    end endgenerate
    wire [TAG-1:0] ct;
    ot_hdc_delay #(.W(TAG), .D(21)) u_ct (.clk(clk), .rst_n(rst_n), .d(q_t), .q(ct));

    // -- TREE ---------------------------------------------------------------------------------------
    wire [NC*32-1:0] lvl [0:LC];
    wire [LC:0]      tv;
    wire [TAG-1:0]   tt [0:LC];
    wire [LC:0]      tf;
    wire [LC:0]      tb;
    assign lvl[0] = chunk;
    assign tv[0] = vch[21];
    assign tt[0] = ct;
    assign tf[0] = 1'b0;
    assign tb[0] = 1'b0;
    genvar lv, p;
    generate for (lv = 1; lv <= LC; lv = lv + 1) begin : g_tree
        wire [(NC >> lv)-1:0] pf;
        wire [3:0] vd;
        ot_hdc_vline #(.D(3)) u_vd (.clk(clk), .rst_n(rst_n), .v(tv[lv-1]), .vd(vd));
        wire [TAG-1:0] td;
        ot_hdc_delay #(.W(TAG), .D(3)) u_td (.clk(clk), .rst_n(rst_n), .d(tt[lv-1]), .q(td));
        wire [NC*32-1:0] q;
        for (p = 0; p < (NC >> lv); p = p + 1) begin : g_pair
            ot_hdc_v41x_vred_op u_op (.clk(clk), .rst_n(rst_n), .v(tv[lv-1]), .mx(tt[lv-1][TAG-1]),
                .a(lvl[lv-1][32*(2*p) +: 32]), .b(lvl[lv-1][32*(2*p+1) +: 32]), .y(q[32*p +: 32]), .fault(pf[p]));
        end
        assign q[NC*32-1 : (NC >> lv)*32] = 0;
        assign lvl[lv] = q;
        assign tv[lv] = vd[3];
        assign tt[lv] = td;
        assign tf[lv] = |pf;
        assign tb[lv] = |vd[2:0];
    end endgenerate

    // -- taps: the item at level j with lt == j --------------------------------------------------------
    // tag fields
    reg  [LC:0] hit;
    integer h;
    always @(*) for (h = 0; h <= LC; h = h + 1) hit[h] = tv[h] && (tt[h][TAG-2 -: 4] == h);
    reg  [NC*32-1:0] tap_x;
    reg  [TAG-1:0]   tap_t;
    reg              tap_v;
    always @(*) begin
        tap_v = 1'b0; tap_x = {NC*32{1'b0}}; tap_t = {TAG{1'b0}};
        for (h = 0; h <= LC; h = h + 1) if (hit[h]) begin tap_v = 1'b1; tap_x = lvl[h]; tap_t = tt[h]; end
    end
    wire pk_v = tap_v && !tap_t[TAG-6];
    wire tm_v = tap_v && tap_t[TAG-6];
    wire tap_multi = ($countones(hit) > 1);

    // -- TIME ------------------------------------------------------------------------------------------
    wire [31:0]    sv [0:LV];
    wire [LV:0]    sval;
    wire [TAG-1:0] st [0:LV];
    wire [LV:0]    sf, sb, sx;               // sx: an item leaving at level t as a result
    assign sv[0] = tap_x[31:0];
    assign sval[0] = tm_v;
    assign st[0] = tap_t;
    assign sf[0] = 1'b0;
    assign sb[0] = 1'b0;
    assign sx[0] = 1'b0;
    genvar t;
    generate for (t = 1; t <= LV; t = t + 1) begin : g_time
        wire [31:0]    in_x = sv[t-1];
        wire           in_v = sval[t-1] && !sx[t-1];
        wire [TAG-1:0] in_t = st[t-1];
        wire           in_last = in_t[TAG-10];
        reg  [31:0] held;
        reg         held_v;
        wire pair = in_v && held_v;
        wire pass = in_v && !held_v && in_last;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) held_v <= 1'b0;
            else if (pair) held_v <= 1'b0;
            else if (in_v && !pass) held_v <= 1'b1;
        end
        always @(posedge clk) if (in_v && !held_v && !pass) held <= in_x;
        wire [31:0] s, pd;
        wire f;
        ot_hdc_v41x_vred_op u_op (.clk(clk), .rst_n(rst_n), .v(pair), .mx(in_t[TAG-1]), .a(held), .b(in_x),
                                  .y(s), .fault(f));
        wire [TAG+1-1:0] od;
        ot_hdc_delay #(.W(TAG + 1 + 32), .D(3)) u_od (.clk(clk), .rst_n(rst_n), .d({in_t, pair, in_x}), .q({od, pd}));
        wire [3:0] vd;
        ot_hdc_vline #(.D(3)) u_vd (.clk(clk), .rst_n(rst_n), .v(pair || pass), .vd(vd));
        assign sv[t] = od[0] ? s : pd;
        assign sval[t] = vd[3];
        assign st[t] = od[TAG:1];
        assign sx[t] = vd[3] && od[TAG:1][TAG-10] && (od[TAG:1][TAG-7 -: 3] == t);
        assign sf[t] = f;
        assign sb[t] = held_v || (|vd[2:0]);
    end endgenerate
    // an item that leaves the top without being a result: its segment was longer than 2^LV vectors
    wire top_bad = sval[LV] && !sx[LV];
    reg  [LV:0] xs;
    integer e;
    reg  [31:0]   tr_x;
    reg  [TAG-1:0] tr_t;
    reg           tr_v;
    always @(*) begin
        tr_v = 1'b0; tr_x = 32'd0; tr_t = {TAG{1'b0}};
        for (e = 1; e <= LV; e = e + 1) if (sx[e]) begin tr_v = 1'b1; tr_x = sv[e]; tr_t = st[e]; end
    end
    wire res_multi = (pk_v && tr_v) || ($countones(sx) > 1);

    // -- OUT --------------------------------------------------------------------------------------------
    integer k;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin o_we <= 0; o_ev <= 1'b0; fault <= 1'b0; end
        else begin
            for (k = 0; k < NC; k = k + 1)
                o_we[k] <= pk_v ? (k < tap_t[TAG-11 -: 8]) : (tr_v && k == 0);
            o_ev <= pk_v || tr_v;
            fault <= (|fsq) || (|fch) || (|tf) || (|sf) || top_bad || tap_multi || res_multi;
        end
    end
    always @(posedge clk) begin
        for (k = 0; k < NC; k = k + 1) begin
            o_addr[k*AW +: AW] <= pk_v ? tap_t[TAG-20 -: AW] + (k << tap_t[TAG-20-AW -: 5]) : tr_t[TAG-20 -: AW];
            o_data[32*k +: 32] <= pk_v ? (tap_t[TAG-19] ? bf16(tap_x[32*k +: 32]) : tap_x[32*k +: 32])
                                       : (tr_t[TAG-19] ? bf16(tr_x) : tr_x);
        end
        o_meta <= pk_v ? tap_t[MW-1:0] : tr_t[MW-1:0];
    end
    assign busy = i_v || (|vq) || (|vch) || (|tv) || (|tb) || (|sval) || (|sb) || (|o_we);
endmodule
