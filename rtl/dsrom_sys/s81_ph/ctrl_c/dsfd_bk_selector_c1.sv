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
    output reg  [4*515-1:0] o_lanes         // {NE, NW, SE, SW} as dsfd_bk_selector
);
    reg [1:0] rs_q;
    always @(posedge ck[0] or negedge rst[0]) if (!rst[0]) rs_q <= 2'b00; else rs_q <= {rs_q[0], 1'b1};
    wire rn = rs_q[1];
    reg [514:0] p;                           // pin flop
    always @(posedge ck[0]) p <= i_sw;
    wire        hv  = p[0] && p[512:509] == 4'd1;            // a segment header on SW (data[511:508] type 1)
    wire [7:0]  tag = p[508:501];                            // data[507:500]
    wire [9:0]  k   = p[30:21];                              // data[29:20]
    wire [1:0]  r   = p[32:31];                              // data[31:30]
    reg  [1:0]  ph;                                          // 1: header sent, beat next
    reg  [7:0]  tg_q; reg [9:0] k_q; reg [1:0] r_q;
    integer j;
    always @(posedge ck[0] or negedge rn)
        if (!rn) begin o_lanes <= {4{515'd0}}; ph <= 2'd0; tg_q <= 0; k_q <= 0; r_q <= 0; end
        else begin
            o_lanes[0 +: 515] <= p;                          // SW
            for (j = 1; j < 4; j = j + 1) o_lanes[515 * j +: 515] <= {1'b0, 1'b1, 512'd0, 1'b0};   // live, idle
            if (hv) begin
                tg_q <= tag; k_q <= k; r_q <= r; ph <= 2'd1;
                for (j = 1; j < 4; j = j + 1)
                    o_lanes[515 * j +: 515] <= {1'b0, 1'b1, 4'd1, tag, 468'd0, 2'(MUT == 1 ? r : (r + j)), k, 20'd0, 1'b1};
            end else if (ph == 2'd1) begin
                ph <= 2'd0;
                for (j = 1; j < 4; j = j + 1)
                    o_lanes[515 * j +: 515] <= {1'b0, 1'b1, 4'd2, tg_q, 227'd0, 1'b1, 16'd0, 256'd0, 1'b1};
            end
        end
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
    dsfd_selt_xq #(.MUT(MUT)) u_xq (.ck(ck), .rst(rst), .i_sw(iSW), .o_lanes(ln));
    dsfd_bk_selector u_s (.ck(ck), .iNE(ln[3*515 +: 515]), .iNW(ln[2*515 +: 515]), .iSE(ln[515 +: 515]), .iSW(ln[0 +: 515]),
        .rst(rst), .vd(vd), .vf(vf));
    dsfd_dw_ep_s u_dw (.ck(ck), .rst(rst), .vh({vd[513:502], vd[493:482], vd[1], vd[0]}), .c_cmd(c_cmd), .c_done(c_done), .c_st(c_st));
endmodule
