`timescale 1ns/1ps
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
// ---------------------------------------------------------------------------------------------------------------
module ot_s81ph_coll_lane #(
    parameter integer FB = 69,
    parameter integer CREDITS = 512,
    parameter integer SEQW = 10,
    parameter integer CH_UCIE = 100,
    parameter integer CH_BOARD = 400,
    parameter integer IDLE_P = 1024,
    parameter integer SRAM = 1
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
    localparam integer PNUM = FB * G * (IDLE_P - 1);
    localparam integer PDEN = S * IDLE_P;
    reg [1:0] rst_s;
    always @(posedge clk or negedge rs_n) if (!rs_n) rst_s <= 2'b00; else rst_s <= {rst_s[0], 1'b1};
    wire rst_n = rst_s[1];
    reg [514:0] lr;
    always @(posedge clk or negedge rst_n) if (!rst_n) lr <= 0; else lr <= rx;
    // core -> link
    wire iv, ir, il; wire [W-1:0] id;
    ot_s81ph_skid #(.W(W + 1)) u_ski (.clk(clk), .rst_n(rst_n), .in_v(lo_v), .in_r(lo_r), .in_d(lo_d),
        .out_v(iv), .out_r(ir), .out_d({il, id}));
    // link -> core
    wire ov, orr, ol; wire [W-1:0] od;
    ot_s81ph_skid #(.W(W + 1)) u_sko (.clk(clk), .rst_n(rst_n), .in_v(ov), .in_r(orr), .in_d({ol, od}),
        .out_v(li_v), .out_r(li_r), .out_d(li_d));
    wire ftv, rtv, frv, rrv; wire [FFW-1:0] ft, fr; wire [RFW-1:0] rt, rr; wire ep_f, gb_f, gb_l;
    ot_s81ph_link_ep #(.FLIT_BYTES(FB), .TX_STAGES(2), .RX_STAGES(3), .CHANNEL_CYCLES(CH_UCIE), .CHANNEL_CYCLES_B(CH_BOARD),
        .CREDITS(CREDITS), .SEQW(SEQW), .PHY_NUM(PNUM), .PHY_DEN(PDEN), .SRAM(SRAM)) u_ep (
        .clk(clk), .rst_n(rst_n), .ch_b(ch_b),
        .in_valid(iv), .in_ready(ir), .in_data(id), .in_last(il),
        .out_valid(ov), .out_ready(orr), .out_data(od), .out_last(ol),
        .f_tx_v(ftv), .f_tx(ft), .f_rx_v(frv), .f_rx(fr), .r_tx_v(rtv), .r_tx(rt), .r_rx_v(rrv), .r_rx(rr),
        .credit_stalls(), .fault(ep_f), .fault_code(), .st_flits_tx(), .st_flits_rx_ok(), .st_crc_err(),
        .st_naks(), .st_replays(), .st_timeouts(), .st_retx_flits(), .st_max_replay_occ());
    ot_s81ph_link_gbx #(.FFW(FFW), .RFW(RFW), .IDLE_P(IDLE_P)) u_gb (
        .clk(clk), .rst_n(rst_n), .f_tx_v(ftv), .f_tx(ft), .r_tx_v(rtv), .r_tx(rt), .beat_tx(tx),
        .beat_rx_v(lr[0] && lr[513]), .beat_rx(lr[512:1]), .f_rx_v(frv), .f_rx(fr), .r_rx_v(rrv), .r_rx(rr),
        .locked(gb_l), .fault(gb_f));
    always @(posedge clk or negedge rst_n) if (!rst_n) flt <= 3'b000; else flt <= {lr[514], gb_f, ep_f};
    ot_s81ph_ckbuf u_tf (.a(clk), .y(tf));
endmodule

// tile tops (pin plans differ: W lanes face the slab's W edge, E lanes the E edge)
module dsfd_coll_lane_w (
    input wire [0:0] ck, input wire [0:0] rs, input wire [0:0] chb, input wire [514:0] rx, output wire [511:0] tx,
    output wire [0:0] tf, input wire [0:0] lo_v, output wire [0:0] lo_r, input wire [552:0] lo_d,
    output wire [0:0] li_v, input wire [0:0] li_r, output wire [552:0] li_d, output wire [2:0] flt);
    ot_s81ph_coll_lane u (.clk(ck[0]), .rs_n(rs[0]), .ch_b(chb[0]), .rx(rx), .tx(tx), .tf(tf[0]), .lo_v(lo_v[0]),
        .lo_r(lo_r[0]), .lo_d(lo_d), .li_v(li_v[0]), .li_r(li_r[0]), .li_d(li_d), .flt(flt));
endmodule
module dsfd_coll_lane_e (
    input wire [0:0] ck, input wire [0:0] rs, input wire [0:0] chb, input wire [514:0] rx, output wire [511:0] tx,
    output wire [0:0] tf, input wire [0:0] lo_v, output wire [0:0] lo_r, input wire [552:0] lo_d,
    output wire [0:0] li_v, input wire [0:0] li_r, output wire [552:0] li_d, output wire [2:0] flt);
    ot_s81ph_coll_lane u (.clk(ck[0]), .rs_n(rs[0]), .ch_b(chb[0]), .rx(rx), .tx(tx), .tf(tf[0]), .lo_v(lo_v[0]),
        .lo_r(lo_r[0]), .lo_d(lo_d), .li_v(li_v[0]), .li_r(li_r[0]), .li_d(li_d), .flt(flt));
endmodule
