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
module ot_coll_dly1 #(parameter integer N = 1, SAFE_RING = 0) (input wire clk, input wire rs_n, input wire d, output wire q);
    generate if (N == 0) begin : g_wire
        assign q = d;
    end else if (SAFE_RING && N >= 3) begin : g_ring
        // A pin-capture copy, a stationary ring, and registered read preserve
        // exactly N edges. Banks of <=16 tokens bound data/select fanout.
        // Only the pointer/warm-up/output reset; stale ring bits stay hidden.
        localparam integer D = N-2;
        localparam integer A = D>1 ? $clog2(D) : 1;
        localparam integer B = (D+15)/16;
        localparam integer H = A>4 ? A-4 : 1;
        reg [A-1:0] pos_q;
        reg [$clog2(N):0] filled_q;
        (* keep="true", dont_touch="true" *) reg [H-1:0] wr_bank_q,rd_bank_q;
        wire [B-1:0] bank_out;
        reg selected;
        reg out_q;
        always @(posedge clk) begin
            wr_bank_q <= pos_q>>4;
            rd_bank_q <= pos_q>>4;
        end
        for(genvar b=0;b<B;b=b+1)begin:g_bank
            localparam integer W = D-16*b<16 ? D-16*b : 16;
            reg [W-1:0] bits_q;
            (* keep="true", dont_touch="true" *) reg data_q;
            (* keep="true", dont_touch="true" *) reg [3:0] local_pos_q;
            always @(posedge clk) begin
                data_q<=d;
                local_pos_q<=pos_q;
                if(wr_bank_q==b && local_pos_q<W)
                    bits_q[local_pos_q]<=data_q;
            end
            assign bank_out[b]=local_pos_q<W ? bits_q[local_pos_q] : 1'b0;
        end
        always @* begin
            selected=1'b0;
            for(integer k=0;k<B;k=k+1)
                selected=selected | (bank_out[k] & (rd_bank_q==k));
        end
        always @(posedge clk or negedge rs_n) begin
            if(!rs_n) begin pos_q<=0;filled_q<=0;out_q<=0;end
            else begin
                pos_q <= pos_q==D-1 ? 0 : pos_q+1'b1;
                if(filled_q<N-1)filled_q<=filled_q+1'b1;
`ifdef OT_COLL_MUT_RING_EARLY
                out_q <= filled_q<N-2 ? 1'b0 : d;
`else
                out_q <= filled_q<N-1 ? 1'b0 : selected;
`endif
            end
        end
        assign q=out_q;
    end else begin : g_sr
        reg [N-1:0] sr;
        always @(posedge clk or negedge rs_n) if (!rs_n) sr <= {N{1'b0}}; else sr <= {sr, d};
        assign q = sr[N-1];
    end endgenerate
endmodule

// Four stationary token slots cross related regional roots. E=2 leaves two
// complete write/read phase windows; q is registered at the destination.
// Both reset copies have the same two-edge release depth. No flow control.
module ot_coll_token_landing(input wire ck_w,ck_r,rs_w,rs_r,d,output wire q);
    reg[3:0]bits_q;
    reg[1:0]wp_q,rp_q,warm_q;
    reg out_q;
    always @(posedge ck_w)if(rs_w)bits_q[wp_q]<=d;
    always @(posedge ck_w or negedge rs_w)
        if(!rs_w)wp_q<=0;else wp_q<=wp_q+1'b1;
    always @(posedge ck_r or negedge rs_r)begin
        if(!rs_r)begin rp_q<=0;warm_q<=0;out_q<=0;end
        else begin
            rp_q<=rp_q+1'b1;
            if(warm_q<2)warm_q<=warm_q+1'b1;
            out_q<=warm_q<2 ? 1'b0 : bits_q[(rp_q-2)&3];
        end
    end
`ifdef OT_COLL_MUT_LAND_UNLANDED
    assign q=d;
`else
    assign q=out_q;
`endif
endmodule

// slot counter: 6-bit address + lap parity (version = 1 on lap 0: the CDC publication map resets to 0)
module ot_coll_slotcnt (input wire clk, input wire rs_n, input wire en, output wire [5:0] addr, output wire version);
    reg [6:0] c;
    always @(posedge clk or negedge rs_n) if (!rs_n) c <= 7'd0; else if (en) c <= c + 7'd1;
    assign addr = c[5:0];
    assign version = ~c[6];
endmodule

module ot_coll_lcal_tx #(parameter integer KC = 4, parameter integer KW = 2, SAFE_RING = 0, LAND_CORE = 0) (
    input  wire clk, lck, rs_c, rs_l,
    input  wire slot,                                       // core: compiled send slot
    output wire w_slot, output wire [5:0] w_addr, output wire w_version,
    output wire r_slot, output wire [5:0] r_addr, output wire r_version,
    output wire wr_v, output wire [5:0] wr_slot,
    output wire rd_v, output wire [5:0] rd_slot
);
    assign w_slot = slot;
    ot_coll_slotcnt u_wc (.clk(clk), .rs_n(rs_c), .en(slot), .addr(w_addr), .version(w_version));
    if(LAND_CORE)begin:g_land_tx
        wire landed;
        initial if(KC<3)$error("landed calendar needs KC>=3");
        ot_coll_token_landing u_land(.ck_w(clk),.ck_r(lck),.rs_w(rs_c),.rs_r(rs_l),.d(slot),.q(landed));
        ot_coll_dly1 #(.N(KC-3),.SAFE_RING(SAFE_RING))u_tail(.clk(lck),.rs_n(rs_l),.d(landed),.q(r_slot));
    end else begin:g_direct_tx
        ot_coll_dly1 #(.N(KC),.SAFE_RING(SAFE_RING)) u_x (.clk(lck), .rs_n(rs_l), .d(slot), .q(r_slot));
    end
    ot_coll_slotcnt u_rc (.clk(lck), .rs_n(rs_l), .en(r_slot), .addr(r_addr), .version(r_version));
    ot_coll_dly1 #(.N(4),.SAFE_RING(SAFE_RING)) u_w (.clk(lck), .rs_n(rs_l), .d(r_slot), .q(wr_v));
    wire unused_v1, unused_v2;
    ot_coll_slotcnt u_cw (.clk(lck), .rs_n(rs_l), .en(wr_v), .addr(wr_slot), .version(unused_v1));
    ot_coll_dly1 #(.N(KW),.SAFE_RING(SAFE_RING)) u_r (.clk(lck), .rs_n(rs_l), .d(wr_v), .q(rd_v));
    ot_coll_slotcnt u_cr (.clk(lck), .rs_n(rs_l), .en(rd_v), .addr(rd_slot), .version(unused_v2));
endmodule

module ot_coll_lcal_rx #(parameter integer KC = 4, parameter integer KW = 2, parameter integer PHY = 14,
                         parameter integer L = 40, parameter integer R = 0, parameter integer PEER_R = R, SAFE_RING = 0, LAND_CORE = 0) (
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
    if(LAND_CORE)begin:g_land_rx
        wire landed;
        ot_coll_token_landing u_land(.ck_w(clk),.ck_r(lck),.rs_w(rs_c),.rs_r(rs_l),.d(exp),.q(landed));
`ifdef OT_LCAL_MUT_PEER_AGE
        ot_coll_dly1 #(.N(KC+4+KW+4+PHY-3),.SAFE_RING(SAFE_RING))u_tail(
`else
        ot_coll_dly1 #(.N(KC+4+KW+4+PHY+PEER_R-R-3),.SAFE_RING(SAFE_RING))u_tail(
`endif
            .clk(lck),.rs_n(rs_l),.d(landed),.q(rx_expect_v));
    end else begin:g_direct_rx
`ifdef OT_LCAL_MUT_PEER_AGE
    ot_coll_dly1 #(.N(KC + 4 + KW + 4 + PHY),.SAFE_RING(SAFE_RING)) u_e
`else
    ot_coll_dly1 #(.N(KC + 4 + KW + 4 + PHY + PEER_R - R),.SAFE_RING(SAFE_RING)) u_e
`endif (.clk(lck), .rs_n(rs_l), .d(exp), .q(rx_expect_v));
    end
    ot_coll_slotcnt u_ec (.clk(lck), .rs_n(rs_l), .en(rx_expect_v), .addr(rx_expect_slot), .version(unused_v));
    ot_coll_dly1 #(.N(2),.SAFE_RING(SAFE_RING)) u_w (.clk(lck), .rs_n(rs_l), .d(rx_expect_v), .q(w_slot));   // codec: pin capture 1 + RX 1
    ot_coll_slotcnt u_wc (.clk(lck), .rs_n(rs_l), .en(w_slot), .addr(w_addr), .version(w_version));
`ifdef OT_LCAL_MUT_RX_EARLY
    ot_coll_dly1 #(.N(L - 5 - 2 * R),.SAFE_RING(SAFE_RING)) u_r (.clk(clk), .rs_n(rs_c), .d(exp), .q(r_slot));    // negative control: read 1 early
`else
    ot_coll_dly1 #(.N(L - 4 - 2 * R),.SAFE_RING(SAFE_RING)) u_r (.clk(clk), .rs_n(rs_c), .d(exp), .q(r_slot));
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
