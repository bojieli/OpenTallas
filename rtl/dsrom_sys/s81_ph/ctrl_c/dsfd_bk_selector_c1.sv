`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// dsfd_bk_selector_c1 (s81-die-rtl-bind 2026-10-14, die item F5): the selector slab master of a die with ONE HBM stack
// (S81 layer1: stack SW).  The selector's native select (ot_hdc_v41x_sel, Q 4) takes a segment as FOUR contiguous
// position quarters, each on its own lane / quarter tile; on a TP4 layer1 die the local top-k (L<n>.attn.idx.topk_local)
// selects over THIS die's quarter only -- the positions of the other three quarters live on the three peer dies, so on
// this die they are EMPTY quarters ("an empty quarter sends one beat with in_lv = 0 and in_last", ot_hdc_v41x_sel).
// The 4-stack master dsfd_bk_selector_c had those three lanes unconnected (no producer: the selector never completes).
// This master has the SW lane only and an absent-quarter tile in front of the UNCHANGED 4-lane selector:
//   dsfd_selt_xq  lane 0 = the SW lane (pin flop, passed on); lanes 1..3 = for every segment header on SW (type 1, its tag,
//                 k, qslot r) one header for each other qslot q != r (same tag / k, base = 0) and one empty last beat
//                 (type 2, lane valid 0, last) -- 2 words, one cycle after the SW header, on each of the three lanes
//                 (replays re-send the SW header: the empty quarters are re-sent with it)
//   dsfd_bk_selector (4 lanes {NE, NW, SE, SW}) and the sel endpoint dsfd_dw_ep_s on a snoop of vd, as dsfd_bk_selector_c.
// Cost: +1 cycle on the SW lane (the tile's pin flop).  The cross-die FINAL select (attn.idx.topk_final over the four
// dies' local selections) needs every quarter's (score, index) candidates on this die: an open functional item of the
// selector / svc / VM path (the local IDX words carry indices, not scores), recorded in el1014-s81-die-rtl-bind.log.
// MUT 1 (negative control): the synthesised quarters repeat the SW qslot (qslot collision -> selector format fault).
// ---------------------------------------------------------------------------------------------------------------------
module dsfd_selt_xq #(parameter integer MUT = 0) (
    input  wire [0:0]       ck, rst,
    input  wire [514:0]     i_sw,           // die lane {fault, live, data 512, valid}
    output wire [514:0]     o_sw,           // lane SW (pin flop, passed on)            = old o_lanes[0 +: 515]
    output wire [3*515-1:0] o_x             // synthesised {NE, NW, SE} empty quarters = old o_lanes[515 +: 1545]
);
    // r2 (S-ELEM-PQ 2026-10-16, closure-first after s81sel_xq x3 native launch / x4 congestion): SAME cycle behaviour as r1;
    // (a) the output is split in two ports so the pin plan can give the SW pass-through its own wide face range;
    // (b) only the control bits {fault, live, valid} take the (local) reset, data bits are plain flops (no 598-load reset
    //     net; data is don't-care while valid = 0, as before); (c) the synthesised quarters keep flops only on the bits
    //     that ever change (valid, k, qslot, beat flag, tag, type, live): every other bit is the constant it always was.
    reg [1:0] rs_q;
    always @(posedge ck[0] or negedge rst[0]) if (!rst[0]) rs_q <= 2'b00; else rs_q <= {rs_q[0], 1'b1};
    wire rn = rs_q[1];
    reg [514:0] p;                           // pin flop
    always @(posedge ck[0]) p <= i_sw;
    wire        hv  = p[0] && p[512:509] == 4'd1;            // a segment header on SW (data[511:508] type 1)
    wire [7:0]  tag = p[508:501];                            // data[507:500]
    wire [9:0]  k   = p[30:21];                              // data[29:20]
    wire [1:0]  r   = p[32:31];                              // data[31:30]
    // SW lane: data flops without reset, control flops with reset
    reg [511:0] sw_d; reg sw_v, sw_l, sw_f;
    always @(posedge ck[0]) sw_d <= p[512:1];
    always @(posedge ck[0] or negedge rn)
        if (!rn) begin sw_v <= 1'b0; sw_l <= 1'b0; sw_f <= 1'b0; end
        else begin sw_v <= p[0]; sw_l <= p[513]; sw_f <= p[514]; end
    assign o_sw = {sw_f, sw_l, sw_d, sw_v};
    // synthesised quarters: one state machine, per-lane qslot only
    reg  [1:0]  ph;                                          // 1: header sent, beat next
    reg  [7:0]  tg_q;
    reg         x_v, x_l, x_bt;                              // valid, live, beat flag (data bit 272 of a type-2 word)
    reg  [3:0]  x_ty; reg [7:0] x_tg; reg [9:0] x_k; reg [1:0] x_r [1:3];
    integer j;
    always @(posedge ck[0] or negedge rn)
        if (!rn) begin ph <= 2'd0; x_v <= 1'b0; x_l <= 1'b0; end
        else begin
            x_l <= 1'b1;
            if (hv) begin ph <= 2'd1; x_v <= 1'b1; end
            else if (ph == 2'd1) begin ph <= 2'd0; x_v <= 1'b1; end
            else x_v <= 1'b0;
        end
    always @(posedge ck[0]) begin                            // data: no reset (don't-care while x_v = 0)
        if (hv) begin
            tg_q <= tag; x_ty <= 4'd1; x_tg <= tag; x_k <= k; x_bt <= 1'b0;
            for (j = 1; j < 4; j = j + 1) x_r[j] <= 2'(MUT == 1 ? r : (r + j));
        end else if (ph == 2'd1) begin
            x_ty <= 4'd2; x_tg <= tg_q; x_k <= 10'd0; x_bt <= 1'b1;
            for (j = 1; j < 4; j = j + 1) x_r[j] <= 2'd0;
        end else begin
            x_ty <= 4'd0; x_tg <= 8'd0; x_k <= 10'd0; x_bt <= 1'b0;
            for (j = 1; j < 4; j = j + 1) x_r[j] <= 2'd0;
        end
    end
    genvar g;
    generate for (g = 1; g < 4; g = g + 1) begin : g_x
        // {fault 0 [514], live [513], type [512:509], tag [508:501], 227'0, beat flag [273], 240'0, qslot [32:31], k [30:21], 20'0, valid [0]} (r1 positions)
        assign o_x[515 * (g - 1) +: 515] = {1'b0, x_l, x_ty, x_tg, 227'd0, x_bt, 240'd0, x_r[g], x_k, 20'd0, x_v};
    end endgenerate
endmodule

module dsfd_bk_selector_c1 #(parameter integer MUT = 0) (
    input wire [0:0] ck,
    input wire [514:0] iSW,
    input wire [0:0] rst,
    output wire [513:0] vd,
    output wire [0:0] vf,
    input wire [84:0] c_cmd, output wire [8:0] c_done, output wire [1:0] c_st
);
    wire [4*515-1:0] ln;
    dsfd_selt_xq #(.MUT(MUT)) u_xq (.ck(ck), .rst(rst), .i_sw(iSW), .o_sw(ln[0 +: 515]), .o_x(ln[515 +: 1545]));
    dsfd_bk_selector u_s (.ck(ck), .iNE(ln[3*515 +: 515]), .iNW(ln[2*515 +: 515]), .iSE(ln[515 +: 515]), .iSW(ln[0 +: 515]),
        .rst(rst), .vd(vd), .vf(vf));
    dsfd_dw_ep_s u_dw (.ck(ck), .rst(rst), .vh({vd[513:502], vd[493:482], vd[1], vd[0]}), .c_cmd(c_cmd), .c_done(c_done), .c_st(c_st));
endmodule
