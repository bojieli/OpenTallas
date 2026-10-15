`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// qwen-coll-io r5 2026-10-14 (OWNER 0ah static cycle schedule; OWNER 19:12 all on-chip execution real hardware):
// IO CALENDAR of the static TP8 collective.  Drives the real static IO masters of one compute die
//   qfd_io_xfifo_static   (static CDC channels up / ur / sx0-2 out, dp / dr / sr0-2 in: w/r slot, addr, version)
//   qfd_io_ucie_static    (P 546 + R 514 codecs: wr / rd / rx_expect slots)
//   qfd_io_serdes_static  x3 (board codecs: wr / rd / rx_expect slots)
// from the collective's COMPILED schedule tokens only (up_slot, ur_valid, sx_valid, ur_peer_slot, sx_peer_slot): no
// observed valid, credit, ready or arrival ever selects a slot.  Every event is a fixed offset from the compiled
// command; observed validity is checked by the masters as faults (CDC w_fault/r_fault, codec fault_cause/abort).
//
// Fixed timeline per TX channel (core slot presented at core cycle t; link cycles counted from the crossing flop):
//   CDC write          w_slot = slot (core t), addr = per-channel write count mod 64, version = lap parity
//   CDC read           link: slot crossed + KC flops -> r_slot;  o_valid/o_data 4 link edges later
//   codec write        wr_v = r_slot + 4 (with the CDC's word; wr_observed_v = CDC o_valid), slot = count mod 64
//   codec read         rd_v = wr_v + KW;  PHY frame 4 edges later (TX3 + pin)
// RX channel (the peer runs the identical calendar on the same compiled cycle numbering; exp = peer send slot):
//   rx_expect          link: exp crossed + KC + 4 + KW + 4 + PHY  (= the peer frame's pin cycle);  rx_v 2 later
//   CDC write          w_slot = rx_expect + 2 (i_valid = the codec's OBSERVED rx_v: a missing frame faults)
//   CDC read           core: r_slot = exp + (L - 4 - 2R);  o_valid/o_data at exp + L - R, + R relays = the collective's pin
//                      (R = on-die relay stages collective <-> face; this block is placed at the face, tokens relayed R)
// L = LU (UCIe P/R) or LS (SerDes): the collective's parameters; the composed bench measures the minimum L with no
// publication fault (tools/qwen_coll_tp8_static_links_bench.py) and the compiler prices exactly that.
// Core <-> link: the link roots are mesochronous with the core root (same PLL, fixed phase); the crossing flop of each
// 1-bit calendar token is a related-clock timed path (STA at the measured phase), the 514/546-bit records cross only
// through the static CDC SRAM with its publication check.  PHY = the PHY's fixed latency (off-chip, modelled).
// ---------------------------------------------------------------------------
module ot_coll_dly1 #(parameter integer N = 1) (input wire clk, input wire rs_n, input wire d, output wire q);
    generate if (N == 0) begin : g_wire
        assign q = d;
    end else begin : g_sr
        reg [N-1:0] sr;
        always @(posedge clk or negedge rs_n) if (!rs_n) sr <= {N{1'b0}}; else sr <= {sr, d};
        assign q = sr[N-1];
    end endgenerate
endmodule

// slot counter: 6-bit address + lap parity (version = 1 on lap 0: the CDC publication map resets to 0)
module ot_coll_slotcnt (input wire clk, input wire rs_n, input wire en, output wire [5:0] addr, output wire version);
    reg [6:0] c;
    always @(posedge clk or negedge rs_n) if (!rs_n) c <= 7'd0; else if (en) c <= c + 7'd1;
    assign addr = c[5:0];
    assign version = ~c[6];
endmodule

module ot_coll_lcal_tx #(parameter integer KC = 4, parameter integer KW = 2) (
    input  wire clk, lck, rs_c, rs_l,
    input  wire slot,                                       // core: compiled send slot
    output wire w_slot, output wire [5:0] w_addr, output wire w_version,
    output wire r_slot, output wire [5:0] r_addr, output wire r_version,
    output wire wr_v, output wire [5:0] wr_slot,
    output wire rd_v, output wire [5:0] rd_slot
);
    assign w_slot = slot;
    ot_coll_slotcnt u_wc (.clk(clk), .rs_n(rs_c), .en(slot), .addr(w_addr), .version(w_version));
    ot_coll_dly1 #(.N(KC)) u_x (.clk(lck), .rs_n(rs_l), .d(slot), .q(r_slot));   // first flop = the crossing
    ot_coll_slotcnt u_rc (.clk(lck), .rs_n(rs_l), .en(r_slot), .addr(r_addr), .version(r_version));
    ot_coll_dly1 #(.N(4)) u_w (.clk(lck), .rs_n(rs_l), .d(r_slot), .q(wr_v));
    wire unused_v1, unused_v2;
    ot_coll_slotcnt u_cw (.clk(lck), .rs_n(rs_l), .en(wr_v), .addr(wr_slot), .version(unused_v1));
    ot_coll_dly1 #(.N(KW)) u_r (.clk(lck), .rs_n(rs_l), .d(wr_v), .q(rd_v));
    ot_coll_slotcnt u_cr (.clk(lck), .rs_n(rs_l), .en(rd_v), .addr(rd_slot), .version(unused_v2));
endmodule

module ot_coll_lcal_rx #(parameter integer KC = 4, parameter integer KW = 2, parameter integer PHY = 14,
                         parameter integer L = 40, parameter integer R = 0, parameter integer PEER_R = R) (
    input  wire clk, lck, rs_c, rs_l,
    input  wire exp,                                        // core: the peer's compiled send slot
    output wire rx_expect_v, output wire [5:0] rx_expect_slot,
    output wire w_slot, output wire [5:0] w_addr, output wire w_version,
    output wire r_slot, output wire [5:0] r_addr, output wire r_version
);
    // R = on-die relay stages between the collective and this face (each direction; core domain, outside this block):
    // exp arrives R late and the CDC read word travels R back, so the read slot is exp + L - 4 - 2R
    initial if (L - 4 - 2 * R < 1) $error("ot_coll_lcal_rx: L - 4 - 2R >= 1");
    wire unused_v;
    // exp travelled local R; the peer frame travelled PEER_R before its CDC.
    // Opposite SerDes ports are paired 0<->2,1<->1; unequal placement ages
    // must adjust the expected PHY slot rather than invent a same-R path.
`ifdef OT_LCAL_MUT_PEER_AGE
    ot_coll_dly1 #(.N(KC + 4 + KW + 4 + PHY)) u_e
`else
    ot_coll_dly1 #(.N(KC + 4 + KW + 4 + PHY + PEER_R - R)) u_e
`endif (.clk(lck), .rs_n(rs_l), .d(exp), .q(rx_expect_v));
    ot_coll_slotcnt u_ec (.clk(lck), .rs_n(rs_l), .en(rx_expect_v), .addr(rx_expect_slot), .version(unused_v));
    ot_coll_dly1 #(.N(2)) u_w (.clk(lck), .rs_n(rs_l), .d(rx_expect_v), .q(w_slot));   // codec: pin capture 1 + RX 1
    ot_coll_slotcnt u_wc (.clk(lck), .rs_n(rs_l), .en(w_slot), .addr(w_addr), .version(w_version));
`ifdef OT_LCAL_MUT_RX_EARLY
    ot_coll_dly1 #(.N(L - 5 - 2 * R)) u_r (.clk(clk), .rs_n(rs_c), .d(exp), .q(r_slot));    // negative control: read 1 early
`else
    ot_coll_dly1 #(.N(L - 4 - 2 * R)) u_r (.clk(clk), .rs_n(rs_c), .d(exp), .q(r_slot));
`endif
    ot_coll_slotcnt u_rc (.clk(clk), .rs_n(rs_c), .en(r_slot), .addr(r_addr), .version(r_version));
endmodule

module ot_coll_static_linkcal #(
    parameter integer KC = 4,          // core slot -> TX CDC read slot, link flops incl. the crossing flop
    parameter integer KW = 2,          // codec write -> read
    parameter integer PU = 14,         // UCIe PHY latency (link cycles, modelled PHY)
    parameter integer PS = 339,        // SerDes board PHY latency
    parameter integer LU = 37,         // collective LU (core cycles, up register -> peer dp pin)
    parameter integer LS = 362,        // collective LS (sx register -> peer sr pin)
    parameter integer RU = 0,          // on-die relay stages collective <-> UCIe face (each direction)
    parameter integer RS0 = 0, RS1 = 0, RS2 = 0   // ... <-> SerDes face j (LS >= 362 + 2 max(RSj))
) (
    input  wire clk, lck, rst_n,
    // collective compiled tokens (core)
    input  wire up_slot, ur_slot, sx_slot, ur_peer_slot,
    input  wire [2:0] sx_peer_slot,
    // link epoch (link domain)
    output reg  epoch_begin,
    output wire [7:0] epoch,
    // TX CDC + codec: up (UCIe P), ur (UCIe R), sx0..2 (SerDes)
    output wire [4:0] tx_w_slot, tx_w_version, tx_r_slot, tx_r_version, tx_wr_v, tx_rd_v,
    output wire [29:0] tx_w_addr, tx_r_addr, tx_wr_slot, tx_rd_slot,
    // RX codec + CDC: dp (UCIe P), dr (UCIe R), sr0..2 (SerDes)
    output wire [4:0] rx_expect_v, rx_w_slot, rx_w_version, rx_r_slot, rx_r_version,
    output wire [29:0] rx_expect_slot, rx_w_addr, rx_r_addr
);
    wire rs_c, rs_l;
    ot_reset_sync u_rc (.clk(clk), .async_rst_n(rst_n), .sync_rst_n(rs_c));
    ot_reset_sync u_rl (.clk(lck), .async_rst_n(rst_n), .sync_rst_n(rs_l));
    // one epoch per reset: begins 2 link edges after the link reset release (before any compiled command)
    reg [1:0] ec;
    always @(posedge lck or negedge rs_l)
        if (!rs_l) begin ec <= 2'd0; epoch_begin <= 1'b0; end
        else begin
            if (ec != 2'd3) ec <= ec + 2'd1;
            epoch_begin <= (ec == 2'd1);
        end
    assign epoch = 8'h01;
    wire [4:0] txs = {sx_slot, sx_slot, sx_slot, ur_slot, up_slot};
    wire [4:0] rxe = {sx_peer_slot, ur_peer_slot, up_slot};       // P: the package peer sends exactly when I do
    genvar i;
    generate for (i = 0; i < 5; i = i + 1) begin : g_ch
        ot_coll_lcal_tx #(.KC(KC), .KW(KW)) u_tx (.clk(clk), .lck(lck), .rs_c(rs_c), .rs_l(rs_l), .slot(txs[i]),
            .w_slot(tx_w_slot[i]), .w_addr(tx_w_addr[6*i +: 6]), .w_version(tx_w_version[i]),
            .r_slot(tx_r_slot[i]), .r_addr(tx_r_addr[6*i +: 6]), .r_version(tx_r_version[i]),
            .wr_v(tx_wr_v[i]), .wr_slot(tx_wr_slot[6*i +: 6]), .rd_v(tx_rd_v[i]), .rd_slot(tx_rd_slot[6*i +: 6]));
        ot_coll_lcal_rx #(.KC(KC), .KW(KW), .PHY(i < 2 ? PU : PS), .L(i < 2 ? LU : LS),
            .R(i < 2 ? RU : i == 2 ? RS0 : i == 3 ? RS1 : RS2)) u_rx (.clk(clk), .lck(lck),
            .rs_c(rs_c), .rs_l(rs_l), .exp(rxe[i]),
            .rx_expect_v(rx_expect_v[i]), .rx_expect_slot(rx_expect_slot[6*i +: 6]),
            .w_slot(rx_w_slot[i]), .w_addr(rx_w_addr[6*i +: 6]), .w_version(rx_w_version[i]),
            .r_slot(rx_r_slot[i]), .r_addr(rx_r_addr[6*i +: 6]), .r_version(rx_r_version[i]));
    end endgenerate
endmodule
