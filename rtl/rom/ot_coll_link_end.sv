`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// qwen-coll-io 2026-10-14: link-level credit termination for one board (SerDes) port of the TP8 collective.
//
// Why: the collective engine (ot_rom_oneshot_die_m) holds DEPTH = 32 credits per destination and its receive FIFO is
// 32 words deep.  With the engine's credit loop closed END TO END over the board link (one-way LAT 339 cycles,
// round trip ~700), a 128-word owner half needs 4 credit round trips: the native TP8 WT1 composition measures
// AR256 2,587 cycles at LAT 339 against the 1,121-cycle AR price (2.31x).  The fix is structural: terminate the
// engine's credit loop locally and run a link-level credit loop whose receive buffer covers the whole owner half
// (bandwidth-delay product of one all-reduce), so a half is posted at once and no word waits for a board round trip.
//
// Two halves, one per direction, both at the die's link end (the io_xfifo SerDes channels / the collective's
// SerDes face; same clock here, the CDC is the xfifo's):
//   TX (engine -> link): no storage.  The converter mirrors the credits the engine holds (G, <= EC = the engine's
//      DEPTH) and the link credits it holds (A, <= LC = the far receive buffer).  It grants the engine a credit back
//      whenever A > G and G < EC, so the engine can never send a word the far buffer cannot take (G <= A always).
//      Words pass through one register (pin flop at the link face).
//   RX (link -> engine): an LC-word credit-managed queue (ot_coll_tp8_q, LC / 32 macros of 32 x 546).  A word
//      leaves for the engine only with an engine credit in hand (EA, init EC, +1 per engine cr_out); every word that
//      leaves returns one link credit to the far sender.
// Order and values are preserved exactly; the engine sees the same word stream on every port.  Latency: TX +1,
// RX +3 edges (pin capture, queue head, launch).  Faults (sticky): link word into a full buffer (far sender ignored
// credits), engine credit overflow (more engine credits returned than EC), queue overflow.
// Negative controls (bench only): OT_LINKEND_MUT_NOGATE (TX grants ignore the link credits) and OT_LINKEND_MUT_RXNOGATE
// (RX releases words without engine credits) must overflow a receive buffer and fault under skew.
// ---------------------------------------------------------------------------
module ot_coll_link_end #(
    parameter integer PW  = 546,
    parameter integer EC  = 32,     // engine credits per destination (the engine's DEPTH)
    parameter integer LC  = 128,    // link credits = far receive buffer words (32 * 2^k)
    parameter integer MEM = 1
) (
    input  wire          clk,
    input  wire          rst_n,
    // TX: engine side
    input  wire          e_tx_v,
    input  wire [PW-1:0] e_tx_rec,
    output wire          e_tx_cr,      // credit pulse to the engine (its cr_in for this destination)
    // TX: link side
    output wire          l_tx_v,
    output wire [PW-1:0] l_tx_rec,
    input  wire          l_tx_cr,      // link credit back from the far receive buffer
    // RX: link side
    input  wire          l_rx_v,
    input  wire [PW-1:0] l_rx_rec,
    output wire          l_rx_cr,      // link credit to the far sender (one per word leaving the buffer)
    // RX: engine side
    output wire          e_rx_v,
    output wire [PW-1:0] e_rx_rec,
    input  wire          e_rx_cr,      // engine credit back (its cr_out for this source)
    output wire          fault
);
    localparam integer CW = $clog2(LC + 1) + 1;
    initial if (EC > LC || EC < 1) $error("ot_coll_link_end: 1 <= EC <= LC");
    wire rs;
    (* keep_hierarchy *) ot_coll_rst_leaf u_rs (.clk(clk), .arst_n(rst_n), .q(rs));

    // ---------------- TX ----------------
    reg          tv_q, tc_q, lcr_q, f_tx;
    reg [PW-1:0] tr_q;
    reg [CW-1:0] a, g;
`ifdef OT_LINKEND_MUT_NOGATE
    wire grant = (g < EC);
`else
    wire grant = (a > g) && (g < EC);
`endif
    always @(posedge clk) tr_q <= e_tx_rec;
    always @(posedge clk or negedge rs)
        if (!rs) begin tv_q <= 1'b0; tc_q <= 1'b0; lcr_q <= 1'b0; a <= LC; g <= EC; f_tx <= 1'b0; end
        else begin
            tv_q  <= e_tx_v;
            lcr_q <= l_tx_cr;
            tc_q  <= grant;
            // the engine's word consumes one granted and one link credit; a link credit back restores one
            a <= a - (e_tx_v ? 1'b1 : 1'b0) + (lcr_q ? 1'b1 : 1'b0);
            g <= g - (e_tx_v ? 1'b1 : 1'b0) + (grant ? 1'b1 : 1'b0);
            if ((e_tx_v && (g == 0 || a == 0)) || a > LC) f_tx <= 1'b1;
        end
    assign l_tx_v = tv_q; assign l_tx_rec = tr_q; assign e_tx_cr = tc_q;

    // ---------------- RX ----------------
    reg          rv_q, ecr_q, ov_q, lc_q, f_rx;
    reg [PW-1:0] rr_q, od_q;
    reg [CW-1:0] ea;
    wire         q_hv, q_ovf;
    wire [PW-1:0] q_hd;
`ifdef OT_LINKEND_MUT_RXNOGATE
    wire         pop = q_hv;                 // mutant: words leave without an engine credit
`else
    wire         pop = q_hv && (ea != 0);
`endif
    always @(posedge clk) begin rr_q <= l_rx_rec; od_q <= q_hd; end
    ot_coll_tp8_q #(.W(PW), .D(LC), .MEM(MEM)) u_q (.clk(clk), .rst_n(rst_n), .push(rv_q), .wd(rr_q), .pop(pop),
        .hv(q_hv), .hd(q_hd), .ovf(q_ovf));
    always @(posedge clk or negedge rs)
        if (!rs) begin rv_q <= 1'b0; ecr_q <= 1'b0; ov_q <= 1'b0; lc_q <= 1'b0; ea <= EC; f_rx <= 1'b0; end
        else begin
            rv_q  <= l_rx_v;
            ecr_q <= e_rx_cr;
            ov_q  <= pop;
            lc_q  <= pop;
            ea    <= ea - (pop ? 1'b1 : 1'b0) + (ecr_q ? 1'b1 : 1'b0);
            if (ea > EC) f_rx <= 1'b1;
        end
    assign e_rx_v = ov_q; assign e_rx_rec = od_q; assign l_rx_cr = lc_q;
    assign fault = f_tx | f_rx | q_ovf;
endmodule
