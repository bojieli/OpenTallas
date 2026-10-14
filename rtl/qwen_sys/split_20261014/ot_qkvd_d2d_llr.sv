`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// Qwen3-8B TP8 two-die split, die link: LINK-LEVEL RETRY + CRC (the UCIe D2D adapter's digital layer as real RTL,
// owner 2026-10-14 08:05 PT: no stubs, only the PHY analog may be a behavioural model).  One instance at each die end,
// between the link adapter (ot_qkvd_d2d / ot_qkvd_kv_end / ot_qkvd_rom_end: framing, per-class credits, its own
// sequence check) and the PHY macro's FDI.  Contract: results/arch/qwen_split_1014/LINK.md.
//
// PHY flit (PW = FW + 35): {crc 16 | nak 1, ack_seq 8, ack_v 1 | dv 1, lseq 8 | inner flit FW}
//   ack_seq = the last lseq delivered in order (cumulative; ack_v = at least one delivered); nak = resend everything
//   after ack_seq (from lseq 0 when ack_v = 0).
//   inner flit = the adapter's 548-b flit, carried unchanged; dv = 0 is an LLR idle (ack / nak only, no sequence).
//   crc = CRC-16/CCITT (x^16 + x^12 + x^5 + 1, init 0xFFFF) over every other bit of the PHY flit, MSB first.
// TX   every adapter flit (tx_v) is appended to a QD-deep replay queue and numbered lseq (mod 256); one PHY flit a
//      cycle while the macro is up: the oldest unsent queued flit, else an LLR idle.  A good received ack frees the
//      queue to ack_seq (cumulative); a good received nak rewinds the send pointer to the nak'd lseq (go-back-N).
//      The adapter's tx_up is withdrawn while the queue is within GUARD flits of full (its own pipeline still
//      delivers up to GUARD - 1 flits after that), so a replay never loses a flit; overflow is a sticky fault.
// RX   the PHY flit is captured at the pin; bad CRC, or a good data flit ahead of the expected lseq (a lost flit), asks
//      for a nak of the expected lseq (sent once, re-sent after NAKT cycles without progress); a good data flit at the
//      expected lseq is delivered (rx_v) and acknowledged; a duplicate (behind the expected lseq) is dropped.
// Latency: TX +1 (queue / CRC register), RX +1 (check register) per direction.
// MUT (bench only): 1 = CRC never checked (a corrupted flit is delivered), 2 = nak ignored (no replay).
// ---------------------------------------------------------------------------------------------------------------------
module ot_qkvd_d2d_llr #(
    parameter integer FW    = 548,
    parameter integer QD    = 64,
    parameter integer GUARD = 8,
    parameter integer NAKT  = 64,
    parameter integer MUT   = 0,
    parameter integer PW    = FW + 35
) (
    input  wire          clk,
    input  wire          rst_n,
    // adapter side (FDI as the adapter sees it)
    output reg           a_tx_up,
    input  wire          a_tx_v,
    input  wire [FW-1:0] a_tx_flit,
    output reg           a_rx_v,
    output reg  [FW-1:0] a_rx_flit,
    // PHY side
    input  wire          p_tx_up,
    output reg           p_tx_v,
    output reg  [PW-1:0] p_tx_flit,
    input  wire          p_rx_v,
    input  wire [PW-1:0] p_rx_flit,
    output reg           fault,
    output reg  [2:0]    fault_cause          // {nak timeout storm, queue overflow, ack out of window}
);
    localparam integer QA = $clog2(QD);
    function automatic [15:0] crc16(input [PW-17:0] d);
        integer i;
        reg [15:0] c;
        reg fb;
        begin
            c = 16'hFFFF;
            for (i = PW - 17; i >= 0; i = i - 1) begin
                fb = c[15] ^ d[i];
                c = {c[14:0], 1'b0} ^ (fb ? 16'h1021 : 16'h0000);
            end
            crc16 = c;
        end
    endfunction
    // ---------------- RX (captured at the pin) ----------------
    reg          rv;
    reg [PW-1:0] rf;
    always @(posedge clk) rf <= p_rx_flit;
    always @(posedge clk or negedge rst_n) if (!rst_n) rv <= 1'b0; else rv <= p_rx_v;
    wire [15:0]  r_crc  = rf[PW-1 -: 16];
    wire         r_nak  = rf[FW+18];
    wire [7:0]   r_aseq = rf[FW+17 -: 8];
    wire         r_ackv = rf[FW+9];
    wire         r_dv   = rf[FW+8];
    wire [7:0]   r_lseq = rf[FW+7 -: 8];
    wire         r_good = rv && ((MUT == 1) || crc16(rf[PW-17:0]) == r_crc);
    reg  [7:0]   exp_s;
    reg          ack_have, nak_req, nak_sent;
    wire [7:0]   ack_s = exp_s - 1'b1;
    reg  [15:0]  nak_t;
    wire [7:0]   ahead = r_lseq - exp_s;                 // 0 = expected, 1..127 = ahead (lost), else behind (duplicate)
    wire         r_take = r_good && r_dv && (ahead == 8'd0);
    wire         r_lost = rv && (!r_good || (r_dv && ahead != 8'd0 && ahead < 8'd128));
    // ---------------- TX replay queue ----------------
    reg  [FW-1:0] q [0:QD-1];
    reg  [7:0]    wp, sp, ap;                            // write (next lseq), send, oldest unacked
    wire [7:0]    occ = wp - ap;
    wire          send_d = p_tx_up && (sp != wp);
    // received ack / nak (from a good flit of the far end)
    wire [7:0]    r_next = r_ackv ? r_aseq + 1'b1 : 8'd0;                     // first flit the far end still wants
    wire          r_win  = ((r_next - ap) <= occ);                             // inside [ap, wp]
    wire          g_ack = r_good && r_ackv && r_win;
    wire          g_nak = r_good && r_nak && (MUT != 2) && r_win;
    always @(posedge clk) if (a_tx_v) q[wp[QA-1:0]] <= a_tx_flit;
    reg [PW-17:0] body;
    always @* begin
        body = {nak_req, ack_s, ack_have, send_d, send_d ? sp : 8'd0, send_d ? q[sp[QA-1:0]] : {FW{1'b0}}};
    end
    reg f_ack, f_ovr, f_nak;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            a_tx_up <= 1'b0; p_tx_v <= 1'b0; p_tx_flit <= {PW{1'b0}}; a_rx_v <= 1'b0;
            wp <= 8'd0; sp <= 8'd0; ap <= 8'd0; exp_s <= 8'd0; ack_have <= 1'b0;
            nak_req <= 1'b0; nak_sent <= 1'b0; nak_t <= 16'd0; f_ack <= 1'b0; f_ovr <= 1'b0; f_nak <= 1'b0;
            fault <= 1'b0; fault_cause <= 3'd0;
        end else begin
            // ---- TX ----
            a_tx_up <= p_tx_up && (occ < 8'(QD - GUARD));
            if (a_tx_v) begin
                wp <= wp + 1'b1;
                if (occ >= 8'(QD)) f_ovr <= 1'b1;
            end
            p_tx_v <= p_tx_up;
            if (p_tx_up) p_tx_flit <= {crc16(body), body};
            if (g_nak) sp <= r_next;                 // go back to the first flit the far end did not take
            else if (send_d) sp <= sp + 1'b1;
            if (g_ack) ap <= r_next;
            if (r_good && r_ackv && !r_win) f_ack <= 1'b1;
            if (p_tx_up && nak_req) nak_req <= 1'b0;     // the nak left in this flit
            // ---- RX ----
            a_rx_v <= r_take;
            if (r_take) begin
                a_rx_flit <= rf[FW-1:0];
                exp_s <= exp_s + 1'b1; ack_have <= 1'b1;
                nak_sent <= 1'b0; nak_t <= 16'd0;
            end else if (r_lost && !nak_sent) begin
                nak_req <= 1'b1; nak_sent <= 1'b1; nak_t <= 16'd0;
            end else if (nak_sent) begin
                nak_t <= nak_t + 1'b1;
                if (nak_t == 16'(NAKT)) begin nak_req <= 1'b1; nak_t <= 16'd0; end
                if (nak_t == 16'hFFFF) f_nak <= 1'b1;
            end
            fault_cause <= {f_nak, f_ovr, f_ack};
            fault <= f_nak | f_ovr | f_ack;
        end
endmodule
