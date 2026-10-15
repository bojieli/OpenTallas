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
// Latency: TX +2 (SRAM read / pin-output and CRC metadata), RX +1 per direction.
// Replay data is bit-sliced into independently clocked leaves in the native
// implementation below; prefetch/write-through preserve this latency.
// MUT (bench only): 1 = CRC never checked, 2 = nak ignored, 3 = replay bank0 bit0 corrupted.
// ---------------------------------------------------------------------------------------------------------------------
module ot_qkvd_d2d_llr_ctl #(
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
    output reg           a_rx_v,
    output reg  [FW-1:0] a_rx_flit,
    // PHY side
    input  wire          p_tx_up,
    output reg           p_tx_v,
    output reg  [PW-1:0] p_tx_flit,
    input  wire          p_rx_v,
    input  wire [PW-1:0] p_rx_flit,
    output reg           fault,
    output reg  [2:0]    fault_cause,         // {nak timeout storm, queue overflow, ack out of window}
    output wire [$clog2(QD)-1:0] q_wa, q_ra,
    input wire [FW-1:0] q_dout
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
    // Storage lives in independently clocked bit-slice leaves.
    reg  [7:0]    wp, sp, ap;                            // write (next lseq), send, oldest unacked
    wire [7:0]    occ = wp - ap;
    wire          send_d = p_tx_up && (sp != wp);
    // received ack / nak (from a good flit of the far end)
    wire [7:0]    r_next = r_ackv ? r_aseq + 1'b1 : 8'd0;                     // first flit the far end still wants
    wire          r_win  = ((r_next - ap) <= occ);                             // inside [ap, wp]
    wire          g_ack = r_good && r_ackv && r_win;
    wire          g_nak = r_good && r_nak && (MUT != 2) && r_win;
    assign q_wa = wp[QA-1:0];
    // Prefetch the pointer that control will hold after this edge.
    // Same-edge enqueue/read forwards din in each bank.
    wire [7:0] pref_s = g_nak ? r_next : (send_d ? sp + 1'b1 : sp);
    assign q_ra = pref_s[QA-1:0];
    reg send_emit;
    reg [7:0] seq_emit;
    reg [PW-17:0] body;
    always @* begin
        body = {nak_req, ack_s, ack_have, send_emit, send_emit ? seq_emit : 8'd0, send_emit ? q_dout : {FW{1'b0}}};
    end
    reg f_ack, f_ovr, f_nak;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            a_tx_up <= 1'b0; p_tx_v <= 1'b0; p_tx_flit <= {PW{1'b0}}; a_rx_v <= 1'b0;
            send_emit <= 1'b0; seq_emit <= 8'd0;
            wp <= 8'd0; sp <= 8'd0; ap <= 8'd0; exp_s <= 8'd0; ack_have <= 1'b0;
            nak_req <= 1'b0; nak_sent <= 1'b0; nak_t <= 16'd0; f_ack <= 1'b0; f_ovr <= 1'b0; f_nak <= 1'b0;
            fault <= 1'b0; fault_cause <= 3'd0;
        end else begin
            // ---- TX ----
            send_emit <= send_d; seq_emit <= sp;
            a_tx_up <= p_tx_up && (occ < 8'(QD - GUARD));
            if (a_tx_v) begin
                wp <= wp + 1'b1;
                if (occ >= 8'(QD)) f_ovr <= 1'b1;
            end
            p_tx_v <= p_tx_up;
            if (p_tx_up) p_tx_flit <= {crc16(body), body};
            if (!p_tx_up) sp <= ap; // flush reserved send stage: retry every unacked flit on re-up
            else if (g_nak) sp <= r_next;                 // go back to the first flit the far end did not take
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

// Native64x137 replay is in a real64x512 SRAM; 431 wrapper flip-flops. No reset
// touches the payload array: occupancy/sequence control prevents invalid reads.
// SRAM read and pin-output registers are distinct. Control delays reserved
// send metadata by one edge to match the native read pipeline and prefetches its next
// send pointer and a write-through bypass covers enqueue into an empty queue.
// This partition still requires native physical timing before qualification.
module ot_qkvd_llr_replay_sram_leaf #(
    parameter integer W = 137, QD = 64,
    parameter integer QA = $clog2(QD), MUT = 0
) (
    input wire ck, we,
    input wire [QA-1:0] wa, ra,
    input wire [W-1:0] din,
    output reg [W-1:0] dout
);
    // Real 64x512 SRAM at the native64x137 shape. Unused columns are masked;
    // all readable queue words are written before their valid reservation.
    // Capture write pins, then commit to the SRAM. Track both collision ages
    // because the macro read is synchronous and read-before-write.
    reg wq, wqq;
    reg [QA-1:0] aq, aqq, rq;
    reg [W-1:0] dq, dqq;
    wire [511:0] mr;
    always @(posedge ck) begin
        wq <= we; aq <= wa; dq <= din;
        wqq <= wq; aqq <= aq; dqq <= dq;
        rq <= ra;
    end
    ot_sram_1r1w_64x512_m1_r2c2 u_sram (
        .clk(ck), .r_ce_in(1'b1), .r_addr_in(ra), .rd_out(mr),
        .w_ce_in(wq), .w_addr_in(aq), .wd_in({{(512-W){1'b0}},dq}),
        .w_mask_in({{(512-W){1'b0}},{W{1'b1}}}),
        .rr_en(2'd0), .rr_addr(12'd0), .cr_en(2'd0), .cr_sel(18'd0));
    always @(posedge ck)
        // A write arriving after this read reservation is forbidden by the
        // compiler ownership check. Bypass only the two captured write ages;
        // raw write pins must not feed the read-output D cones.
        dout <= (wq && aq == rq ? dq :
                 wqq && aqq == rq ? dqq : mr[W-1:0]) ^
            (MUT != 0 ? {{(W-1){1'b0}}, 1'b1} : {W{1'b0}});

endmodule

// ck[0] is the control entry, ck[1..4] the four storage entries. They belong
// to one logical domain, delivered independently at phi - each leaf's R.
// Predicted-address prefetch preserves one flit/edge throughput; TX adds one edge;
// retry and full-queue behavior must pass the production link bench.
module ot_qkvd_d2d_llr_split #(
    parameter integer FW = 548, QD = 64, GUARD = 8, NAKT = 64,
    parameter integer MUT = 0, PW = FW + 35
) (
    input wire [4:0] ck,
    input wire rst_n,
    output wire a_tx_up,
    input wire a_tx_v,
    input wire [FW-1:0] a_tx_flit,
    output wire a_rx_v,
    output wire [FW-1:0] a_rx_flit,
    input wire p_tx_up,
    output wire p_tx_v,
    output wire [PW-1:0] p_tx_flit,
    input wire p_rx_v,
    input wire [PW-1:0] p_rx_flit,
    output wire fault,
    output wire [2:0] fault_cause
);
    localparam integer BW = (FW + 3) / 4;
    wire [$clog2(QD)-1:0] wa, ra;
    wire [4*BW-1:0] padded_in = {{(4*BW-FW){1'b0}}, a_tx_flit};
    wire [4*BW-1:0] padded_out;
    ot_qkvd_d2d_llr_ctl #(.FW(FW), .QD(QD), .GUARD(GUARD), .NAKT(NAKT), .MUT(MUT), .PW(PW)) u_ctl (
        .clk(ck[0]), .rst_n(rst_n), .a_tx_up(a_tx_up), .a_tx_v(a_tx_v), .a_rx_v(a_rx_v), .a_rx_flit(a_rx_flit), .p_tx_up(p_tx_up), .p_tx_v(p_tx_v), .p_tx_flit(p_tx_flit), .p_rx_v(p_rx_v), .p_rx_flit(p_rx_flit), .fault(fault), .fault_cause(fault_cause),
        .q_wa(wa), .q_ra(ra), .q_dout(padded_out[FW-1:0]));
    for (genvar b = 0; b < 4; b = b + 1) begin : g_bank
        ot_qkvd_llr_replay_sram_leaf #(.W(BW), .QD(QD), .MUT(MUT == 3 && b == 0)) u_replay (
            .ck(ck[b+1]), .we(a_tx_v), .wa(wa), .ra(ra),
            .din(padded_in[b*BW +: BW]), .dout(padded_out[b*BW +: BW]));
    end
endmodule

// Historical single-clock API for existing benches/clients. Native die binding
// must use the split module's explicit entries, never this compatibility API.
module ot_qkvd_d2d_llr #(
    parameter integer FW = 548, QD = 64, GUARD = 8, NAKT = 64,
    parameter integer MUT = 0, PW = FW + 35
) (
    input wire clk, rst_n,
    output wire a_tx_up,
    input wire a_tx_v,
    input wire [FW-1:0] a_tx_flit,
    output wire a_rx_v,
    output wire [FW-1:0] a_rx_flit,
    input wire p_tx_up,
    output wire p_tx_v,
    output wire [PW-1:0] p_tx_flit,
    input wire p_rx_v,
    input wire [PW-1:0] p_rx_flit,
    output wire fault,
    output wire [2:0] fault_cause
);
    ot_qkvd_d2d_llr_split #(.FW(FW), .QD(QD), .GUARD(GUARD), .NAKT(NAKT), .MUT(MUT), .PW(PW)) u_split (
        .ck({5{clk}}), .rst_n(rst_n), .a_tx_up(a_tx_up), .a_tx_v(a_tx_v), .a_tx_flit(a_tx_flit), .a_rx_v(a_rx_v), .a_rx_flit(a_rx_flit), .p_tx_up(p_tx_up), .p_tx_v(p_tx_v), .p_tx_flit(p_tx_flit), .p_rx_v(p_rx_v), .p_rx_flit(p_rx_flit), .fault(fault), .fault_cause(fault_cause));
endmodule

// Retained predecessor for source-bound diagnostic kits only. Native wrappers
// instantiate the SRAM leaf above; this flop-mux leaf has not qualified.
module ot_qkvd_llr_replay_leaf #(
    parameter integer W = 137, QD = 64,
    parameter integer QA = $clog2(QD), MUT = 0
) (
    input wire ck, we,
    input wire [QA-1:0] wa, ra,
    input wire [W-1:0] din,
    output reg [W-1:0] dout
);
    // Expand storage before memory_dff: otherwise Yosys retimes the output
    // flops into six read-address flops, destroying the registered pin face.
    (* mem2reg *) reg [W-1:0] q [0:QD-1];
    // Capture the write face once at the pins instead of fanning each input
    // bit to all 64 words. The queued write commits a cycle later; two bypass
    // cases make that delay invisible to the predicted read pipeline.
    reg wq;
    reg [QA-1:0] aq;
    reg [W-1:0] dq;
    always @(posedge ck) begin
        wq <= we; aq <= wa; dq <= din;
        if (wq) q[aq] <= dq;
    end
    always @(posedge ck)
        dout <= (we && wa == ra ? din : (wq && aq == ra ? dq : q[ra])) ^
            (MUT != 0 ? {{(W-1){1'b0}}, 1'b1} : {W{1'b0}});
endmodule
