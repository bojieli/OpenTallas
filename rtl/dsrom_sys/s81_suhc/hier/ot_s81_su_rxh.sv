`timescale 1ns/1ps
// ot_s81_su_rxh (s81-romB3 2026-10-14): the RA / RB / QR stop of dsfd_sp_su_h as a hardened CLUSTER (the single
// rx tile, 16 softplus_s lanes + 32 QR lanes, did not synthesise within the 2700 s gate cap: one block).
// Children (each hardened once, every face registered on both sides):
//   ot_s81_su_rxc   control: the rxt down-tap pin flops, row numbering, parameter rows, RB adders, result rows -> the
//                   two write slots (ot_s81_su_rxt with the RA / QR lanes moved out; same control, same RB arithmetic)
//   ot_s81_su_rxra  L RA lanes (ot_hdc_v41x_softplus_s PCUT 1), 16 / L of them
//   ot_s81_su_rxqr  one QR row: 16 lanes (2 multiplies + 1 add, BF16 RNE), two of them (QR pair)
//   ot_s81_su_rxrb  the 16 RB adders (score + bias, ot_dsrom_qadd) as their own leaf (B6 s81-elemB 2026-10-14: the
//                   control leaf with the adders inside had 17,301 sinks, CTS 491 ps > the 15k / 300 ps clock rule);
//                   operands = the control's registered QR operand word xq_x = {bias, score} (no new issue flops),
//                   result captured at the control's pins (+3 cycles on RB: 108 -> 111 vs price 117.6)
// Arithmetic bit-identical to ot_s81_su_rxe (same units, same operands); the leaf faces add registers on the RA and
// QR result paths only (a job runs alone; the control counts result rows, not cycles).
module ot_s81_su_rxc #(
    parameter integer S_RD = 16, RAL = 16, LM = 5, LA = 4, XMUT = 0,
    parameter integer QW = 1                  // QR rope rows a cycle (2: rows j, j + 1 of a head on two read / write slots)
) (
    input  wire                   clk,
    input  wire                   rst_in,
    input  wire                   dn_st_i,
    input  wire [3:0]             dn_kind_i,
    input  wire [7:0]             dn_jid_i,
    input  wire [S_RD-1:0]        dn_v_i,
    input  wire [S_RD*512-1:0]    dn_d_i,
    output reg                    o_v,
    output reg  [13:0]            o_a,
    output reg  [15:0]            o_m,
    output reg  [511:0]           o_d,
    output reg                    o_v2,       // QW 2: the second QR result row (write slot W0 + 1)
    output reg  [13:0]            o_a2,
    output reg  [511:0]           o_d2,
    output reg                    o_fu, o_fo, o_alive, o_den, o_rdy,
    output reg  [7:0]             o_rjid,
    // RA / QR lane leaves (registered here, captured at the leaves' pins; results captured at these pins)
    output wire                   xa_v,
    output wire [511:0]           xa_x,
    input  wire                   xa_vi,
    input  wire [511:0]           xa_r,
    input  wire [3:0]             xa_f,
    output wire [1:0]             xq_v,
    output wire [1023:0]          xq_x,
    output wire [511:0]           xq_c,
    output wire [511:0]           xq_s,
    input  wire [1:0]             xq_vi,
    input  wire [1023:0]          xq_y,
    input  wire [3:0]             xq_f,       // one fault bit per QR lane leaf (2 rows x 2 leaves of 8 lanes)
    output wire                   xb_v,       // RB leaf issue (operands on xq_x = {bias, score})
    input  wire                   xb_vi,
    input  wire [511:0]           xb_y,
    input  wire                   xb_f
);
    localparam [3:0] K_RA = 8, K_RB = 9, K_QR = 10;
    localparam integer MAXP = 5;

    reg rr0, rr1;
    always @(posedge clk or negedge rst_in) if (!rst_in) begin rr0 <= 1'b0; rr1 <= 1'b0; end else begin rr0 <= 1'b1; rr1 <= rr0; end
    wire rst_n = rr1;

    // ------------------------------------------------------------------ pin flops (the down-spine tap)
    reg                dq_st;
    reg  [3:0]         dq_kind;
    reg  [S_RD-1:0]    dq_v;
    reg  [S_RD*512-1:0] dq_d;
    always @(posedge clk) begin dq_kind <= dn_kind_i; dq_d <= dn_d_i; end
    always @(posedge clk or negedge rst_n) if (!rst_n) begin dq_st <= 1'b0; dq_v <= 0; end
                                           else begin dq_st <= dn_st_i; dq_v <= dn_v_i; end

    // ------------------------------------------------------------------ rows of this cycle, numbered from the announce
    // (the descriptor + parameter rows may arrive several a cycle; operand rows arrive one a cycle)
    reg  [511:0] xin;                         // the operand row of this cycle
    reg  [511:0] xin2;                        // RB: the bias row arriving with its score row (pair issue)
    reg          xv, xtwo;
    reg  [15:0]  nrc;                         // rows of the job after this cycle
    reg  [15:0]  xidx;                        // the operand row's number from the announce
    reg  [S_RD-1:0]    sv;                    // slot s carries a parameter row
    reg  [S_RD*3-1:0]  sj;                    // ... its parameter index

    // ------------------------------------------------------------------ job context: rows numbered from the announce
    reg  [3:0]   jk;
    reg          mine;
    reg  [15:0]  rc;                          // rows of the job seen (descriptor + parameters, then operands)
    reg  [511:0] prow [0:MAXP-1];
    reg  [511:0] hold;                        // RB: the score row waiting for its bias row
    wire [3:0]   np = (jk == K_QR) ? 4'd5 : 4'd1;
    always @(*) begin : pick
        integer i;
        reg [15:0] c;
        xin = 512'd0; xin2 = 512'd0; xv = 1'b0; xtwo = 1'b0; xidx = 16'd0; sv = 0; sj = 0;
        c = rc;
        for (i = 0; i < S_RD; i = i + 1)
            if (dq_v[i]) begin
                if (c < np) begin sv[i] = 1'b1; sj[3 * i +: 3] = c[2:0]; end
                else begin
                    if (xv) begin xtwo = 1'b1; xin2 = dq_d[512 * i +: 512]; end
                    else begin xv = 1'b1; xin = dq_d[512 * i +: 512]; xidx = c; end
                end
                c = c + 1;
            end
        nrc = c;
    end
    wire         isop = xv && mine;
    wire [15:0]  oi = xidx - np;              // operand index
    wire [13:0]  obase = prow[0][13:0];
    integer j;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin jk <= 0; mine <= 0; rc <= 0; end
        else if (dq_st) begin jk <= dq_kind; mine <= (dq_kind == K_RA || dq_kind == K_RB || dq_kind == K_QR); rc <= 0; end
        else if (mine) rc <= nrc;
    end
    always @(posedge clk)
        if (mine && !dq_st) begin : cap
            integer i;
            for (i = 0; i < S_RD; i = i + 1)
                for (j = 0; j < MAXP; j = j + 1)
                    if (sv[i] && sj[3 * i +: 3] == j) prow[j] <= dq_d[512 * i +: 512];
            if (xv && jk == K_RB && !oi[0] && !xtwo) hold <= xin;   // legacy split pair (not issued by hctl any more)
        end

    // ------------------------------------------------------------------ engine
    // RB: a score row and its bias row arrive in one cycle (xin = score, xin2 = bias; xtwo); a lone RB row is the legacy
    // interleave (score held, then bias)
    wire        rbp = (jk == K_RB) && xtwo;
    wire        e_v = isop && !dq_st && (jk != K_RB || rbp || oi[0]);
    wire        qrp = (QW > 1) && (jk == K_QR) && xtwo;      // QR pair: rope rows oi, oi + 1 of one head
    wire [1:0]  e_k = (jk == K_RA) ? 2'd0 : (jk == K_RB) ? 2'd1 : 2'd2;
    wire [511:0] e_x = (jk == K_RB) ? (rbp ? xin : hold) : xin;
    wire [511:0] e_b = (rbp || qrp) ? xin2 : xin;
    wire        ev, ev2, ef, erdy;
    wire [511:0] ed, ed2;
    ot_s81_su_rxex #(.LM(LM), .LA(LA), .MUT(XMUT)) u_e (
        .clk(clk), .rst_n(rst_n), .i_v(e_v), .i_k(e_k), .i_x(e_x), .i_b(e_b), .i_v2(qrp), .i_j(oi[1:0]), .i_rdy(erdy),
        .cos_t({prow[2], prow[1]}), .sin_t({prow[4], prow[3]}), .o_v(ev), .o_d(ed), .o_v2(ev2), .o_d2(ed2), .fault(ef),
        .xa_v(xa_v), .xa_x(xa_x), .xa_vi(xa_vi), .xa_r(xa_r), .xa_f(xa_f),
        .xq_v(xq_v), .xq_x(xq_x), .xq_c(xq_c), .xq_s(xq_s), .xq_vi(xq_vi), .xq_y(xq_y), .xq_f(xq_f),
        .xb_v(xb_v), .xb_vi(xb_vi), .xb_y(xb_y), .xb_f(xb_f));

    // ------------------------------------------------------------------ result rows -> the write slot
    reg [15:0] wc;                            // result rows of the job written
    wire [13:0] wa = (jk == K_QR) ? obase + {wc[13:2], 5'd0} + 14'd28 + {12'd0, wc[1:0]} : obase + wc[13:0];
    wire [15:0] wc1 = wc + 16'd1;
    wire [13:0] wa2 = obase + {wc1[13:2], 5'd0} + 14'd28 + {12'd0, wc1[1:0]};
    always @(posedge clk) begin
        o_a <= wa; o_m <= 16'hFFFF; o_d <= ed; o_a2 <= wa2; o_d2 <= ed2;
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            o_v <= 0; o_v2 <= 0; o_fu <= 0; o_fo <= 0; o_alive <= 0; o_den <= 0; o_rdy <= 0; o_rjid <= 0; wc <= 0;
        end else begin
            o_v <= ev; o_v2 <= ev2; o_alive <= 1'b1; o_den <= 1'b1; o_rdy <= 1'b0; o_rjid <= 8'd0;
            if (dq_st) wc <= 0; else if (ev) wc <= wc + (ev2 ? 16'd2 : 16'd1);
            if (ef) o_fu <= 1'b1;
            if ((xtwo && mine && jk != K_RB && !(QW > 1 && jk == K_QR)) || (e_v && !erdy)) o_fo <= 1'b1;
        end
    end
`ifdef SU_RX_TRACE_C
    reg [31:0] tr_cyc; reg tr_f, tr_e;
    always @(posedge clk) begin
        tr_cyc <= (!rst_n) ? 32'd0 : tr_cyc + 32'd1;
        if (dq_st) begin tr_f <= 1'b0; tr_e <= 1'b0; end
        if (isop && !dq_st && !tr_f) begin tr_f <= 1'b1; $display("RXTR rxt %0d first_operand_at_tile", tr_cyc); end
        if (ev && !tr_e) begin tr_e <= 1'b1; $display("RXTR rxt %0d first_result", tr_cyc); end
    end
`endif
endmodule

// RA / QR / RB leaf interfaces of the control leaf (ot_s81_su_rxe with the RA / QR lanes and the RB adders external)
module ot_s81_su_rxex #(
    parameter integer LM = 5, LA = 4, MUT = 0
) (
    input  wire              clk, rst_n,
    input  wire              i_v,
    input  wire [1:0]        i_k,
    input  wire [511:0]      i_x, i_b,
    input  wire              i_v2,
    input  wire [1:0]        i_j,
    output wire              i_rdy,
    input  wire [32*32-1:0]  cos_t, sin_t,
    output reg               o_v,
    output reg  [511:0]      o_d,
    output reg               o_v2,
    output reg  [511:0]      o_d2,
    output reg               fault,
    output reg               xa_v,
    output reg  [511:0]      xa_x,
    input  wire              xa_vi,
    input  wire [511:0]      xa_r,
    input  wire [3:0]        xa_f,
    output reg  [1:0]        xq_v,
    output reg  [1023:0]     xq_x,
    output reg  [511:0]      xq_c, xq_s,
    input  wire [1:0]        xq_vi,
    input  wire [1023:0]     xq_y,
    input  wire [3:0]        xq_f,
    output reg               xb_v,
    input  wire              xb_vi,
    input  wire [511:0]      xb_y,
    input  wire              xb_f
);
    localparam integer LAR = (LA >= 5) ? LA : LA + 1;
    localparam integer DB  = LAR + 1;
    genvar l;
    assign i_rdy = 1'b1;                     // 16 RA lanes: one row a cycle
    // ---------------- RA / QR issue: registered toward the leaves
    // QR coefficient words of rope row j: pair p of row j is entry 8 j + p of the 32-entry tables (a 4-way select of
    // constant slices: no runtime part-select)
    function automatic [255:0] coef(input [1:0] j, input [1023:0] t);
        case (j)
            2'd0: coef = t[0 +: 256];
            2'd1: coef = t[256 +: 256];
            2'd2: coef = t[512 +: 256];
            default: coef = t[768 +: 256];
        endcase
    endfunction
    wire iss_a = i_v && i_k == 2'd0;
    wire iss_q = i_v && i_k == 2'd2;
    wire iss_b = i_v && i_k == 2'd1;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin xa_v <= 1'b0; xq_v <= 2'b00; xb_v <= 1'b0; end
        else begin xa_v <= iss_a; xq_v <= {iss_q && i_v2, iss_q}; xb_v <= iss_b; end
    always @(posedge clk) begin
        xa_x <= i_x;
        xq_x <= {i_b, i_x};                  // QR: {pair row, row}; RB: {bias, score} (the RB leaf's operands)
        xq_c <= {coef(i_j + 2'd1, cos_t), coef(i_j, cos_t)};
        xq_s <= {coef(i_j + 2'd1, sin_t), coef(i_j, sin_t)};
    end
    // ---------------- results from the leaves: captured at this leaf's pins
    reg          a_vq; reg [511:0] a_rq; reg [3:0] a_fq;
    reg  [1:0]   q_vq; reg [1023:0] q_yq; reg [3:0] q_fq;
    reg          b_vq; reg [511:0] b_yq; reg b_fq;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin a_vq <= 1'b0; q_vq <= 2'b00; a_fq <= 4'd0; q_fq <= 4'd0; b_vq <= 1'b0; b_fq <= 1'b0; end
        else begin a_vq <= xa_vi; q_vq <= xq_vi; a_fq <= xa_f; q_fq <= xq_f; b_vq <= xb_vi; b_fq <= xb_f; end
    always @(posedge clk) begin a_rq <= xa_r; q_yq <= xq_y; b_yq <= xb_y; end
    // ---------------- result row (one job kind runs at a time)
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin o_v <= 0; o_v2 <= 0; fault <= 0; end
        else begin
            o_v <= a_vq | b_vq | q_vq[0];
            o_v2 <= q_vq[1];
            if (|a_fq || b_fq || |q_fq) fault <= 1;
        end
    end
    always @(posedge clk) begin o_d <= a_vq ? a_rq : b_vq ? b_yq : q_yq[511:0]; o_d2 <= q_yq[1023:512]; end
endmodule

// L RA lanes: sqrt(softplus) (ot_hdc_v41x_softplus_s PCUT 1, the flat core's units); input and output pin flops.
// MUT 1 (bench negative control): the lanes return softplus instead of its square root.
module ot_s81_su_rxra #(
    parameter integer L = 4, MUT = 0
) (
    input  wire            clk, rst_in,
    input  wire            i_v,
    input  wire [32*L-1:0] i_x,
    output reg             o_v,
    output reg  [32*L-1:0] o_r,
    output reg             o_f
);
    reg rr0, rr1;
    always @(posedge clk or negedge rst_in) if (!rst_in) begin rr0 <= 1'b0; rr1 <= 1'b0; end else begin rr0 <= 1'b1; rr1 <= rr0; end
    wire rst_n = rr1;
    reg v_q; reg [32*L-1:0] x_q;
    always @(posedge clk or negedge rst_n) if (!rst_n) v_q <= 1'b0; else v_q <= i_v;
    always @(posedge clk) x_q <= i_x;
    wire [32*L-1:0] r, sp; wire [L-1:0] vo, f;
    genvar l;
    generate for (l = 0; l < L; l = l + 1) begin : g_l
        ot_hdc_v41x_softplus_s #(.PCUT(1)) u (.clk(clk), .rst_n(rst_n), .v(v_q), .x(x_q[32 * l +: 32]),
            .sp(sp[32 * l +: 32]), .r(r[32 * l +: 32]), .vo(vo[l]), .fault(f[l]));
    end endgenerate
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin o_v <= 1'b0; o_f <= 1'b0; end
        else begin o_v <= vo[0]; o_f <= |(vo & f); end
    always @(posedge clk) o_r <= (MUT == 1) ? sp : r;
endmodule

// One QR row: forward RoPE of 8 pairs on 16 lanes (2 multiplies + 1 add, BF16 RNE out), the flat core's units;
// i_c / i_s = the row's 8 cos / sin coefficients (pair p at [32 p +: 32]); input and output pin flops.
// MUT 3 (bench negative control): the inverse rotation.
module ot_s81_su_rxqr #(
    parameter integer LM = 5, LA = 4, MUT = 0,
    parameter integer QL = 16                 // lanes of this leaf (even: a lane's rotation pair stays inside the leaf)
) (
    input  wire               clk, rst_in,
    input  wire               i_v,
    input  wire [32*QL-1:0]   i_x,
    input  wire [16*QL-1:0]   i_c, i_s,
    output reg                o_v,
    output reg  [32*QL-1:0]   o_y,
    output reg                o_f
);
    localparam integer LMR = LM + 1, LAR = (LA >= 5) ? LA : LA + 1;
    localparam integer DQ  = LMR + LAR + 1;
    function automatic [31:0] bf16(input [31:0] x);
        reg [32:0] s;
        begin
            s = {1'b0, x} + 33'h7FFF + {32'd0, x[16]};
            bf16 = {s[31:16], 16'd0};
        end
    endfunction
    reg rr0, rr1;
    always @(posedge clk or negedge rst_in) if (!rst_in) begin rr0 <= 1'b0; rr1 <= 1'b0; end else begin rr0 <= 1'b1; rr1 <= rr0; end
    wire rst_n = rr1;
    reg v_q; reg [32*QL-1:0] x_q; reg [16*QL-1:0] c_q, s_q;
    always @(posedge clk or negedge rst_n) if (!rst_n) v_q <= 1'b0; else v_q <= i_v;
    always @(posedge clk) begin x_q <= i_x; c_q <= i_c; s_q <= i_s; end
    wire [DQ:0] vq;
    ot_hdc_vline #(.D(DQ)) u_vq (.clk(clk), .rst_n(rst_n), .v(v_q), .vd(vq));
    wire [32*QL-1:0] y; wire [QL-1:0] f;
    genvar l;
    integer g;
    generate for (l = 0; l < QL; l = l + 1) begin : g_qr
        localparam integer ODD = l % 2, P = l / 2;
        wire [31:0] cc = c_q[32 * P +: 32], sn = s_q[32 * P +: 32];
        wire [31:0] mine = x_q[32 * l +: 32], pair = x_q[32 * (ODD ? l - 1 : l + 1) +: 32];
        wire [31:0] sg = ((ODD != 0) ^ (MUT == 3)) ? sn : {~sn[31], sn[30:0]};
        wire [31:0] pp, qq, rs;
        wire f0, f1, f2;
        ot_hdc_qmul_lat #(LMR) u_p (clk, rst_n, v_q, mine, cc, pp, f0);
        ot_hdc_qmul_lat #(LMR) u_q (clk, rst_n, v_q, pair, sg, qq, f1);
        ot_dsrom_qadd #(.LAT(LAR)) u_a (clk, rst_n, vq[LMR], pp, qq, rs, f2);
        assign y[32 * l +: 32] = rs;
        assign f[l] = f0 | f1 | f2;
    end endgenerate
    reg [32*QL-1:0] yo;
    always @(posedge clk) for (g = 0; g < QL; g = g + 1) yo[32 * g +: 32] <= bf16(y[32 * g +: 32]);
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin o_v <= 1'b0; o_f <= 1'b0; end
        else begin o_v <= vq[DQ]; o_f <= |f; end
    always @(posedge clk) o_y <= yo;
endmodule

// RB leaf: 16 lanes score + bias (ot_dsrom_qadd, the flat core's unit, bit-identical to ot_s81_su_rxe); input and
// output pin flops.  i_x = {bias, score} (the control's xq_x word).  MUT 2 (bench negative control): bias dropped.
module ot_s81_su_rxrb #(
    parameter integer LA = 4, MUT = 0
) (
    input  wire            clk, rst_in,
    input  wire            i_v,
    input  wire [1023:0]   i_x,
    output reg             o_v,
    output reg  [511:0]    o_y,
    output reg             o_f
);
    localparam integer LAR = (LA >= 5) ? LA : LA + 1;
    reg rr0, rr1;
    always @(posedge clk or negedge rst_in) if (!rst_in) begin rr0 <= 1'b0; rr1 <= 1'b0; end else begin rr0 <= 1'b1; rr1 <= rr0; end
    wire rst_n = rr1;
    reg v_q; reg [1023:0] x_q;
    always @(posedge clk or negedge rst_n) if (!rst_n) v_q <= 1'b0; else v_q <= i_v;
    always @(posedge clk) x_q <= i_x;
    wire [511:0] y; wire [15:0] f;
    genvar l;
    generate for (l = 0; l < 16; l = l + 1) begin : g_rb
        ot_dsrom_qadd #(.LAT(LAR)) u_a (clk, rst_n, v_q, x_q[32 * l +: 32], (MUT == 2) ? 32'd0 : x_q[512 + 32 * l +: 32],
                                        y[32 * l +: 32], f[l]);
    end endgenerate
    wire [LAR:0] vd;
    ot_hdc_vline #(.D(LAR)) u_v (.clk(clk), .rst_n(rst_n), .v(v_q), .vd(vd));
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin o_v <= 1'b0; o_f <= 1'b0; end
        else begin o_v <= vd[LAR]; o_f <= |f; end
    always @(posedge clk) o_y <= y;
endmodule

// The cluster: control + 16 / L RA lane leaves + 2 QR row leaves + the RB leaf (ports = ot_s81_su_rxt at S_RD, QW 2)
module ot_s81_su_rxh #(
    parameter integer S_RD = 5, LM = 5, LA = 4, XMUT = 0, L = 4,
    parameter integer QL = 8                  // QR lanes a leaf (16 / QL leaves a QR row; one 16-lane row = 23.8k sinks)
) (
    input  wire                   clk, rst_in,
    input  wire                   dn_st_i,
    input  wire [3:0]             dn_kind_i,
    input  wire [7:0]             dn_jid_i,
    input  wire [S_RD-1:0]        dn_v_i,
    input  wire [S_RD*512-1:0]    dn_d_i,
    output wire                   o_v,
    output wire [13:0]            o_a,
    output wire [15:0]            o_m,
    output wire [511:0]           o_d,
    output wire                   o_v2,
    output wire [13:0]            o_a2,
    output wire [511:0]           o_d2,
    output wire                   o_fu, o_fo, o_alive, o_den, o_rdy,
    output wire [7:0]             o_rjid
);
    localparam integer NA = 16 / L;
    wire xa_v; wire [511:0] xa_x, xa_r; wire [NA-1:0] a_vo, a_f;
    wire [1:0] xq_v, xq_vi; wire [3:0] xq_f; wire [1023:0] xq_x, xq_y; wire [511:0] xq_c, xq_s;
    wire [3:0] a_fo4;
    wire xb_v, xb_vi, xb_f; wire [511:0] xb_y;
    ot_s81_su_rxc #(.S_RD(S_RD), .LM(LM), .LA(LA), .XMUT(XMUT), .QW(2)) u_c (
        .clk(clk), .rst_in(rst_in), .dn_st_i(dn_st_i), .dn_kind_i(dn_kind_i), .dn_jid_i(dn_jid_i), .dn_v_i(dn_v_i),
        .dn_d_i(dn_d_i), .o_v(o_v), .o_a(o_a), .o_m(o_m), .o_d(o_d), .o_v2(o_v2), .o_a2(o_a2), .o_d2(o_d2),
        .o_fu(o_fu), .o_fo(o_fo), .o_alive(o_alive), .o_den(o_den), .o_rdy(o_rdy), .o_rjid(o_rjid),
        .xa_v(xa_v), .xa_x(xa_x), .xa_vi(a_vo[0]), .xa_r(xa_r), .xa_f(a_fo4),
        .xq_v(xq_v), .xq_x(xq_x), .xq_c(xq_c), .xq_s(xq_s), .xq_vi(xq_vi), .xq_y(xq_y), .xq_f(xq_f),
        .xb_v(xb_v), .xb_vi(xb_vi), .xb_y(xb_y), .xb_f(xb_f));
    ot_s81_su_rxrb #(.LA(LA), .MUT(XMUT == 2 ? 2 : 0)) u_b (.clk(clk), .rst_in(rst_in), .i_v(xb_v), .i_x(xq_x),
        .o_v(xb_vi), .o_y(xb_y), .o_f(xb_f));
    // RA fault per leaf group folded to 4 bits for the control's 4-bit fault input
    genvar k;
    generate for (k = 0; k < 4; k = k + 1) begin : g_af
        if (k < NA) begin : g_y
            if (NA > 4) begin : g_or assign a_fo4[k] = |a_f[k * (NA / 4) +: NA / 4]; end
            else begin : g_one assign a_fo4[k] = a_f[k]; end
        end else begin : g_n assign a_fo4[k] = 1'b0; end
    end endgenerate
    generate for (k = 0; k < NA; k = k + 1) begin : g_ra
        ot_s81_su_rxra #(.L(L), .MUT(XMUT == 1 ? 1 : 0)) u_a (.clk(clk), .rst_in(rst_in), .i_v(xa_v),
            .i_x(xa_x[32 * L * k +: 32 * L]), .o_v(a_vo[k]), .o_r(xa_r[32 * L * k +: 32 * L]), .o_f(a_f[k]));
    end endgenerate
    localparam integer NQ = 16 / QL;
    generate for (k = 0; k < 2; k = k + 1) begin : g_qr
        wire [NQ-1:0] q_vo, q_f;
        genvar j;
        for (j = 0; j < NQ; j = j + 1) begin : g_ql
            ot_s81_su_rxqr #(.LM(LM), .LA(LA), .MUT(XMUT == 3 ? 3 : 0), .QL(QL)) u_q (.clk(clk), .rst_in(rst_in),
                .i_v(xq_v[k]), .i_x(xq_x[512 * k + 32 * QL * j +: 32 * QL]), .i_c(xq_c[256 * k + 16 * QL * j +: 16 * QL]),
                .i_s(xq_s[256 * k + 16 * QL * j +: 16 * QL]), .o_v(q_vo[j]), .o_y(xq_y[512 * k + 32 * QL * j +: 32 * QL]),
                .o_f(q_f[j]));
        end
        assign xq_vi[k] = q_vo[0];
        assign xq_f[NQ * k +: NQ] = q_f;               // registered at the control's pins, ORed there
    end endgenerate
endmodule

// hardened leaf / cluster tops at the production parameters
module dsfd_su_t_rxc (
    input  wire          ck, rst,
    input  wire          dn_st, input wire [3:0] dn_kind, input wire [7:0] dn_jid, input wire [4:0] dn_v,
    input  wire [2559:0] dn_d,
    output wire          o_v, output wire [13:0] o_a, output wire [15:0] o_m, output wire [511:0] o_d,
    output wire          o_v2, output wire [13:0] o_a2, output wire [511:0] o_d2,
    output wire          o_fu, o_fo, o_alive, o_den, o_rdy, output wire [7:0] o_rjid,
    output wire          xa_v, output wire [511:0] xa_x, input wire xa_vi, input wire [511:0] xa_r, input wire [3:0] xa_f,
    output wire [1:0]    xq_v, output wire [1023:0] xq_x, output wire [511:0] xq_c, xq_s,
    input  wire [1:0]    xq_vi, input wire [1023:0] xq_y, input wire [3:0] xq_f,
    output wire          xb_v, input wire xb_vi, input wire [511:0] xb_y, input wire xb_f
);
    ot_s81_su_rxc #(.S_RD(5), .LM(5), .LA(4), .QW(2)) u_c (
        .clk(ck), .rst_in(rst), .dn_st_i(dn_st), .dn_kind_i(dn_kind), .dn_jid_i(dn_jid), .dn_v_i(dn_v), .dn_d_i(dn_d),
        .o_v(o_v), .o_a(o_a), .o_m(o_m), .o_d(o_d), .o_v2(o_v2), .o_a2(o_a2), .o_d2(o_d2),
        .o_fu(o_fu), .o_fo(o_fo), .o_alive(o_alive), .o_den(o_den), .o_rdy(o_rdy), .o_rjid(o_rjid),
        .xa_v(xa_v), .xa_x(xa_x), .xa_vi(xa_vi), .xa_r(xa_r), .xa_f(xa_f),
        .xq_v(xq_v), .xq_x(xq_x), .xq_c(xq_c), .xq_s(xq_s), .xq_vi(xq_vi), .xq_y(xq_y), .xq_f(xq_f),
        .xb_v(xb_v), .xb_vi(xb_vi), .xb_y(xb_y), .xb_f(xb_f));
endmodule
module dsfd_su_t_rxrb (
    input wire ck, rst, i_v, input wire [1023:0] i_x, output wire o_v, output wire [511:0] o_y, output wire o_f
);
    ot_s81_su_rxrb #(.LA(4)) u_b (.clk(ck), .rst_in(rst), .i_v(i_v), .i_x(i_x), .o_v(o_v), .o_y(o_y), .o_f(o_f));
endmodule
module dsfd_su_t_rxra (
    input wire ck, rst, i_v, input wire [127:0] i_x, output wire o_v, output wire [127:0] o_r, output wire o_f
);
    ot_s81_su_rxra #(.L(4)) u_a (.clk(ck), .rst_in(rst), .i_v(i_v), .i_x(i_x), .o_v(o_v), .o_r(o_r), .o_f(o_f));
endmodule
module dsfd_su_t_rxqr (
    input wire ck, rst, i_v, input wire [255:0] i_x, input wire [127:0] i_c, i_s,
    output wire o_v, output wire [255:0] o_y, output wire o_f
);
    ot_s81_su_rxqr #(.LM(5), .LA(4), .QL(8)) u_q (.clk(ck), .rst_in(rst), .i_v(i_v), .i_x(i_x), .i_c(i_c), .i_s(i_s),
        .o_v(o_v), .o_y(o_y), .o_f(o_f));
endmodule
