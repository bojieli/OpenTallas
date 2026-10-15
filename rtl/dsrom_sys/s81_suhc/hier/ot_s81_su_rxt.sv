`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// ot_s81_su_rxt (s81-functional-token 2026-10-14, die item F1): the RA / RB / QR tile of the hierarchical SU slab
// dsfd_sp_su_h (its own spine stop, TK 14): router sqrt(softplus) (ffn.softplus_sqrt), router scores + bias (ffn.bias)
// and the q heads' RoPE tail (attn.q_rope), on the row engine ot_s81_su_rxe (the flat core's arithmetic, bit-identical).
//
// Streaming, no beat store: for these kinds the control tile issues ONE operand row read a cycle (RA: one every
// 16 / RAL cycles), RB interleaved score row r, bias row r (scores at in_base, the layer's bias rows directly after
// them), QR the head's 4 rope rows; this tile takes the row off the down-spine tap, holds an RB score row for its bias
// row, and issues the engine.  Result rows leave on ONE write slot (the tile's window: slot 0 of the up spine; a job
// runs alone, so no other tile drives the slot while it runs): RA / RB out_base + r, QR out_base + 32 h + 28 + j.
// Boundaries as every SU tile: pin flops on the tap, a registered write slot and status, a two-flop reset relay.
// Faults: the engine's (o_fu); two operand rows of a job in one cycle (the issue contract broken) -> o_fo.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_su_rxt #(
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
    output reg  [7:0]             o_rjid
);
    localparam [3:0] K_RA = 8, K_RB = 9, K_QR = 10, K_RW = 11;   // RW: s81-ftok r3 (F11, ot_s81_su_rw)
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
        else if (dq_st) begin jk <= dq_kind; mine <= (dq_kind == K_RA || dq_kind == K_RB || dq_kind == K_QR || dq_kind == K_RW); rc <= 0; end
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
    wire        e_v = isop && !dq_st && jk != K_RW && (jk != K_RB || rbp || oi[0]);
    wire        qrp = (QW > 1) && (jk == K_QR) && xtwo;      // QR pair: rope rows oi, oi + 1 of one head
    wire [1:0]  e_k = (jk == K_RA) ? 2'd0 : (jk == K_RB) ? 2'd1 : 2'd2;
    wire [511:0] e_x = (jk == K_RB) ? (rbp ? xin : hold) : xin;
    wire [511:0] e_b = (rbp || qrp) ? xin2 : xin;
    wire        ev, ev2, ef, erdy;
    wire [511:0] ed, ed2;
    ot_s81_su_rxe #(.RAL(RAL), .LM(LM), .LA(LA), .MUT(XMUT), .QW(QW)) u_e (
        .clk(clk), .rst_n(rst_n), .i_v(e_v), .i_k(e_k), .i_x(e_x), .i_b(e_b), .i_v2(qrp), .i_j(oi[1:0]), .i_rdy(erdy),
        .cos_t({prow[2], prow[1]}), .sin_t({prow[4], prow[3]}), .o_v(ev), .o_d(ed), .o_v2(ev2), .o_d2(ed2), .fault(ef));

    // ------------------------------------------------------------------ RW (ffn.weights): ids row + score rows -> weights
    wire        rwv, rwf; wire [511:0] rwd; wire [15:0] rwm;
    ot_s81_su_rw #(.LM(LM), .LA(LA), .MUT((XMUT == 4) ? 4 : 0)) u_rw (
        .clk(clk), .rst_n(rst_n), .start(dq_st && dq_kind == K_RW), .k_i(prow[0][160 +: 4]), .scale_i(prow[0][96 +: 32]),
        .off_i(prow[0][128 +: 4]), .i_v(isop && !dq_st && jk == K_RW), .i_x(xin), .i_last(oi == prow[0][64 +: 16] - 16'd1),
        .o_v(rwv), .o_d(rwd), .o_m(rwm), .fault(rwf));

    // ------------------------------------------------------------------ result rows -> the write slot
    reg [15:0] wc;                            // result rows of the job written
    wire [13:0] wa = (jk == K_QR) ? obase + {wc[13:2], 5'd0} + 14'd28 + {12'd0, wc[1:0]} : obase + wc[13:0];
    wire [15:0] wc1 = wc + 16'd1;
    wire [13:0] wa2 = obase + {wc1[13:2], 5'd0} + 14'd28 + {12'd0, wc1[1:0]};
    always @(posedge clk) begin
        o_a <= rwv ? obase : wa; o_m <= rwv ? rwm : 16'hFFFF; o_d <= rwv ? rwd : ed; o_a2 <= wa2; o_d2 <= ed2;
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            o_v <= 0; o_v2 <= 0; o_fu <= 0; o_fo <= 0; o_alive <= 0; o_den <= 0; o_rdy <= 0; o_rjid <= 0; wc <= 0;
        end else begin
            o_v <= ev | rwv; o_v2 <= ev2; o_alive <= 1'b1; o_den <= 1'b1; o_rdy <= 1'b0; o_rjid <= 8'd0;
            if (dq_st) wc <= 0; else if (ev) wc <= wc + (ev2 ? 16'd2 : 16'd1);
            if (ef || rwf) o_fu <= 1'b1;
            if ((xtwo && mine && jk != K_RB && !(QW > 1 && jk == K_QR)) || (e_v && !erdy)) o_fo <= 1'b1;
        end
    end
`ifdef SU_RX_TRACE
    reg [31:0] tr_cyc; reg tr_f, tr_e;
    always @(posedge clk) begin
        tr_cyc <= (!rst_n) ? 32'd0 : tr_cyc + 32'd1;
        if (dq_st) begin tr_f <= 1'b0; tr_e <= 1'b0; end
        if (isop && !dq_st && !tr_f) begin tr_f <= 1'b1; $display("RXTR rxt %0d first_operand_at_tile", tr_cyc); end
        if (ev && !tr_e) begin tr_e <= 1'b1; $display("RXTR rxt %0d first_result", tr_cyc); end
    end
`endif
endmodule

// dsfd_su_t_rx (s81-romB3 2026-10-14): the hardened RA / RB / QR tile of dsfd_sp_su_h (RXH 1: at the spine head, stop 0),
// ot_s81_su_rxt at its production parameters: 5 tapped read slots (QR 5 parameter rows; operand pairs on slots 0 / 1),
// 16 RA lanes, QR pair (QW 2: two result rows on write slots 0 / 1).
module dsfd_su_t_rx (
    input  wire          ck, rst,
    input  wire          dn_st, input wire [3:0] dn_kind, input wire [7:0] dn_jid, input wire [4:0] dn_v,
    input  wire [2559:0] dn_d,
    output wire          o_v, output wire [13:0] o_a, output wire [15:0] o_m, output wire [511:0] o_d,
    output wire          o_v2, output wire [13:0] o_a2, output wire [511:0] o_d2,
    output wire          o_fu, o_fo, o_alive, o_den, o_rdy, output wire [7:0] o_rjid
);
    ot_s81_su_rxh #(.S_RD(5), .LM(5), .LA(4), .L(4)) u_t (
        .clk(ck), .rst_in(rst), .dn_st_i(dn_st), .dn_kind_i(dn_kind), .dn_jid_i(dn_jid), .dn_v_i(dn_v), .dn_d_i(dn_d),
        .o_v(o_v), .o_a(o_a), .o_m(o_m), .o_d(o_d), .o_v2(o_v2), .o_a2(o_a2), .o_d2(o_d2),
        .o_fu(o_fu), .o_fo(o_fo), .o_alive(o_alive), .o_den(o_den), .o_rdy(o_rdy), .o_rjid(o_rjid));
endmodule
