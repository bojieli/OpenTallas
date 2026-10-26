`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// dsfd_coll_mtp_lane (mtp-colllane-1011, 2026-10-10): the DEDICATED MTP link lane of the S81 collective slab
// (owner/coordinator decision ds-1010: the head-die sequencer's token return / seed get their own die-to-die lane,
// NOT a pass-through queue in the collective core -- no head-of-line blocking against collective traffic, the CLOSED
// collective core untouched).  This tile is the lane's MTP adapter; the lane itself is one more instance of the
// closed lane tile dsfd_coll_lane_w (LCR = 1: reliable link layer ot_s81ph_link_ep with its own 512 link credits and
// replay buffer, gearbox, board SerDes beat), so the slab gains lane W4 = the generator's first --mtp-links SerDes.
//
//   die side (from dsfd_mtp_seq_rtt over the hub chain, generator bus mtp -> collective 648 / collective -> mtp 2):
//     f_tv / f_td / t_tg   token return (RESULT flits to S0), grant protocol, receiver dsfd_coll_mtp_ep u_t
//     f_sv / f_sd / t_sg   seed to the draft primary, grant protocol, receiver dsfd_coll_mtp_ep u_s
//     f_acc                the sequencer's accept word {fault, acc_v, acc_u, acc_a, acc_c, acc_y} (from its flops, no
//                          flow control): an event (acc_v pulse or a rising fault) is queued and carried as a flit
//     The receivers are RTT-sized to the real pin-to-pin stages (FWD_C mtp -> collective, RET_C back; head631 8 / 8,
//     tools/s81/hub_stage_count.py --check-mtp-rtt): depth FWD_C + RET_C + 4, full rate.
//   lane side (abutting dsfd_coll_lane_w u_ml, LCR credit seams, same as the core <-> lane seams of split3cr):
//     lo_v / lo_d / lo_r   adapter -> lane: ot_link_credit_tx, CRED = the lane's landing depth (8)
//     li_v / li_d / li_r   lane -> adapter: ot_link_credit_rx, DEPTH 8 (the lane's tx CRED)
//   peer side (the far die's dsfd_coll_mtp_lane delivers to its consumers, grant protocol = the sequencer's links):
//     t_rtv / t_rtd / f_rtg   received token return    t_rsv / t_rsd / f_rsg   received seed
//     t_racc                  received accept word (acc_v = one-cycle event, from flops)
//
// No head-of-line blocking inside the lane: token and seed carry END-TO-END PER-CLASS CREDITS.  The receiving adapter
// lands every flit of a class in that class's own buffer (TCRED token / SCRED seed entries); the sender holds one credit
// per free remote entry and sends a class flit only with a credit in hand, so the lane's shared landing FIFO always
// drains (o_ready = 1) whatever either consumer does.  Freed entries return as CREDIT flits (counts of both classes)
// on the reverse direction of the same lane.  TCRED >= the lane's class credit round trip / the sequencer's fastest
// emission (one flit per 6 cycles, ot_dsrom_mtp_seq release): measured (tools/mtp_colllane_gate.py rate cases, board
// channel) 32 -> 8.0, 64 -> 9.0, 128 -> 6.4 cycles / token, so TCRED = 128 (two 128 x 256 SRAM macros); a stalled seed
// consumer never slows the token return and neither ever touches collective lanes 0..7.
//
// Flit {last = 1, type[551:549], payload}: 1 token (td 512 at [511:0]), 2 seed (sd at [SW-1:0]), 3 credit return
// ([7:0] token credits, [15:8] seed credits), 4 accept word ([AW-1:0]).  Arbitration: round robin over the four kinds.
// Faults (sticky, ORed into t_racc[AW-1]): lane landing overflow / bad type, class buffer overflow, accept queue
// overflow, and the lane tile's faults (f_lflt).
// Mutants (negative controls, never in a build):
//   OT_MTPL_MUT_SHARED  per-class credits off: classes share the landing FIFO, which stalls when the head flit's class
//                       buffer is full (the HOL design): a stalled seed consumer blocks the token return
//   OT_MTPL_MUT_CRED    the sender starts with TCRED + 3 token credits (one over the buffer's TCRED + 2 head capacity): overflow
//   OT_MTPL_MUT_STALE   receivers sized for the chain-record 6 / 7 stages on the real 8 / 8: grant overflow
// ---------------------------------------------------------------------------------------------------------------
module dsfd_coll_mtp_lane #(
    parameter integer FLIT = 512, parameter integer NW = 21, parameter integer USER_W = 10,
    parameter integer SW = USER_W + 3 * NW + 4,           // seed word (77)
    parameter integer AW = 2 * NW + USER_W + 5,           // accept word (57)
`ifdef OT_MTPL_MUT_STALE
    parameter integer FWD_C = 6, parameter integer RET_C = 7,
`else
    // head631 + --coll-split3-cr --coll-mtp-lane (results/rtl/mtp_colllane_20261011/head631_mtpl.opts): the taller slab
    // puts its MTP pins one station further: mtp -> collective 9, back 9 (tools/s81/hub_stage_count.py --check-mtp-rtt;
    // 8 / 8 on the plain head631 slab)
    parameter integer FWD_C = 9, parameter integer RET_C = 9,
`endif
`ifdef OT_MTPL_TCRED
    parameter integer TCRED = `OT_MTPL_TCRED,
`else
    parameter integer TCRED = 128,
`endif
    parameter integer SCRED = 16, parameter integer AQ = 4,
    parameter integer LCRED = 8
) (
    input  wire [0:0]        ck,
    input  wire [0:0]        rs,
    input  wire [0:0]        f_tv,  input  wire [FLIT-1:0] f_td,  output wire [0:0] t_tg,
    input  wire [0:0]        f_sv,  input  wire [SW-1:0]   f_sd,  output wire [0:0] t_sg,
    input  wire [AW-1:0]     f_acc,
    output wire [0:0]        lo_v,  input  wire [0:0] lo_r,  output wire [552:0] lo_d,
    input  wire [0:0]        li_v,  output wire [0:0] li_r,  input  wire [552:0] li_d,
    output wire [0:0]        t_rtv, output wire [FLIT-1:0] t_rtd, input wire [0:0] f_rtg,
    output wire [0:0]        t_rsv, output wire [SW-1:0]   t_rsd, input wire [0:0] f_rsg,
    output wire [AW-1:0]     t_racc,             // [AW-1] = the far sequencer's fault OR this lane's sticky faults
    input  wire [2:0]        f_lflt              // the lane tile's {meso end, gearbox, endpoint} fault flops
);
    localparam integer CW = 8;
    localparam [2:0] K_TOK = 3'd1, K_SEED = 3'd2, K_CRED = 3'd3, K_ACC = 3'd4;
    wire clk = ck[0];
    reg [1:0] rst_s;
    always @(posedge clk or negedge rs[0]) if (!rs[0]) rst_s <= 2'b00; else rst_s <= {rst_s[0], 1'b1};
    wire rst_n = rst_s[1];
    initial if (TCRED > 128 || SCRED > 255) $fatal(1, "dsfd_coll_mtp_lane: class credits exceed the 8-bit credit field");

    // ---------------------------------------------------------------- die side: RTT-sized receivers (dsfd_coll_mtp_ep)
    wire ctv, csv, ctr, csr; wire [FLIT-1:0] ctd; wire [SW-1:0] csd;
    dsfd_coll_mtp_ep #(.FLIT(FLIT), .NW(NW), .USER_W(USER_W), .SW(SW), .FWD_C(FWD_C), .RET_C(RET_C), .OPIPE(1)) u_ep (
        .ck(ck), .rst(rs), .f_tv(f_tv), .f_td(f_td), .t_tg(t_tg), .f_sv(f_sv), .f_sd(f_sd), .t_sg(t_sg),
        .c_tv(ctv), .c_tr(ctr), .c_td(ctd), .c_sv(csv), .c_sr(csr), .c_sd(csd));
    // accept word: pin flop, an event = acc_v (bit AW-2) or a rising fault (bit AW-1); queued (no flow control upstream)
    reg [AW-1:0] acc_p; reg fl_p;
    always @(posedge clk) acc_p <= f_acc;
    always @(posedge clk or negedge rst_n) if (!rst_n) fl_p <= 1'b0; else fl_p <= acc_p[AW-1];
    wire acc_ev = acc_p[AW-2] || (acc_p[AW-1] && !fl_p);
    wire aq_v; wire [AW-1:0] aq_d; wire aq_pop; wire aq_room, aq_flt;
    ot_s81ph_rfifo #(.W(AW), .D(AQ)) u_aq (.clk(clk), .rst_n(rst_n), .push(acc_ev), .wd(acc_p), .pop(aq_pop),
        .hv(aq_v), .hd(aq_d), .room(aq_room), .room2(), .fault(aq_flt));

    // ---------------------------------------------------------------- lane tx: per-class credits + round robin
    reg [CW-1:0] tcr, scr;               // remote class credits (free entries in the peer's class buffers)
    reg [CW-1:0] owe_t, owe_s;           // entries freed here, not yet returned to the peer
    wire t_pop_l, s_pop_l;               // local class buffer pops (receive side, below)
    wire li_ready;
    wire lt_ready; reg lt_valid; reg [552:0] lt_data;
`ifdef OT_MTPL_MUT_SHARED
    wire rq_t = ctv, rq_s = csv;
`else
    wire rq_t = ctv && tcr != 0, rq_s = csv && scr != 0;
`endif
    wire rq_c = owe_t != 0 || owe_s != 0, rq_a = aq_v;
    wire [3:0] rq = {rq_a, rq_c, rq_s, rq_t};
    reg  [1:0] ptr;
    reg  [3:0] gnt;
    integer k;
    always @(*) begin
        gnt = 4'b0;
        for (k = 3; k >= 0; k = k - 1)
            if (rq[(ptr + k) % 4]) gnt = 4'b1 << ((ptr + k) % 4);
    end
    wire send = lt_ready && rq != 4'b0;
    assign ctr = send && gnt[0];
    assign csr = send && gnt[1];
    wire c_snd = send && gnt[2];
    assign aq_pop = send && gnt[3];
    always @(*) begin
        lt_data = {1'b1, 552'b0};
        case (1'b1)
            gnt[0]: begin lt_data[551:549] = K_TOK;  lt_data[FLIT-1:0] = ctd; end
            gnt[1]: begin lt_data[551:549] = K_SEED; lt_data[SW-1:0] = csd; end
            gnt[2]: begin lt_data[551:549] = K_CRED; lt_data[2*CW-1:0] = {owe_s, owe_t}; end
            gnt[3]: begin lt_data[551:549] = K_ACC;  lt_data[AW-1:0] = aq_d; end
            default: ;
        endcase
        lt_valid = rq != 4'b0;
    end
    ot_link_credit_tx #(.W(553), .CRED(LCRED)) u_lo (.clk(clk), .rst_n(rst_n), .i_valid(lt_valid), .i_ready(lt_ready),
        .i_data(lt_data), .l_valid(lo_v[0]), .l_data(lo_d), .l_credit(lo_r[0]));

    // ---------------------------------------------------------------- lane rx: landing, class buffers, credit returns
    wire lr_v, lr_flt; wire [552:0] lr_d;
    ot_link_credit_rx #(.W(553), .DEPTH(LCRED), .OREG(1)) u_li (.clk(clk), .rst_n(rst_n), .l_valid(li_v[0]),
        .l_data(li_d), .l_credit(li_r[0]), .o_valid(lr_v), .o_ready(li_ready), .o_data(lr_d), .fault(lr_flt));
    wire [2:0] lk = lr_d[551:549];
    wire tb_v, sb_v, tb_room, sb_room, tb_flt, sb_flt; wire [FLIT-1:0] tb_d; wire [SW-1:0] sb_d;
`ifdef OT_MTPL_MUT_SHARED
    assign li_ready = !(lr_v && ((lk == K_TOK && !tb_room) || (lk == K_SEED && !sb_room)));
`else
    assign li_ready = 1'b1;              // per-class credits guarantee the class buffer has room
`endif
    wire lr_take = lr_v && li_ready;
    wire tb_push = lr_take && lk == K_TOK, sb_push = lr_take && lk == K_SEED;
    wire cr_in = lr_take && lk == K_CRED, ac_in = lr_take && lk == K_ACC;
    reg  bad_k;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) bad_k <= 1'b0;
        else if (lr_take && (lk == 3'd0 || lk > K_ACC)) bad_k <= 1'b1;
    // token buffer: TCRED x 512 in two ot_sram_1r1w_128x256 macros (ot_fifo_sram_fwft: 2-entry register head, bypass
    // when empty); occupancy counted here (room for the SHARED mutant, the overflow check is the FIFO's ovf)
    reg [CW:0] tb_n;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) tb_n <= '0; else tb_n <= tb_n + (CW+1)'(tb_push) - (CW+1)'(t_pop_l);
    assign tb_room = tb_n < (CW+1)'(TCRED);
    ot_fifo_sram_fwft #(.W(FLIT), .DEPTH(TCRED), .MACRO(2)) u_tb (.clk(clk), .rst_n(rst_n), .push(tb_push),
        .wdata(lr_d[FLIT-1:0]), .pop(t_pop_l), .hv(tb_v), .head(tb_d), .ovf(tb_flt));
    ot_s81ph_rfifo #(.W(SW), .D(SCRED)) u_sb (.clk(clk), .rst_n(rst_n), .push(sb_push), .wd(lr_d[SW-1:0]),
        .pop(s_pop_l), .hv(sb_v), .hd(sb_d), .room(sb_room), .room2(), .fault(sb_flt));
    // consumers: the sequencer's grant-protocol transmitter (launch from flops, one flit per grant)
    wire t_cr, s_cr;
    ot_dsrom_mtp_ltx #(.W(FLIT)) u_ot (.clk(clk), .rst_n(rst_n), .c_valid(tb_v), .c_ready(t_cr), .c_data(tb_d),
        .l_valid(t_rtv[0]), .l_ready(f_rtg[0]), .l_data(t_rtd));
    ot_dsrom_mtp_ltx #(.W(SW)) u_os (.clk(clk), .rst_n(rst_n), .c_valid(sb_v), .c_ready(s_cr), .c_data(sb_d),
        .l_valid(t_rsv[0]), .l_ready(f_rsg[0]), .l_data(t_rsd));
    assign t_pop_l = tb_v && t_cr;
    assign s_pop_l = sb_v && s_cr;
    reg [AW-1:0] racc;
    reg flt;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) racc <= {AW{1'b0}};
        else racc <= ac_in ? {lr_d[AW-1] | flt, lr_d[AW-2:0]} : {racc[AW-1] | flt, 1'b0, racc[AW-3:0]};   // acc_v: one-cycle event

    // ---------------------------------------------------------------- credit state
    wire [CW-1:0] rt = cr_in ? lr_d[CW-1:0] : {CW{1'b0}}, rsc = cr_in ? lr_d[2*CW-1:CW] : {CW{1'b0}};
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
`ifdef OT_MTPL_MUT_CRED
            tcr <= CW'(TCRED + 3);   // one over the buffer's real capacity (TCRED SRAM words + the 2-entry head register)
`else
            tcr <= CW'(TCRED);
`endif
            scr <= CW'(SCRED); owe_t <= {CW{1'b0}}; owe_s <= {CW{1'b0}}; ptr <= 2'd0;
        end else begin
            tcr <= tcr + rt - CW'(ctr);
            scr <= scr + rsc - CW'(csr);
            owe_t <= (c_snd ? {CW{1'b0}} : owe_t) + CW'(t_pop_l);
            owe_s <= (c_snd ? {CW{1'b0}} : owe_s) + CW'(s_pop_l);
            if (send) ptr <= (gnt[0] ? 2'd1 : gnt[1] ? 2'd2 : gnt[2] ? 2'd3 : 2'd0);
        end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) flt <= 1'b0;
        else flt <= flt | lr_flt | bad_k | tb_flt | sb_flt | aq_flt | (acc_ev && !aq_room) | (|f_lflt);
    assign t_racc = racc;                // launched from flops (fault bit = the far fault OR this lane's, +1 cycle)
endmodule
