`timescale 1ns/1ps
// =====================================================================================================================
// QW-SLICE7-LEAVES 10-20: qfd_dv_s5_red2 -- structural successor of qfd_dv_s5_red / redb (Q.STA.SLICE.2), originals
// untouched.  Same ports, same values, same order (R-ARITH reduce_chunked contract of ot_hdc_vreduce); what changes:
//   * FP add / mul are the bit-identical ot_hdc_fp32_add_lat #(LA) / ot_hdc_fp32_mul_lat #(LM) with DRST 0 (only valid
//     bits reset; data stages are plain flops), LA 4 / LM 5 by default (was the LA 3 / LM 3 fast units: red 813 ps,
//     redb 775 ps TT stage > 600 ps SAFE limit).
//   * Every data delay line >= 3 deep is the exact-age kept ring qfd_dv_s5_red_ring32 (no long flop->flop chains).
//   * Every input pin lands in one face register here and every output leaves from a face register here (the kit's
//     flow pin wrapper is OFF, so the edge count equals the old kit's pin_regs in+1 / out+1).
//   * Fanout (reset relays, sq / mx / lane selects) is bounded to <= 32 by the constructor
//     (tools/qwen_dv/bound_math_netlist.py) on this source -> qfd_dv_s5_red2_bounded; the census is on that netlist.
// PRICE vs the old kit qfd_dv_s5_red (bare module + pin regs): red_we / red_addr / red_data / fault later by
//   (LM - 3) + 7 * (LA - 3) + LV * (LA - 3) = 2 + 7 + 4 = 13 edges per reduction result (LA 4, LM 5, LV 4);
//   rd_v unchanged; busy is the registered busy of the deeper pipe.  Boot only: ring phase reset release +2 edges.
// OT_S5_RED2_MUT: SUM taken as MAX (bench witness, must FAIL).
// =====================================================================================================================

// Fixed delay: D < 3 a plain register line, D >= 3 the kept exact-age ring (data only; rstn_i = landed active-low reset).
module qfd_dv_s5_dly2 #(parameter integer W = 32, parameter integer D = 1, parameter integer ID = 0) (
    input  wire         ck,
    input  wire         rstn_i,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    generate
        if (D < 3) begin : g_line
            ot_hdc_delay #(.W(W), .D(D)) u (.clk(ck), .rst_n(rstn_i), .d(d), .q(q));
        end else if (W <= 283 && W * (D - 2) <= 2048) begin : g_ring
            qfd_dv_s5_red_ring32 #(.W(W), .D(D), .ID(ID)) u (.ck(ck), .reset_i(rstn_i), .d(d), .q(q));
        end else begin : g_split
            // wide line: independent rings of <= 64 bits (each its own <= 2 kb store, own kept phases)
            localparam integer NS = (W + 63) / 64;
            genvar s;
            for (s = 0; s < NS; s = s + 1) begin : g_s
                localparam integer B = (W - 64 * s < 64) ? W - 64 * s : 64;
                qfd_dv_s5_red_ring32 #(.W(B), .D(D), .ID(ID * 16 + s)) u (.ck(ck), .reset_i(rstn_i),
                    .d(d[64*s +: B]), .q(q[64*s +: B]));
            end
        end
    endgenerate
endmodule

module ot_hdc_vred_op2 #(parameter integer LA = 4, parameter integer ID = 0) (
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
    wire [1:0] err;
    wire vo, mxd;
    ot_hdc_fp32_add_lat #(.LAT(LA), .DRST(0)) u_add (.clk(clk), .rst_n(rst_n), .valid_in(v && !mx), .a(a), .b(b),
        .y(ys), .err(err), .valid_out(vo));
    qfd_dv_s5_dly2 #(.W(33), .D(LA), .ID(ID)) u_m (.ck(clk), .rstn_i(rst_n),
        .d({mx, (okey(a) >= okey(b)) ? a : b}), .q({mxd, ym}));
    assign y = mxd ? ym : ys;
    assign fault = vo && (err != 2'd0);
endmodule

module ot_hdc_vreduce2 #(
    parameter integer SW = 8,
    parameter integer LV = 4,
    parameter integer AW = 24,
    parameter integer LA = 4,
    parameter integer LM = 5
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire            v_in,
    input  wire            mx_in,
    input  wire            sq_in,
    input  wire            last_in,
    input  wire [AW-1:0]   addr_in,
    input  wire [SW*32-1:0] x_in,
    output reg             o_we,
    output reg  [AW-1:0]   o_addr,
    output reg  [31:0]     o_data,
    output wire            busy,
    output reg             fault
);
    localparam integer CD = 7 * LA;
    localparam integer NC = SW / 8;
    localparam integer LC = $clog2(NC);
    localparam integer TAG = 1 + 1 + AW;

    // -- SQ ------------------------------------------------------------------------------------------
    wire [SW*32-1:0] xsq, xd;
    wire [SW-1:0]    fsq;
    genvar l;
    generate for (l = 0; l < SW; l = l + 1) begin : g_sq
        wire [1:0] e; wire vo;
        ot_hdc_fp32_mul_lat #(.LAT(LM), .DRST(0)) u_sq (.clk(clk), .rst_n(rst_n), .valid_in(v_in && sq_in),
            .a(x_in[32*l +: 32]), .b(x_in[32*l +: 32]), .y(xsq[32*l +: 32]), .err(e), .valid_out(vo));
        assign fsq[l] = vo && (e != 2'd0);
    end endgenerate
    wire [TAG-1:0]   tq;
    wire             sqq;
    // element lanes and the tag/sq line delayed LM (per-lane rings: each <= 2 kb, own phases)
    generate for (l = 0; l < SW; l = l + 1) begin : g_xd
        qfd_dv_s5_dly2 #(.W(32), .D(LM), .ID(100 + l)) u_xd (.ck(clk), .rstn_i(rst_n), .d(x_in[32*l +: 32]), .q(xd[32*l +: 32]));
    end endgenerate
    qfd_dv_s5_dly2 #(.W(TAG + 1), .D(LM), .ID(120)) u_sqd (.ck(clk), .rstn_i(rst_n),
        .d({mx_in, last_in, addr_in, sq_in}), .q({tq, sqq}));
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

    // -- CHAIN --------------------------------------------------------------------------------------
    wire [NC*32-1:0] chunk;
    wire [NC*7-1:0]  fch;
    wire [CD:0]      vch;
    ot_hdc_vline #(.D(CD)) u_vch (.clk(clk), .rst_n(rst_n), .v(c_v), .vd(vch));
    wire [CD:0] mxl;
    ot_hdc_vline #(.D(CD)) u_mxl (.clk(clk), .rst_n(rst_n), .v(c_v && c_mx), .vd(mxl));
    genvar k, j;
    generate for (k = 0; k < NC; k = k + 1) begin : g_chunk
        wire [32*8-1:0] acc;
        assign acc[31:0] = c_x[32*(8*k) +: 32];
        for (j = 1; j < 8; j = j + 1) begin : g_step
            wire [31:0] xj;
            qfd_dv_s5_dly2 #(.W(32), .D(LA * (j - 1)), .ID(200 + 8 * k + j)) u_xd (.ck(clk), .rstn_i(rst_n),
                .d(c_x[32*(8*k + j) +: 32]), .q(xj));
            ot_hdc_vred_op2 #(.LA(LA), .ID(300 + 8 * k + j)) u_op (.clk(clk), .rst_n(rst_n), .v(vch[LA * (j - 1)]),
                .mx(mxl[LA * (j - 1)]), .a(acc[32*(j-1) +: 32]), .b(xj), .y(acc[32*j +: 32]), .fault(fch[7*k + j - 1]));
        end
        assign chunk[32*k +: 32] = acc[32*7 +: 32];
    end endgenerate
    wire [TAG-1:0] ct;
    qfd_dv_s5_dly2 #(.W(TAG), .D(CD), .ID(400)) u_ct (.ck(clk), .rstn_i(rst_n), .d(c_t), .q(ct));
    wire cv = vch[CD];

    // -- TREE -----------------------------------------------------------------------------------------
    wire [NC*32-1:0] lvl [0:LC];
    wire [LC:0]      tv;
    wire [TAG-1:0]   tt [0:LC];
    wire [LC:0]      tf;
    wire [LC:0]      tvb;
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
        qfd_dv_s5_dly2 #(.W(TAG), .D(LA), .ID(500 + lv)) u_td (.ck(clk), .rstn_i(rst_n), .d(tt[lv-1]), .q(td));
        for (p = 0; p < (NC >> lv); p = p + 1) begin : g_pair
            wire [31:0] s;
            ot_hdc_vred_op2 #(.LA(LA), .ID(600 + 16 * lv + p)) u_op (.clk(clk), .rst_n(rst_n), .v(tv[lv-1]),
                .mx(tt[lv-1][TAG-1]), .a(lvl[lv-1][32*(2*p) +: 32]), .b(lvl[lv-1][32*(2*p+1) +: 32]), .y(s), .fault(pf[p]));
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

    // -- TIME -----------------------------------------------------------------------------------------
    wire [31:0]    sv [0:LV];
    wire [LV:0]    sval;
    wire [TAG-1:0] st [0:LV];
    wire [LV:0]    sf;
    wire [LV:0]    tb;
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
        ot_hdc_vred_op2 #(.LA(LA), .ID(700 + t)) u_op (.clk(clk), .rst_n(rst_n), .v(pair), .mx(in_t[TAG-1]), .a(held),
                                        .b(in_x), .y(s), .fault(f));
        wire [TAG+2-1:0] od;
        qfd_dv_s5_dly2 #(.W(TAG + 2 + 32), .D(LA), .ID(800 + t)) u_od (.ck(clk), .rstn_i(rst_n),
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
            q <= od[1] ? s : pd;
            qt <= od[TAG+1 -: TAG];
        end
        assign sv[t] = q;
        assign sval[t] = qv;
        assign st[t] = qt;
        assign sf[t] = f;
        assign tb[t] = |vd;
    end endgenerate

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

// ---------------------------------------------------------------------------------------------------------- red2 leaf
module qfd_dv_s5_red2 #(parameter integer LA = 4, parameter integer LM = 5) (
    input  wire           ck,
    input  wire           rst_n,
    input  wire [7:0]     l_ov,
    input  wire [8*32-1:0] l_out,
    input  wire [1:0]     l_red0,
    input  wire           l_redsq0,
    input  wire           l_last0,
    input  wire [23:0]    l_raddr0,
    output reg            red_we,
    output reg  [23:0]    red_addr,
    output reg  [31:0]    red_data,
    output reg            rd_v,
    output reg            busy,
    output reg            fault
);
    localparam integer SW = 8, AW = 24;
    wire rst;
    qfd_dv_s5_rst2 u_rl (.ck(ck), .rst_n(rst_n), .rst(rst));
    reg rc;
    always @(posedge ck or negedge rst) if (!rst) rc <= 1'b0; else rc <= 1'b1;
    wire rst_c = rc;
    // face input registers (no reset: data; validity is l_ov, reset through the face valid register)
    reg  [7:0]     f_ov;
    reg  [255:0]   f_out;
    reg  [1:0]     f_red0;
    reg            f_redsq0, f_last0;
    reg  [23:0]    f_raddr0;
    always @(posedge ck or negedge rst_c)
        if (!rst_c) f_ov <= 8'd0;
        else f_ov <= l_ov;
    always @(posedge ck) begin
        f_out <= l_out; f_red0 <= l_red0; f_redsq0 <= l_redsq0; f_last0 <= l_last0; f_raddr0 <= l_raddr0;
    end
    reg              q_v, rd_mx, rd_sq, rd_last;
    reg [AW-1:0]     rd_addr;
    reg [SW*32-1:0]  rd_x;
    integer li;
    always @(posedge ck or negedge rst_c) begin
        if (!rst_c) q_v <= 1'b0;
        else q_v <= f_ov[0] && f_red0 != 2'd0;
    end
    always @(posedge ck) begin
`ifdef OT_S5_RED2_MUT
        rd_mx <= (f_red0 == 2'd1); rd_sq <= f_redsq0; rd_last <= f_last0; rd_addr <= f_raddr0;
`else
        rd_mx <= (f_red0 == 2'd2); rd_sq <= f_redsq0; rd_last <= f_last0; rd_addr <= f_raddr0;
`endif
        for (li = 0; li < SW; li = li + 1)
            rd_x[32*li +: 32] <= f_ov[li] ? f_out[32*li +: 32] : (f_red0 == 2'd2) ? f_out[31:0] : 32'd0;
    end
    wire o_we, o_busy, o_fault;
    wire [AW-1:0] o_addr;
    wire [31:0] o_data;
    ot_hdc_vreduce2 #(.SW(SW), .LV(4), .AW(AW), .LA(LA), .LM(LM)) u_red (.clk(ck), .rst_n(rst_c), .v_in(q_v), .mx_in(rd_mx),
        .sq_in(rd_sq), .last_in(rd_last), .addr_in(rd_addr), .x_in(rd_x),
        .o_we(o_we), .o_addr(o_addr), .o_data(o_data), .busy(o_busy), .fault(o_fault));
    // face output registers
    always @(posedge ck or negedge rst_c)
        if (!rst_c) begin red_we <= 1'b0; rd_v <= 1'b0; busy <= 1'b0; fault <= 1'b0; end
        else begin red_we <= o_we; rd_v <= q_v; busy <= o_busy; fault <= o_fault; end
    always @(posedge ck) begin red_addr <= o_addr; red_data <= o_data; end
endmodule
