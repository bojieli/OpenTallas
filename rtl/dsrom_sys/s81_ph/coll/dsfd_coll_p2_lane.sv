`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// dsfd_coll_p2_lane (mtp-colllane-1011, 2026-10-10): the P2 variant of the collective's dedicated MTP lane adapter
// (sibling of dsfd_coll_mtp_lane).  On MD-2 P2 draft die A the P2 selected-path traffic leaves the die over two
// dedicated lanes, never through the collective core's queues:
//   lane E4 (UCIe, die B -> die A)      class 5 L1   604 b: die B's expert-output words (P2 lane 1)
//   lane W4 (board, primary <-> die A)  class 6 ST   101 b: transaction start, primary -> die A
//                                       class 7 ROW  594 b: result row, die A -> primary
//                                       events: abort (primary -> A, 1 b), {corrected, fault, done} (A -> primary, 3 b)
// One adapter = one lane end: ONE data class each way (TXK / RXK, 0 = none) plus one event vector each way.
// Data words wider than a beat payload (548 b) go as TWO consecutive beats (seg 0 = word[547:0], seg 1 = the rest);
// the receiver reassembles in a staging register.  Flit {last = 1, type[551:549], seg[548], payload[547:0]};
// type 3 = credit return ([7:0]), type 4 = event vector ([EVW-1:0]).
// Flow control of the received data class:
//   CRED > 0  END-TO-END CREDITS: the receiver's class buffer has CRED words; the sender holds one credit per free
//             word and sends a word's first beat only with a credit, freed words return as credit flits.  The
//             lane's landing FIFO then always drains (o_ready = 1): the event flits behind a stalled data class are
//             never blocked (no head-of-line blocking inside the lane).  Required on a lane that carries events
//             in that direction.
//   CRED = 0  DIRECT: the landing FIFO backpressures through the lane's own link-layer credits (512, the link RTT).
//             Legal only for a direction that carries ONE class and no events (die B -> A: L1 at full rate).
//             (Elaboration check.)
// Events: the vector is sampled at a pin flop and sent whenever it changes (level semantics: a one-cycle pulse
// arrives as a one-cycle level unless two changes coalesce in the queue -- a pulse closer than the lane's flit gap to
// the previous change keeps its edge order; queue depth EQ, overflow = fault).
// Faults (sticky): landing overflow, unexpected type / segment, class buffer overflow, event queue overflow, the
// lane tile's faults (f_lflt) -> t_flt (from a flop).
// Mutants: OT_P2L_MUT_CRED (sender starts with CRED + 2 credits, one over buffer + output register: overflow), OT_P2L_MUT_SEG (the second
// beat's payload is not shifted: segmentation corrupts the high word), OT_P2L_MUT_DIRECT (credited direction run
// DIRECT: a stalled data consumer blocks the events behind it = HOL).
// ---------------------------------------------------------------------------------------------------------------
module dsfd_coll_p2_lane #(
    parameter integer TXK = 7, parameter integer TXW = 594,
    parameter integer RXK = 6, parameter integer RXW = 101,
    parameter integer EVT = 3, parameter integer EVR = 1,    // event widths sent / received (0 = none)
    parameter integer CRED = 8,                               // receive class buffer (0 = DIRECT)
    parameter integer TCRED = 8,                              // credits for the sent class (= the peer's CRED; 0 = DIRECT)
    parameter integer EQ = 4, parameter integer LCRED = 8,
    parameter integer RSKID = 0                               // 1: DIRECT output stage = 2-slot skid (registered ready)
) (
    input  wire [0:0]             ck, rs,
    input  wire [0:0]             x_v,  output wire [0:0] x_r,  input  wire [(TXW>0?TXW:1)-1:0] x_d,   // data to send
    output wire [0:0]             r_v,  input  wire [0:0] r_r,  output wire [(RXW>0?RXW:1)-1:0] r_d,   // data received
    input  wire [(EVT>0?EVT:1)-1:0] x_ev,                     // events to send (level, sampled)
    output wire [(EVR>0?EVR:1)-1:0] r_ev,                     // events received (level, from flops)
    output wire [0:0]             lo_v, input wire [0:0] lo_r, output wire [552:0] lo_d,
    input  wire [0:0]             li_v, output wire [0:0] li_r, input wire [552:0] li_d,
    input  wire [2:0]             f_lflt,
    output wire [0:0]             t_flt
);
    localparam integer PW = 548, CW = 8;
    localparam integer XW = TXW > 0 ? TXW : 1, RW_ = RXW > 0 ? RXW : 1;
    localparam integer ETW = EVT > 0 ? EVT : 1, ERW = EVR > 0 ? EVR : 1;
    localparam bit XSEG = TXW > PW, RSEG = RXW > PW;
    localparam [2:0] K_CRED = 3'd3, K_EV = 3'd4;
`ifdef OT_P2L_MUT_DIRECT
    localparam integer RCRED = 0, SCRED = 0;
`else
    localparam integer RCRED = CRED, SCRED = TCRED;
`endif
    initial begin
        if (CRED == 0 && EVR > 0) $fatal(1, "dsfd_coll_p2_lane: a DIRECT receive direction must not carry events (HOL)");
        if (TXW > 2 * PW || RXW > 2 * PW || CRED > 255) $fatal(1, "dsfd_coll_p2_lane: dimensions");
    end
    wire clk = ck[0];
    reg [1:0] rst_s;
    always @(posedge clk or negedge rs[0]) if (!rs[0]) rst_s <= 2'b00; else rst_s <= {rst_s[0], 1'b1};
    wire rst_n = rst_s[1];

    // ---------------------------------------------------------------- sender
    // data: a 2-entry input skid (registered x_r) so the 2-beat segmenter never stalls a pin-level handshake
    // x_r is low while this tile's synchronised reset is held (the skid's in_r is 1 in reset: a handshake there was lost)
    wire dv; wire dr; wire [XW-1:0] dd; wire xs_r;
    ot_s81ph_skid2 #(.W(XW)) u_xs (.clk(clk), .rst_n(rst_n), .in_v(x_v[0] && TXK != 0 && rst_n), .in_r(xs_r), .in_d(x_d),
        .out_v(dv), .out_r(dr), .out_d(dd));
    assign x_r[0] = xs_r && rst_n;
    // events: pin flop, change detect, queue
    reg [ETW-1:0] ev_p, ev_last;
    always @(posedge clk) ev_p <= x_ev;
    wire ev_ch = EVT > 0 && ev_p != ev_last;
    wire eq_v, eq_room, eq_flt; wire [ETW-1:0] eq_d; wire eq_pop;
    ot_s81ph_rfifo #(.W(ETW), .D(EQ)) u_eq (.clk(clk), .rst_n(rst_n), .push(ev_ch && eq_room), .wd(ev_p), .pop(eq_pop),
        .hv(eq_v), .hd(eq_d), .room(eq_room), .room2(), .fault(eq_flt));
    always @(posedge clk or negedge rst_n) if (!rst_n) ev_last <= {ETW{1'b0}}; else if (ev_ch && eq_room) ev_last <= ev_p;
    reg [CW-1:0] tcr, owe;
    reg seg;                                  // 1: the second beat of the current word is next
    wire lt_ready; reg lt_valid; reg [552:0] lt_data;
    wire rq_d = dv && (seg || SCRED == 0 || tcr != 0), rq_c = owe != 0, rq_e = eq_v;
    reg [1:0] ptr;                            // rr over data / credit / event; a started word keeps the lane
    reg [2:0] gnt;
    wire [2:0] rq3 = {rq_e, rq_c, rq_d};
    integer k;
    always @(*) begin
        gnt = 3'b0;
        if (seg) gnt = 3'b001;
        else for (k = 2; k >= 0; k = k - 1) if (rq3[(ptr + k) % 3]) gnt = 3'b1 << ((ptr + k) % 3);
    end
    wire send = lt_ready && gnt != 3'b0;
    wire d_beat = send && gnt[0];
    wire d_last = d_beat && (!XSEG || seg);
    assign dr = d_last;
    wire c_snd = send && gnt[1];
    assign eq_pop = send && gnt[2];
    wire [2*PW-1:0] dpad = {{(2 * PW - XW){1'b0}}, dd};
    always @(*) begin
        lt_data = {1'b1, 552'b0};
        lt_valid = gnt != 3'b0;
        case (1'b1)
`ifdef OT_P2L_MUT_SEG
            gnt[0]: begin lt_data[551:549] = 3'(TXK); lt_data[548] = seg; lt_data[PW-1:0] = dpad[PW-1:0]; end
`else
            gnt[0]: begin lt_data[551:549] = 3'(TXK); lt_data[548] = seg; lt_data[PW-1:0] = seg ? dpad[2*PW-1:PW] : dpad[PW-1:0]; end
`endif
            gnt[1]: begin lt_data[551:549] = K_CRED; lt_data[CW-1:0] = owe; end
            gnt[2]: begin lt_data[551:549] = K_EV;   lt_data[ETW-1:0] = eq_d; end
            default: ;
        endcase
    end
    ot_link_credit_tx #(.W(553), .CRED(LCRED)) u_lo (.clk(clk), .rst_n(rst_n), .i_valid(lt_valid), .i_ready(lt_ready),
        .i_data(lt_data), .l_valid(lo_v[0]), .l_data(lo_d), .l_credit(lo_r[0]));

    // ---------------------------------------------------------------- receiver
    wire lr_v, lr_flt; wire [552:0] lr_d; wire li_ready;
    ot_link_credit_rx #(.W(553), .DEPTH(LCRED), .OREG(1)) u_li (.clk(clk), .rst_n(rst_n), .l_valid(li_v[0]),
        .l_data(li_d), .l_credit(li_r[0]), .o_valid(lr_v), .o_ready(li_ready), .o_data(lr_d), .fault(lr_flt));
    wire [2:0] lk = lr_d[551:549]; wire lseg = lr_d[548];
    wire is_d = lk == 3'(RXK) && RXK != 0, is_c = lk == K_CRED, is_e = lk == K_EV && EVR > 0;
    // staging of a first segment, then the word into the class buffer (credited) or the output register (direct)
    reg stg_v; reg [PW-1:0] stg_d;
    wire last_seg = !RSEG || lseg;
    wire [2*PW-1:0] word = RSEG ? {lr_d[PW-1:0], stg_d} : {{PW{1'b0}}, lr_d[PW-1:0]};
    wire cb_v, cb_room, cb_room2, cb_flt; wire [RW_-1:0] cb_d; wire cb_pop;
    wire o_free;                              // the output stage can take a word this cycle
    wire d_ok = RCRED > 0 ? 1'b1 : (last_seg ? o_free : 1'b1);
    assign li_ready = !(lr_v && is_d && !d_ok);
    wire take = lr_v && li_ready;
    wire w_in = take && is_d && last_seg;
    reg bad;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin stg_v <= 1'b0; bad <= 1'b0; end
        else if (take) begin
            if (!(is_d || is_c || is_e)) bad <= 1'b1;
            if (is_d && RSEG) begin
                if (!lseg) begin if (stg_v) bad <= 1'b1; stg_v <= 1'b1; end
                else begin if (!stg_v) bad <= 1'b1; stg_v <= 1'b0; end
            end
        end
    always @(posedge clk) if (take && is_d && RSEG && !lseg) stg_d <= lr_d[PW-1:0];
    reg ov; reg [RW_-1:0] od;                 // output register (r_v / r_d leave flops)
    generate if (RCRED > 0) begin : g_cred
        ot_s81ph_rfifo #(.W(RW_), .D(RCRED)) u_cb (.clk(clk), .rst_n(rst_n), .push(w_in), .wd(word[RW_-1:0]), .pop(cb_pop),
            .hv(cb_v), .hd(cb_d), .room(cb_room), .room2(cb_room2), .fault(cb_flt));
        assign cb_pop = cb_v && (!ov || r_r[0]);
        assign o_free = 1'b1;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) ov <= 1'b0; else if (!ov || r_r[0]) ov <= cb_v;
        always @(posedge clk) if (cb_pop) od <= cb_d;
    end else if (RSKID == 0) begin : g_direct
        assign cb_flt = 1'b0; assign cb_pop = 1'b0; assign cb_v = 1'b0; assign cb_d = '0; assign cb_room = 1'b1; assign cb_room2 = 1'b1;
        assign o_free = !ov || r_r[0];
        always @(posedge clk or negedge rst_n)
            if (!rst_n) ov <= 1'b0; else if (w_in) ov <= 1'b1; else if (r_r[0]) ov <= 1'b0;
        always @(posedge clk) if (w_in) od <= word[RW_-1:0];
    end else begin : g_direct_skid
        // quickfix-1010 (2026-10-10): the DIRECT output stage as a 2-slot skid.  o_free is the skid's registered in_r,
        // so the r_r input pin reaches only the skid's load enable (out_v / out_d / sk_d) instead of li_ready and the
        // link receiver's output register (the 13-15-level r_r class of mtpl-*-0ddaf548b, TT -140).  r_v / r_d still
        // leave flops; same word order, full rate, 0 added cycles on an unstalled stream (one more word of buffering).
        assign cb_flt = 1'b0; assign cb_pop = 1'b0; assign cb_v = 1'b0; assign cb_d = '0; assign cb_room = 1'b1; assign cb_room2 = 1'b1;
        wire sk_in_r, sk_ov; wire [RW_-1:0] sk_od;
        ot_s81ph_skid2 #(.W(RW_)) u_os (.clk(clk), .rst_n(rst_n), .in_v(w_in), .in_r(sk_in_r), .in_d(word[RW_-1:0]),
            .out_v(sk_ov), .out_r(r_r[0]), .out_d(sk_od));
        assign o_free = sk_in_r;
        always @(*) begin ov = sk_ov; od = sk_od; end
    end endgenerate
    assign r_v = ov; assign r_d = od;
    reg [ERW-1:0] rev;
    always @(posedge clk or negedge rst_n) if (!rst_n) rev <= {ERW{1'b0}}; else if (take && is_e) rev <= lr_d[ERW-1:0];
    assign r_ev = rev;

    // ---------------------------------------------------------------- credit state
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
`ifdef OT_P2L_MUT_CRED
            tcr <= CW'(SCRED + 2);   // one over the peer's real capacity (CRED buffer words + its output register)
`else
            tcr <= CW'(SCRED);
`endif
            owe <= {CW{1'b0}}; ptr <= 2'd0; seg <= 1'b0;
        end else begin
            tcr <= tcr + ((take && is_c) ? lr_d[CW-1:0] : {CW{1'b0}}) - CW'(d_beat && !seg && SCRED > 0);
            owe <= (c_snd ? {CW{1'b0}} : owe) + CW'(RCRED > 0 && cb_pop);
            if (d_beat && XSEG) seg <= !seg;
            if (send && !(d_beat && XSEG && !seg)) ptr <= gnt[0] ? 2'd1 : gnt[1] ? 2'd2 : 2'd0;
        end
    reg flt;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) flt <= 1'b0;
        else flt <= flt | lr_flt | bad | cb_flt | eq_flt | (ev_ch && !eq_room) | (|f_lflt);
    assign t_flt = flt;
endmodule

// hardened masters (one per parameter set: the port widths differ)
// dsfd_coll_p2_lane_pa: draft die A, lane W4 to / from the DSpark primary: TX result row 594 (2 beats) + {corrected,
// fault, done}; RX start 101 (credited, 8) + abort
module dsfd_coll_p2_lane_pa (
    input  wire [0:0] ck, rs,
    input  wire [0:0] x_v, output wire [0:0] x_r, input wire [593:0] x_d,
    output wire [0:0] r_v, input wire [0:0] r_r, output wire [100:0] r_d,
    input  wire [2:0] x_ev, output wire [0:0] r_ev,
    output wire [0:0] lo_v, input wire [0:0] lo_r, output wire [552:0] lo_d,
    input  wire [0:0] li_v, output wire [0:0] li_r, input wire [552:0] li_d,
    input  wire [2:0] f_lflt, output wire [0:0] t_flt);
    dsfd_coll_p2_lane #(.TXK(7), .TXW(594), .RXK(6), .RXW(101), .EVT(3), .EVR(1), .CRED(8), .TCRED(8)) u (.ck(ck), .rs(rs),
        .x_v(x_v), .x_r(x_r), .x_d(x_d), .r_v(r_v), .r_r(r_r), .r_d(r_d), .x_ev(x_ev), .r_ev(r_ev),
        .lo_v(lo_v), .lo_r(lo_r), .lo_d(lo_d), .li_v(li_v), .li_r(li_r), .li_d(li_d), .f_lflt(f_lflt), .t_flt(t_flt));
endmodule
// dsfd_coll_p2_lane_ba: draft die A, lane E4 from die B (UCIe): RX lane-1 words 604 (2 beats, DIRECT: the only class)
module dsfd_coll_p2_lane_ba (
    input  wire [0:0] ck, rs,
    output wire [0:0] r_v, input wire [0:0] r_r, output wire [603:0] r_d,
    output wire [0:0] lo_v, input wire [0:0] lo_r, output wire [552:0] lo_d,
    input  wire [0:0] li_v, output wire [0:0] li_r, input wire [552:0] li_d,
    input  wire [2:0] f_lflt, output wire [0:0] t_flt);
`ifdef OT_P2L_BA_NOSKID
    localparam integer BA_RSKID = 0;
`else
    localparam integer BA_RSKID = 1;     // quickfix-1010: registered-ready output skid (r_r pin class)
`endif
    dsfd_coll_p2_lane #(.TXK(0), .TXW(0), .RXK(5), .RXW(604), .EVT(0), .EVR(0), .CRED(0), .TCRED(0), .RSKID(BA_RSKID)) u (.ck(ck), .rs(rs),
        .x_v(1'b0), .x_r(), .x_d(1'b0), .r_v(r_v), .r_r(r_r), .r_d(r_d), .x_ev(1'b0), .r_ev(),
        .lo_v(lo_v), .lo_r(lo_r), .lo_d(lo_d), .li_v(li_v), .li_r(li_r), .li_d(li_d), .f_lflt(f_lflt), .t_flt(t_flt));
endmodule
