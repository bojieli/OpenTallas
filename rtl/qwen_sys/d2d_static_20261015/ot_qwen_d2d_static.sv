`timescale 1ns/1ps
// =====================================================================================================================
// Qwen3-8B TP8 two-die split: STATIC die-to-die link end (Q-LINK, 2026-10-15). One instance on EACH die (compute die
// qfd_d2d_static, KV/system die qkd_d2d_static); replaces the credit adapters ot_qfd_split_romlink / ot_qkvd_kv_end and
// the go-back-N LLR (historical under owner rule 0ah, 2026-10-14 18:59: static cycle schedule, no credits/backpressure).
//
// PHY word (both dies, UCIe-A x64 FDI): PW = 583 = payload 548 + 19 frame bits + CRC16 (ot_qwen_static_slot_link).
// The old 548-wide KV-die FDI net and the 583 = 548 + 35 LLR header of the compute die are both retired.
//
// NORMAL MODE (production): every frame is reserved by the compiler.
//   * Two calendars per end (TX, RX), each a compiler image of 32-b entries {dt14, last1, port3, kind4, beat5, 0}:
//     event i fires dt_0 + .. + dt_i cycles after the compiled cal_start strobe. At most one TX and one RX event per
//     cycle (the PHY carries one frame per cycle per direction). No valid, ready, credit or arrival selects a cycle.
//   * TX event at cycle c: tx_slot[p] / tx_kind / tx_beat go to producer p's typed codec at c (its tx_expected); that
//     codec's registered record is captured TXD_p edges later into the slot SRAM (wr), read one edge after (rd), and
//     the frame leaves the pins TX3 later. Write/read slot numbers are the per-epoch frame count mod 64 on both ends.
//   * RX event at cycle r = the compiler's pin-arrival cycle of the peer frame: rx_expect at r, checked payload and
//     rx_event[p] / rx_slot[p] (the compiled expectation, separately) at r + 2.
//   * Faults (CRC, slot/epoch mismatch, missing/unexpected frame, ownership, stray producer, calendar overrun) never
//     stretch the schedule: they abort the epoch.
// EXCEPTIONAL MODE (explicit, measured; never part of a normal timeline): see ot_qwen_d2d_recovery.
//   abort -> calendars halt -> DRAIN quiet cycles (links_drained) -> HOST link reset request -> both PHYs reset
//   (link_reset_seen) -> retrain (retrained) -> HOST recovery_clear -> forwarded epoch strobe -> both ends begin
//   epoch+1 on the same compiled cycle -> the HOST replays the aborted token from its checkpoint. No transparent
//   retransmission exists in the normal path.
// =====================================================================================================================

// ---------------------------------------------------------------------------------------------------------------------
// Calendar playback: a compiler image in a register file, written only while stopped (init / recovery mode).
// ---------------------------------------------------------------------------------------------------------------------
module ot_qwen_d2d_cal #(parameter integer NE = 128, parameter integer AW = $clog2(NE)) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire          cfg_we,
    input  wire [AW-1:0] cfg_addr,
    input  wire [31:0]   cfg_data,
    input  wire          start,          // compiled start strobe (one cycle)
    input  wire          halt,           // epoch abort: stop at once
    output reg           ev_v,
    output reg  [2:0]    ev_port,
    output reg  [3:0]    ev_kind,
    output reg  [4:0]    ev_beat,
    output reg           running,
    output reg           fault           // sticky: start while running, cfg while running, dt 0, table overrun
);
    reg [31:0]   tbl [0:NE-1];
    reg [31:0]   cur;
    reg [13:0]   cnt;
    reg [AW:0]   ptr;
    always @(posedge ck) if (cfg_we && !running) tbl[cfg_addr] <= cfg_data;
    wire [31:0] nxt = tbl[ptr[AW-1:0]];
    always @(posedge ck or negedge rst_n) begin
        if (!rst_n) begin
            running <= 1'b0; ev_v <= 1'b0; ev_port <= 3'd0; ev_kind <= 4'd0; ev_beat <= 5'd0;
            cur <= 32'd0; cnt <= 14'd0; ptr <= 0; fault <= 1'b0;
        end else begin
            ev_v <= 1'b0;
            if (cfg_we && running) fault <= 1'b1;
            if (halt) running <= 1'b0;
            else if (start) begin
                if (running) fault <= 1'b1;
                running <= 1'b1;
                cur <= tbl[0]; cnt <= tbl[0][31:18]; ptr <= 1;
                if (tbl[0][31:18] == 14'd0) fault <= 1'b1;
            end else if (running) begin
                if (cnt == 14'd1) begin
                    ev_v <= 1'b1; ev_port <= cur[16:14]; ev_kind <= cur[13:10]; ev_beat <= cur[9:5];
                    if (cur[17]) running <= 1'b0;
                    else begin
                        if (ptr == NE) fault <= 1'b1;
                        if (nxt[31:18] == 14'd0) fault <= 1'b1;
                        cur <= nxt; cnt <= nxt[31:18]; ptr <= ptr + 1'b1;
                    end
                end else cnt <= cnt - 1'b1;
            end
        end
    end
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// Link end: two calendars + per-port fixed producer delays + real SRAM/CRC slot link (ot_qwen_static_slot_link).
// ---------------------------------------------------------------------------------------------------------------------
module ot_qwen_d2d_static_end #(
    parameter integer NT = 4, NR = 4, FW = 548, CW = 16, PW = FW + 19 + CW, NE = 128,
    parameter [8*4-1:0] TXD = {8'd1, 8'd1, 8'd2, 8'd1},   // per TX port codec latency (port p = byte p), 1..8
    parameter integer MUT = 0      // bench: 1 = TX write slot off by one (lap ownership), 2 = RX demux port 0<->1
) (
    input  wire [4:0]       ck,           // [0] control + calendars, [1..4] SRAM bank entries (one logical domain)
    input  wire             rst_n,
    input  wire             cfg_tx_we, cfg_rx_we,
    input  wire [6:0]       cfg_addr,
    input  wire [31:0]      cfg_data,
    input  wire             epoch_begin,
    input  wire [7:0]       epoch,
    input  wire             cal_start,
    // producer face
    output wire [NT-1:0]    tx_slot,
    output wire [3:0]       tx_kind,
    output wire [4:0]       tx_beat,
    input  wire [NT-1:0]    tx_valid,
    input  wire [NT*FW-1:0] tx_payload,
    // consumer face
    output reg  [NR-1:0]    rx_event,     // observed: checked frame for port p
    output reg  [NR-1:0]    rx_slot,      // compiled expectation for port p (same cycle)
    output reg  [3:0]       rx_kind,
    output reg  [4:0]       rx_beat,
    output wire [FW-1:0]    rx_payload,
    // PHY FDI
    input  wire             p_tx_up,
    output wire             p_tx_v,
    output wire [PW-1:0]    p_tx_flit,
    input  wire             p_rx_v,
    input  wire [PW-1:0]    p_rx_flit,
    output wire             epoch_abort,
    output wire [7:0]       fault_cause,  // slot link: {ownership, collision, unread, tx_not_up, unexpected, missing, slot, crc}
    output reg              end_fault,    // calendar / stray producer / port collision (sticky until epoch_begin)
    output wire             cal_running
);
    wire halt = epoch_abort | end_fault;
    wire tv, rv; wire [2:0] tp, rp; wire [3:0] tk, rk; wire [4:0] tb, rb; wire tf, rf, trun, rrun;
    ot_qwen_d2d_cal #(.NE(NE)) u_txcal (.ck(ck[0]), .rst_n(rst_n), .cfg_we(cfg_tx_we), .cfg_addr(cfg_addr),
        .cfg_data(cfg_data), .start(cal_start), .halt(halt), .ev_v(tv), .ev_port(tp), .ev_kind(tk), .ev_beat(tb),
        .running(trun), .fault(tf));
    ot_qwen_d2d_cal #(.NE(NE)) u_rxcal (.ck(ck[0]), .rst_n(rst_n), .cfg_we(cfg_rx_we), .cfg_addr(cfg_addr),
        .cfg_data(cfg_data), .start(cal_start), .halt(halt), .ev_v(rv), .ev_port(rp), .ev_kind(rk), .ev_beat(rb),
        .running(rrun), .fault(rf));
    assign cal_running = trun | rrun;
    genvar p;
    for (p = 0; p < NT; p = p + 1) begin : g_slot
        assign tx_slot[p] = tv && tp == p;
    end
    assign tx_kind = tk;
    assign tx_beat = tb;
    // per-port fixed capture delay: the codec's registered record is present TXD_p edges after its slot
    reg [NT-1:0] fire;
    for (p = 0; p < NT; p = p + 1) begin : g_dly
        localparam integer D = TXD[8*p +: 8];
        reg [D-1:0] sr;
        always @(posedge ck[0] or negedge rst_n)
            if (!rst_n) sr <= {D{1'b0}};
            else sr <= {sr, tx_slot[p] & ~halt};
        always @* fire[p] = sr[D-1];
    end
    integer i, j, k;
    reg [FW-1:0] wsel;
    reg          wobs;
    wire         multi = |(fire & (fire - 1'b1));
    always @* begin
        wsel = {FW{1'b0}}; wobs = 1'b0;
        for (j = 0; j < NT; j = j + 1) if (fire[j]) begin
            wsel = wsel | tx_payload[j*FW +: FW];
            wobs = wobs | tx_valid[j];
        end
    end
    wire wr_v = |fire;
    // a producer presenting a record outside its reserved capture edge is a stray (schedule fault)
    wire stray = |(tx_valid & ~fire);
    reg [5:0] wcnt, rcnt, rslot; reg rd_v;
    wire [5:0] wslot = (MUT == 1) ? wcnt + 6'd1 : wcnt;
    // RX expectation and its 2-edge alignment with the slot link's checked output
    reg [5:0] ecnt;
    reg       r1v, r2v; reg [2:0] r1p, r2p; reg [3:0] r1k; reg [4:0] r1b;
    always @(posedge ck[0] or negedge rst_n) begin
        if (!rst_n) begin
            wcnt <= 0; rcnt <= 0; rslot <= 0; rd_v <= 0; ecnt <= 0; end_fault <= 0;
            r1v <= 0; r2v <= 0; r1p <= 0; r2p <= 0; r1k <= 0; r1b <= 0;
            rx_slot <= 0; rx_kind <= 0; rx_beat <= 0;
        end else if (epoch_begin) begin
            wcnt <= 0; rcnt <= 0; rd_v <= 0; ecnt <= 0; end_fault <= 0; r1v <= 0; r2v <= 0;
            rx_slot <= 0;
        end else begin
            if (wr_v) wcnt <= wcnt + 6'd1;
            rd_v <= wr_v & ~halt; rslot <= wslot;
            if (rv) ecnt <= ecnt + 6'd1;
            if (stray | multi | tf | rf) end_fault <= 1'b1;
            r1v <= rv; r1p <= rp; r1k <= rk; r1b <= rb;
            r2v <= r1v; r2p <= (MUT == 2 && r1p < 2) ? r1p ^ 3'd1 : r1p;
            rx_kind <= r1k; rx_beat <= r1b;
            for (i = 0; i < NR; i = i + 1) rx_slot[i] <= r1v && r1p == i;
        end
    end
    wire lrx_v;
    always @* for (k = 0; k < NR; k = k + 1) rx_event[k] = lrx_v && r2p == k;
    ot_qwen_static_slot_link #(.FW(FW), .CW(CW), .PW(PW)) u_link (
        .ck(ck), .rst_n(rst_n), .epoch_begin(epoch_begin), .epoch(epoch),
        .wr_v(wr_v & ~halt), .wr_observed_v(wobs), .wr_slot(wslot), .wr_flit(wsel),
        .rd_v(rd_v), .rd_slot(rslot),
        .rx_expect_v(rv), .rx_expect_slot(ecnt),
        .p_tx_up(p_tx_up), .p_tx_v(p_tx_v), .p_tx_flit(p_tx_flit), .p_rx_v(p_rx_v), .p_rx_flit(p_rx_flit),
        .rx_v(lrx_v), .rx_flit(rx_payload), .epoch_abort(epoch_abort), .fault_cause(fault_cause));
endmodule
