`timescale 1ns/1ps
// QW-SLICE6-SCRED 10-19 (opt-in fallback qfd_dv_s5_redb, +define+OT_S5_RED_RING in qfd_dv_s5_red): rtl/hdc/ot_hdc_vreduce.sv
// (ot_hdc_vred_op + ot_hdc_vreduce, renamed) with every data delay line of depth >= 3 (SAFE-DESIGN item 5: the lane skew
// lines u_xd up to 18 deep, the squaring / tag / output lines) built as a flop RING (qfd_dv_s5r_flop_ring: one write
// slot per edge, the same slot read D - 1 edges later into one output flop = age D) instead of a flop -> flop shift
// chain.  Same ages, same values: cycle-exact with ot_hdc_vreduce.  The 1-bit valid taps (ot_hdc_vline) stay lines
// (their every tap is read).  6 delay instances converted; the source module is untouched.
module qfd_dv_s5_rdelay #(parameter integer W = 32, parameter integer D = 1, parameter integer RESET = 0) (
    input wire clk, input wire rst_n, input wire [W-1:0] d, output wire [W-1:0] q
);
    generate if (D >= 3 && RESET == 0 && W * (D - 1) <= 2048) begin : g_ring
        qfd_dv_s5r_flop_ring #(.W(W), .D(D)) u_r (.clk(clk), .rbr(rst_n), .d(d), .q(q));
    end else if (D >= 3 && RESET == 0) begin : g_split   // wide line: 64-bit ring slices
        localparam integer NSL = (W + 63) / 64;
        for (genvar k = 0; k < NSL; k = k + 1) begin : g_s
            localparam integer SW = (W - 64 * k < 64) ? W - 64 * k : 64;
            qfd_dv_s5r_flop_ring #(.W(SW), .D(D)) u_r (.clk(clk), .rbr(rst_n), .d(d[64*k +: SW]), .q(q[64*k +: SW]));
        end
    end else begin : g_line
        ot_hdc_delay #(.W(W), .D(D), .RESET(RESET)) u_d (.clk(clk), .rst_n(rst_n), .d(d), .q(q));
    end endgenerate
endmodule

module qfd_dv_s5_vred_op_rb #(
    parameter integer LA = 3
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire        mx,         // 1: max, 0: add
    input  wire [31:0] a,
    input  wire [31:0] b,
    output wire [31:0] y,
    output wire        fault
);
    function automatic [31:0] okey(input [31:0] x);
        okey = x[31] ? ~x : {1'b1, x[30:0]};
    endfunction
    wire [31:0] ys, ym;
    wire f, mxd;
    ot_hdc_qadd u_add (clk, rst_n, v && !mx, a, b, ys, f);
    qfd_dv_s5_rdelay #(.W(33), .D(LA)) u_m (.clk(clk), .rst_n(rst_n),
        .d({mx, (okey(a) >= okey(b)) ? a : b}), .q({mxd, ym}));
    assign y = mxd ? ym : ys;
    assign fault = f;
endmodule

module qfd_dv_s5_vreduce_rb #(
    parameter integer SW = 8,          // lanes, a multiple of 8
    parameter integer LV = 4,          // time levels: segments of up to 2^LV vectors
    parameter integer AW = 24
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire            v_in,       // a vector of the reduction
    input  wire            mx_in,      // MAX (else SUM)
    input  wire            sq_in,      // reduce x*x
    input  wire            last_in,    // the segment's last vector
    input  wire [AW-1:0]   addr_in,    // result address (with the last vector)
    input  wire [SW*32-1:0] x_in,      // elements; past the segment: +0 (SUM) or a real element (MAX)
    output reg             o_we,
    output reg  [AW-1:0]   o_addr,
    output reg  [31:0]     o_data,
    output wire            busy,
    output reg             fault
);
    localparam integer LA = 3, LM = 3;       // ot_hdc_qadd / ot_hdc_qmul
    localparam integer CD = 7 * LA;          // the 8-element chain
    localparam integer NC = SW / 8;
    localparam integer LC = $clog2(NC);
    localparam integer TAG = 1 + 1 + AW;   // mx, last, addr

    // -- SQ: every element takes the squaring stage (fixed depth) ------------------
    wire [SW*32-1:0] xsq, xd;
    wire [SW-1:0]    fsq;
    genvar l;
    generate for (l = 0; l < SW; l = l + 1) begin : g_sq
        ot_hdc_qmul u_sq (clk, rst_n, v_in && sq_in, x_in[32*l +: 32], x_in[32*l +: 32], xsq[32*l +: 32], fsq[l]);
    end endgenerate
    wire [SW*32-1:0] xq;
    wire [TAG-1:0]   tq;
    wire             vq, sqq;
    qfd_dv_s5_rdelay #(.W(SW*32 + TAG + 1), .D(LM)) u_sqd (.clk(clk), .rst_n(rst_n),
        .d({x_in, mx_in, last_in, addr_in, sq_in}), .q({xd, tq, sqq}));
    wire [LM:0] vqs;
    ot_hdc_vline #(.D(LM)) u_vq (.clk(clk), .rst_n(rst_n), .v(v_in), .vd(vqs));
    reg  [SW*32-1:0] c_x;
    reg  [TAG-1:0]   c_t;
    reg              c_v;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) c_v <= 1'b0;
        else c_v <= vqs[LM];
    end
    always @(posedge clk) begin
        c_x <= sqq ? xsq : xd;
        c_t <= tq;
    end
    wire c_mx = c_t[TAG-1];

    // -- CHAIN: chunk k = lanes 8k .. 8k+7, sequential from lane 8k -----------------
    wire [NC*32-1:0] chunk;
    wire [NC*7-1:0]  fch;
    wire [CD:0]      vch;
    ot_hdc_vline #(.D(CD)) u_vch (.clk(clk), .rst_n(rst_n), .v(c_v), .vd(vch));
    wire [CD:0] mxl;
    ot_hdc_vline #(.D(CD)) u_mxl (.clk(clk), .rst_n(rst_n), .v(c_v && c_mx), .vd(mxl));
    genvar k, j;
    generate for (k = 0; k < NC; k = k + 1) begin : g_chunk
        wire [32*8-1:0] acc;                 // acc[j]: after element j joins
        assign acc[31:0] = c_x[32*(8*k) +: 32];
        for (j = 1; j < 8; j = j + 1) begin : g_step
            wire [31:0] xj;
            qfd_dv_s5_rdelay #(.W(32), .D(LA * (j - 1))) u_xd (.clk(clk), .rst_n(rst_n),
                .d(c_x[32*(8*k + j) +: 32]), .q(xj));
            qfd_dv_s5_vred_op_rb #(.LA(LA)) u_op (.clk(clk), .rst_n(rst_n), .v(vch[LA * (j - 1)]), .mx(mxl[LA * (j - 1)]),
                .a(acc[32*(j-1) +: 32]), .b(xj), .y(acc[32*j +: 32]), .fault(fch[7*k + j - 1]));
        end
        assign chunk[32*k +: 32] = acc[32*7 +: 32];
    end endgenerate
    wire [TAG-1:0] ct;
    qfd_dv_s5_rdelay #(.W(TAG), .D(CD)) u_ct (.clk(clk), .rst_n(rst_n), .d(c_t), .q(ct));
    wire cv = vch[CD];

    // -- TREE: pairwise over the vector's NC chunk sums ----------------------------------
    wire [NC*32-1:0] lvl [0:LC];
    wire [LC:0]      tv;
    wire [TAG-1:0]   tt [0:LC];
    wire [LC:0]      tf;
    wire [LC:0]      tvb;                    // a tree level's adders hold an item
    assign tvb[0] = 1'b0;
    assign lvl[0] = chunk;
    assign tv[0] = cv;
    assign tt[0] = ct;
    assign tf[0] = 1'b0;
    genvar lv, p;
    generate for (lv = 1; lv <= LC; lv = lv + 1) begin : g_tree
        wire [(NC >> lv)-1:0] pf;
        reg  [NC*32-1:0] q;
        wire [LA:0] vd;
        ot_hdc_vline #(.D(LA)) u_vd (.clk(clk), .rst_n(rst_n), .v(tv[lv-1]), .vd(vd));
        wire [TAG-1:0] td;
        qfd_dv_s5_rdelay #(.W(TAG), .D(LA)) u_td (.clk(clk), .rst_n(rst_n), .d(tt[lv-1]), .q(td));
        for (p = 0; p < (NC >> lv); p = p + 1) begin : g_pair
            wire [31:0] s;
            qfd_dv_s5_vred_op_rb #(.LA(LA)) u_op (.clk(clk), .rst_n(rst_n), .v(tv[lv-1]), .mx(tt[lv-1][TAG-1]),
                .a(lvl[lv-1][32*(2*p) +: 32]), .b(lvl[lv-1][32*(2*p+1) +: 32]), .y(s), .fault(pf[p]));
            always @(posedge clk) q[32*p +: 32] <= s;
        end
        if ((NC >> lv) < NC) begin : g_rest
            always @(posedge clk) q[NC*32-1 : (NC >> lv)*32] <= 0;
        end
        reg rv;
        reg [TAG-1:0] rt;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) rv <= 1'b0;
            else rv <= vd[LA];
        end
        always @(posedge clk) rt <= td;
        assign lvl[lv] = q;
        assign tv[lv] = rv;
        assign tt[lv] = rt;
        assign tf[lv] = |pf;
        assign tvb[lv] = |vd;
    end endgenerate

    // -- TIME: pair the segment's vector sums --------------------------------------------
    wire [31:0]    sv [0:LV];
    wire [LV:0]    sval;
    wire [TAG-1:0] st [0:LV];
    wire [LV:0]    sf;
    wire [LV:0]    tb;                     // a level's op or pass line holds an item
    assign tb[0] = 1'b0;
    assign sv[0] = lvl[LC][31:0];
    assign sval[0] = tv[LC];
    assign st[0] = tt[LC];
    assign sf[0] = 1'b0;
    genvar t;
    generate for (t = 1; t <= LV; t = t + 1) begin : g_time
        wire [31:0] in_x = sv[t-1];
        wire        in_v = sval[t-1];
        wire [TAG-1:0] in_t = st[t-1];
        wire        in_last = in_t[TAG-2];
        reg  [31:0] held;
        reg         held_v;
        //: pair: held (left) with the new item (right); pass: a LAST item with no
        //: held left sibling (its right sibling is +0); hold: otherwise
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
        qfd_dv_s5_vred_op_rb #(.LA(LA)) u_op (.clk(clk), .rst_n(rst_n), .v(pair), .mx(in_t[TAG-1]), .a(held),
                                        .b(in_x), .y(s), .fault(f));
        wire [TAG+2-1:0] od;
        qfd_dv_s5_rdelay #(.W(TAG + 2 + 32), .D(LA)) u_od (.clk(clk), .rst_n(rst_n),
            .d({in_t, pair, pass, in_x}), .q({od, pd}));
        wire [LA:0] vd;
        ot_hdc_vline #(.D(LA)) u_vd (.clk(clk), .rst_n(rst_n), .v(pair || pass), .vd(vd));
        reg  [31:0] q;
        reg         qv;
        reg  [TAG-1:0] qt;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) qv <= 1'b0;
            else qv <= vd[LA];
        end
        always @(posedge clk) begin
            q <= od[1] ? s : pd;               // od = {tag, pair, pass}
            qt <= od[TAG+1 -: TAG];
        end
        assign sv[t] = q;
        assign sval[t] = qv;
        assign st[t] = qt;
        assign sf[t] = f;
        assign tb[t] = |vd;
    end endgenerate

    // -- result ------------------------------------------------------------------------------
    wire top_last = st[LV][TAG-2];
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin o_we <= 1'b0; fault <= 1'b0; end
        else begin
            o_we <= sval[LV] && top_last;
            fault <= (|fsq) || (|fch) || (|tf) || (|sf) || (sval[LV] && !top_last);
        end
    end
    always @(posedge clk) begin
        o_addr <= st[LV][AW-1:0];
        o_data <= sv[LV];
    end
    assign busy = (|vqs) || c_v || (|vch) || (|tv) || (|tvb) || (|sval) || (|tb) || o_we;
endmodule

// copied from rtl/qwen_dv/qfd_dv_head_safe1.sv (QW-CLUSTER3/HEAD safe2 flop ring, closed in qfd_dv_lane_h_safe2), renamed s1 -> s5r
(* keep_hierarchy *)
module qfd_dv_s5r_rst_relay (input wire clk, input wire arst_n, output reg q);
    always @(posedge clk or negedge arst_n) if (!arst_n) q <= 1'b0; else q <= 1'b1;
endmodule
module qfd_dv_s5r_flop_ring #(parameter integer W = 32, D = 3) (
    input wire clk, rbr, input wire [W-1:0] d, output wire [W-1:0] q
);
    localparam integer N = D - 1, PB = (N < 2) ? 1 : $clog2(N);
    localparam integer NS = (W + 15) / 16, SPL = 32 / PB, NLF = (NS + SPL - 1) / SPL;
    wire [NLF-1:0] lf;
    genvar k;
    for (k = 0; k < NLF; k = k + 1) begin : g_lf
        qfd_dv_s5r_rst_relay u_r (.clk(clk), .arst_n(rbr), .q(lf[k]));
    end
    for (k = 0; k < NS; k = k + 1) begin : g_sl
        localparam integer SW = (W - 16 * k < 16) ? W - 16 * k : 16;
        qfd_dv_s5r_ring_slice #(.W(SW), .N(N)) u_s (.clk(clk), .rst_n(lf[k / SPL]), .d(d[16*k +: SW]), .q(q[16*k +: SW]));
    end
`ifndef SYNTHESIS
    initial if (D < 3 || D > 33 || W * (D - 1) > 2048) $fatal(1, "S1_FLOP_RING unsupported shape W %0d D %0d", W, D);
`endif
endmodule
(* keep_hierarchy *)
module qfd_dv_s5r_ring_slice #(parameter integer W = 16, N = 4) (
    input wire clk, rst_n, input wire [W-1:0] d, output reg [W-1:0] q
);
    localparam integer PB = (N < 2) ? 1 : $clog2(N);
    reg [PB-1:0] p;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) p <= 0; else p <= (p == N - 1) ? {PB{1'b0}} : p + 1'b1;
    reg [W*N-1:0] slot;
    wire [W*(N+1)-1:0] rd;
    assign rd[W-1:0] = {W{1'b0}};
    genvar j;
    for (j = 0; j < N; j = j + 1) begin : g_slot
        wire sel = (p == j);
        always @(posedge clk) if (sel) slot[W*j +: W] <= d;
        assign rd[W*(j+1) +: W] = rd[W*j +: W] | ({W{sel}} & slot[W*j +: W]);
    end
`ifdef OT_S5R_RING_AGE_MUT
    always @(posedge clk) q <= rd[W*N +: W] ^ {{(W-1){1'b0}}, (p == 0)};
`else
    always @(posedge clk) q <= rd[W*N +: W];
`endif
endmodule
