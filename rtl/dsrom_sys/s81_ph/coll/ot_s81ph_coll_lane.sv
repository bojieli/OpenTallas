`timescale 1ns/1ps
`ifndef OT_S81PH_GFMT_DEF
`ifdef OT_S81PH_GBX_FMT1
`define OT_S81PH_GFMT_DEF 1
`else
`define OT_S81PH_GFMT_DEF 0
`endif
`endif
`ifndef OT_S81PH_EPPIPE_DEF
`ifdef OT_S81PH_EP_PIPE2
`define OT_S81PH_EPPIPE_DEF 2
`else
`define OT_S81PH_EPPIPE_DEF -1
`endif
`endif
// ---------------------------------------------------------------------------------------------------------------
// ot_s81ph_coll_lane -- one link lane TILE of the S81 collective slab (CLAUDE S81-PH coll v2, redesign pass).
// coll_m1 (the whole slab, 156k flops, 104 macros, ~1M nets) stayed 7 h in timing-driven global placement; the slab
// is now composed of 8 of these tiles (W lanes: dsfd_coll_lane_w, E lanes: dsfd_coll_lane_e, same RTL, mirrored pin
// plans), the core tile dsfd_coll_core (engine, VM queues, packer) and the clock tile dsfd_coll_ck (PLL, reset
// sequencer).  This tile = the lane's ot_s81ph_link_ep (reliable link layer, 10 SRAM macros) + ot_s81ph_link_gbx
// (512-b beat format), with:
//   die side   rx: {fault, live, data 512, valid} registered at the pin (as the v1 slab); tx = the gearbox's
//              registered beat; tf = forwarded clock (kept buffer of this tile's clock)
//   core side  lo (core -> link: flit 552 + last) through a 2-slot skid into the endpoint's in_*; li (link -> core)
//              through a 2-slot skid out of the endpoint's out_* (registered valid / data / ready both ways); lane
//              faults {meso, gearbox, endpoint} as flops.
//   ch_b       static: 1 = board lane (ACK timeout from CH_BOARD), 0 = UCIe lane (CH_UCIE)
// Function = the v1 slab lane (ot_s81ph_coll_core EXT 0): only the core <-> link handshakes gain the skid latency.
// v4 (CLAUDE 2026-10-07) LINK-UP GATE: v1..v3 sent flits from reset, before the peer's gearbox had locked (two
// markers 149 beats apart); those flits were cut while unaligned and lost, and with nothing behind them to raise a
// NAK the sender recovered only by its ACK timeout (~880 cycles: AG 24 records +914).  Now (1) this receiver sends
// no reverse frame until its gearbox has locked once (lk1), and (2) this sender accepts no flit from the core until
// it has received a reverse frame (up), i.e. until the peer's receiver is locked.  Both flags are sticky; before
// the first lock the receiver has accepted nothing, so a suppressed reverse frame carries no ACK or credit.  Later
// lock losses are recovered by the link protocol as before.  UPGATE = 0: the v3 lane.
// ---------------------------------------------------------------------------------------------------------------
module ot_s81ph_coll_lane #(
`ifdef OT_S81PH_GBX_FMT1
    parameter integer GFMT = 1,                // CLAUDE s81-blocks: gearbox FMT (ot_s81ph_link_gbx), ep pacing follows
`else
    parameter integer GFMT = 0,
`endif
`ifdef OT_S81PH_EP_PIPE2
    parameter integer EPPIPE = 2,              // CLAUDE s81-blocks: ot_s81ph_link_ep PIPE
`else
    parameter integer EPPIPE = -1,             // -1: the file's historical choice
`endif
    parameter integer FB = 69,
    parameter integer CREDITS = 512,
    parameter integer SEQW = 10,
    parameter integer CH_UCIE = 100,
    parameter integer CH_BOARD = 400,
    parameter integer IDLE_P = 1024,
    parameter integer SRAM = 1,
    parameter integer UPGATE = 1,
    // LCR (redesign-ds 2026-10-10, default 0): the core-facing face as CREDIT links (rtl/common/ot_link_credit.sv) for the
    // three-tile collective core in CR mode: lo_v / lo_d land in pin flops + an 8-deep FIFO (OREG), lo_r is a credit pulse
    // per freed slot; li_v / li_d leave from sender flops under credits, li_r is the receiver's credit pulse.  No pin
    // drives a wide enable on either side.  Same ports and pin plan; +2..3 cycles each way.
    parameter integer LCR = `ifdef OT_S81PH_LANE_CR 1 `else 0 `endif
) (
    input  wire          clk,
    input  wire          rs_n,       // stream reset (async assert), synchronised here
    input  wire          ch_b,
    input  wire [514:0]  rx,
    output wire [511:0]  tx,
    output wire          tf,
    input  wire          lo_v,
    output wire          lo_r,
    input  wire [552:0]  lo_d,       // {last, flit 552}
    output wire          li_v,
    input  wire          li_r,
    output wire [552:0]  li_d,
    output reg  [2:0]    flt         // {meso end fault, gearbox fault, endpoint fault}
);
    localparam integer W = FB * 8;
    localparam integer FFW = SEQW + 1 + W + 32;
    localparam integer RFW = 1 + SEQW + $clog2(CREDITS + 1) + 32;
    localparam integer G = 509 - RFW;
    localparam integer S = FFW + 1;
    localparam integer PNUM = (GFMT != 0) ? FB * 3 * (IDLE_P - 1) : FB * G * (IDLE_P - 1);
    localparam integer PDEN = (GFMT != 0) ? 4 * IDLE_P : S * IDLE_P;
    reg [1:0] rst_s;
    always @(posedge clk or negedge rs_n) if (!rs_n) rst_s <= 2'b00; else rst_s <= {rst_s[0], 1'b1};
    wire rst_n = rst_s[1];
    reg [514:0] lr;
    always @(posedge clk or negedge rst_n) if (!rst_n) lr <= 0; else lr <= rx;
    // core -> link
    wire iv, ir, il; wire [W-1:0] id;
    reg  lk1, up;                                // link-up gate (v4): own receiver locked once / peer's locked
    wire ir_g = ir && (UPGATE == 0 || up);
    generate if (LCR != 0) begin : g_lcri
        wire lcf;
        ot_link_credit_rx #(.W(W + 1), .DEPTH(8), .OREG(1)) u_ski (.clk(clk), .rst_n(rst_n), .l_valid(lo_v), .l_data(lo_d),
            .l_credit(lo_r), .o_valid(iv), .o_ready(ir_g), .o_data({il, id}), .fault(lcf));
    end else begin : g_skid_i
    ot_s81ph_skid2 #(.W(W + 1)) u_ski (.clk(clk), .rst_n(rst_n), .in_v(lo_v), .in_r(lo_r), .in_d(lo_d),
        .out_v(iv), .out_r(ir_g), .out_d({il, id}));
    end endgenerate
    // link -> core
    wire ov, orr, ol; wire [W-1:0] od;
    generate if (LCR != 0) begin : g_lcro
        wire lv; reg lvq; wire [W:0] ld;
        ot_link_credit_tx #(.W(W + 1), .CRED(8)) u_sko (.clk(clk), .rst_n(rst_n), .i_valid(ov), .i_ready(orr), .i_data({ol, od}),
            .l_valid(lv), .l_data(ld), .l_credit(li_r));
        assign li_v = lv; assign li_d = ld;
    end else begin : g_skid_o
    ot_s81ph_skid2 #(.W(W + 1)) u_sko (.clk(clk), .rst_n(rst_n), .in_v(ov), .in_r(orr), .in_d({ol, od}),
        .out_v(li_v), .out_r(li_r), .out_d(li_d));
    end endgenerate
    wire ftv, rtv, frv, rrv; wire [FFW-1:0] ft, fr; wire [RFW-1:0] rt, rr; wire ep_f, gb_f, gb_l;
    ot_s81ph_link_ep #(.FLIT_BYTES(FB), .TX_STAGES(2), .RX_STAGES(3), .CHANNEL_CYCLES(CH_UCIE), .CHANNEL_CYCLES_B(CH_BOARD),
        .CREDITS(CREDITS), .SEQW(SEQW), .PHY_NUM(PNUM), .PHY_DEN(PDEN), .SRAM(SRAM), .PIPE(EPPIPE < 0 ? 1 : EPPIPE)) u_ep (
        .clk(clk), .rst_n(rst_n), .ch_b(ch_b),
        .in_valid(iv && (UPGATE == 0 || up)), .in_ready(ir), .in_data(id), .in_last(il),
        .out_valid(ov), .out_ready(orr), .out_data(od), .out_last(ol),
        .f_tx_v(ftv), .f_tx(ft), .f_rx_v(frv), .f_rx(fr), .r_tx_v(rtv), .r_tx(rt), .r_rx_v(rrv), .r_rx(rr),
        .credit_stalls(), .fault(ep_f), .fault_code(), .st_flits_tx(), .st_flits_rx_ok(), .st_crc_err(),
        .st_naks(), .st_replays(), .st_timeouts(), .st_retx_flits(), .st_max_replay_occ());
    ot_s81ph_link_gbx #(.FMT(GFMT), .FFW(FFW), .RFW(RFW), .IDLE_P(IDLE_P)) u_gb (
        .clk(clk), .rst_n(rst_n), .f_tx_v(ftv), .f_tx(ft), .r_tx_v(rtv && (UPGATE == 0 || lk1)), .r_tx(rt), .beat_tx(tx),
        .beat_rx_v(lr[0] && lr[513]), .beat_rx(lr[512:1]), .f_rx_v(frv), .f_rx(fr), .r_rx_v(rrv), .r_rx(rr),
        .locked(gb_l), .fault(gb_f));
    always @(posedge clk or negedge rst_n) if (!rst_n) flt <= 3'b000; else flt <= {lr[514], gb_f, ep_f};
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin lk1 <= 1'b0; up <= 1'b0; end
        else begin if (gb_l) lk1 <= 1'b1; if (rrv) up <= 1'b1; end
    ot_s81ph_ckbuf u_tf (.a(clk), .y(tf));
endmodule

// tile tops (pin plans differ: W lanes face the slab's W edge, E lanes the E edge)
module dsfd_coll_lane_w #(parameter integer GFMT = `OT_S81PH_GFMT_DEF, parameter integer EPPIPE = `OT_S81PH_EPPIPE_DEF) (
    input wire [0:0] ck, input wire [0:0] rs, input wire [0:0] chb, input wire [514:0] rx, output wire [511:0] tx,
    output wire [0:0] tf, input wire [0:0] lo_v, output wire [0:0] lo_r, input wire [552:0] lo_d,
    output wire [0:0] li_v, input wire [0:0] li_r, output wire [552:0] li_d, output wire [2:0] flt);
    ot_s81ph_coll_lane #(.GFMT(GFMT), .EPPIPE(EPPIPE)) u (.clk(ck[0]), .rs_n(rs[0]), .ch_b(chb[0]), .rx(rx), .tx(tx), .tf(tf[0]), .lo_v(lo_v[0]),
        .lo_r(lo_r[0]), .lo_d(lo_d), .li_v(li_v[0]), .li_r(li_r[0]), .li_d(li_d), .flt(flt));
endmodule
module dsfd_coll_lane_e #(parameter integer GFMT = `OT_S81PH_GFMT_DEF, parameter integer EPPIPE = `OT_S81PH_EPPIPE_DEF) (
    input wire [0:0] ck, input wire [0:0] rs, input wire [0:0] chb, input wire [514:0] rx, output wire [511:0] tx,
    output wire [0:0] tf, input wire [0:0] lo_v, output wire [0:0] lo_r, input wire [552:0] lo_d,
    output wire [0:0] li_v, input wire [0:0] li_r, output wire [552:0] li_d, output wire [2:0] flt);
    ot_s81ph_coll_lane #(.GFMT(GFMT), .EPPIPE(EPPIPE)) u (.clk(ck[0]), .rs_n(rs[0]), .ch_b(chb[0]), .rx(rx), .tx(tx), .tf(tf[0]), .lo_v(lo_v[0]),
        .lo_r(lo_r[0]), .lo_d(lo_d), .li_v(li_v[0]), .li_r(li_r[0]), .li_d(li_d), .flt(flt));
endmodule
