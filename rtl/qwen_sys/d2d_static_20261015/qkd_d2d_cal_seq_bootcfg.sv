`timescale 1ns/1ps
// KV-DCAL-BOOTCFG 2026-10-19 (Qwen KV MU release die): the KV link end's calendar sequencer with the BOOT cfg merged in.
//
// Why: on the KV die the link end (qkd_d2ds) calendar cfg port has one producer, boot image target 11
// (qkd_static_kv_boot_dispatch LINKCFG=1, 66 words: TX/RX entries 0..31, then the TX and RX segment-1 bases = the
// ADMISSION segment).  But ot_qwen_d2d_cal_seq also writes the segment-1 base register at RUNTIME: at every epoch
// (e = 1, 2) back to SEG2, and after the admission run (E_SW, E_SW + 1) to SEG1 (the token run).  With the sequencer's
// cfg outputs load-less, every token run on the KV end replayed the admission segment.
//
// This tile = the qkd_d2d_cal_seq_pin input capture (reload / epoch_go / halt captured once, 2-edge reset release) around
// qkd_d2d_cal_seq (MU image, ot_qwen_d2d_cal_seq_dies_mu.sv; ot_qwen_d2d_cal_seq.sv unchanged) PLUS the boot cfg inputs
// bcfg_* (the dispatcher's link_cfg_*, pin-registered), and ONE output register stage on every output:
//   cfg_*   = the boot write when one arrives, else the sequencer's own writes AFTER its init stream (the inner init's
//             66 image writes are suppressed: boot target 11 loads the tables, so no compile-time table reaches the link)
//   others  = the sequencer's outputs, one edge later
// The inner sequencer counts its epoch anchor from EP_SKEW - 2 (pin version: EP_SKEW - 1), so with the output stage every
// epoch-anchored output (cal_start / cal_seg / layer / tok_start / adm_done / the runtime base writes) leaves on exactly
// the edge qkd_d2d_cal_seq_pin drives it (bench: cycle-equal to the pin tile).  The runtime base write keeps its 2-edge
// lead on the token start (the calendar's cfg settle rule).  One edge later than the pin tile: reset- and halt-relative
// outputs (init, cal_ready, halt stop; boot constants / exceptional paths) and the events counted from the strobe edge
// itself rather than the anchor (adm_done fall, the e = 1, 2 SEG2 restore writes; >= 60 edges before the admission).
//
// Sticky faults (folded into `fault`, registered; never stretch the schedule):
//   COL   a boot write and a sequencer write on the same edge
//   RUN   a boot write while a calendar runs (token programme running, or the admission run until adm_done)
//   STALE a boot base word (addr 6'b100000, TX then RX) != this tile's SEG2 constants (stale boot image vs the image
//         the sequencer's runtime base writes come from)
//   EARLY a calendar start before both boot base words arrived (since reset / the last reload)
//   (+ the sequencer's own faults)
// Static schedule: no ready / credit / backpressure.  MUT (bench only, 0 = shipped): 1 = sequencer writes never reach
// cfg_* (today's die: the base switch is lost).
module qkd_d2d_cal_seq_pin_bc #(parameter integer GO_OFS = 0, parameter [20*36-1:0] START_ADJ = '0,
                                parameter integer EP_SKEW = 3, parameter integer MUT = 0) (
    input  wire        ck, rst_n, reload, epoch_go, halt,
    input  wire        bcfg_tx_we, bcfg_rx_we,
    input  wire [5:0]  bcfg_addr,
    input  wire [31:0] bcfg_data,
    output reg         cfg_tx_we, cfg_rx_we,
    output reg  [5:0]  cfg_addr,
    output reg  [31:0] cfg_data,
    output reg         cal_start, cal_seg, cal_ready, running,
    output reg  [5:0]  layer,
    output reg         adm_done, tok_start,
    output reg         fault);
    `include "d2d_cal_image_mu.svh"
    initial if (EP_SKEW < 2) $error("EP_SKEW >= 2 needed (input capture + output stage)");
    // ---- input capture (as qkd_d2d_cal_seq_pin) + the boot cfg pin registers
    reg [1:0] release_q;
    reg reload_q, epoch_go_q, halt_q;
    reg b_tx_q, b_rx_q;
    reg [5:0] b_addr_q;
    reg [31:0] b_data_q;
    always @(posedge ck or negedge rst_n) begin
        if (!rst_n) begin
            release_q <= 0; reload_q <= 0; epoch_go_q <= 0; halt_q <= 1;
            b_tx_q <= 0; b_rx_q <= 0; b_addr_q <= 0; b_data_q <= 0;
        end else begin
            release_q <= {release_q[0], 1'b1};
            reload_q <= reload; epoch_go_q <= epoch_go; halt_q <= halt;
            b_tx_q <= bcfg_tx_we; b_rx_q <= bcfg_rx_we; b_addr_q <= bcfg_addr; b_data_q <= bcfg_data;
        end
    end
    wire rl = release_q[1];
    wire s_tx, s_rx, s_cs, s_seg, s_rdy, s_run, s_adm, s_tok, s_fault;
    wire [5:0] s_addr, s_layer;
    wire [31:0] s_data;
    qkd_d2d_cal_seq #(.GO_OFS(GO_OFS), .START_ADJ(START_ADJ), .EP_SKEW(EP_SKEW - 2)) u_seq (
        .ck(ck), .rst_n(rl), .reload(reload_q), .tok_go(1'b0), .epoch_go(epoch_go_q), .halt(halt_q),
        .cfg_tx_we(s_tx), .cfg_rx_we(s_rx), .cfg_addr(s_addr), .cfg_data(s_data),
        .cal_start(s_cs), .cal_seg(s_seg), .cal_ready(s_rdy), .running(s_run), .layer(s_layer),
        .adm_done(s_adm), .tok_start(s_tok), .fault(s_fault));
    // ---- merge: the sequencer's own writes only after its init stream.  The init's last write and cal_ready rise on the
    // same edge, so "after init" = cal_ready now AND one edge ago (a reload drops cal_ready with its first init write).
    reg rdy_q, adm_act, btx_seen, brx_seen;
    reg f_col, f_run, f_stale, f_early;      // fault cause (bench observability; `fault` is their OR with the sequencer's)
    wire s_we = (MUT == 1) ? 1'b0 : ((s_tx || s_rx) && s_rdy && rdy_q);
    wire b_we = b_tx_q || b_rx_q;
    wire b_base = b_we && (b_addr_q == 6'b100000);
    wire n_col = b_we && s_we;
    wire n_run = b_we && (s_run || adm_act);
    wire n_stale = b_base && (b_tx_q ? (b_data_q != D2D_CAL_K_TX_SEG2) : (b_data_q != D2D_CAL_K_RX_SEG2));
    wire n_early = s_cs && !(btx_seen && brx_seen);
    always @(posedge ck or negedge rl) begin
        if (!rl) begin
            cfg_tx_we <= 0; cfg_rx_we <= 0; cfg_addr <= 0; cfg_data <= 0;
            cal_start <= 0; cal_seg <= 0; cal_ready <= 0; running <= 0; layer <= 0; adm_done <= 0; tok_start <= 0;
            rdy_q <= 0; adm_act <= 0; btx_seen <= 0; brx_seen <= 0;
            f_col <= 0; f_run <= 0; f_stale <= 0; f_early <= 0; fault <= 0;
        end else begin
            cal_start <= s_cs; cal_seg <= s_seg; cal_ready <= s_rdy; running <= s_run; layer <= s_layer;
            adm_done <= s_adm; tok_start <= s_tok;
            rdy_q <= s_rdy;
            if (b_we) begin
                cfg_tx_we <= b_tx_q; cfg_rx_we <= b_rx_q; cfg_addr <= b_addr_q; cfg_data <= b_data_q;
            end else begin
                cfg_tx_we <= s_we && s_tx; cfg_rx_we <= s_we && s_rx;
                if (s_we) begin cfg_addr <= s_addr; cfg_data <= s_data; end
            end
            // admission run: from its start (layer 63) until adm_done; the token programme is the sequencer's `running`
            if (s_cs && s_seg && s_layer == 6'h3f) adm_act <= 1'b1;
            else if (s_adm || halt_q) adm_act <= 1'b0;
            if (reload_q) begin btx_seen <= 1'b0; brx_seen <= 1'b0; end
            else begin
                if (b_base && b_tx_q) btx_seen <= 1'b1;
                if (b_base && b_rx_q) brx_seen <= 1'b1;
            end
            if (n_col) f_col <= 1'b1;
            if (n_run) f_run <= 1'b1;
            if (n_stale) f_stale <= 1'b1;
            if (n_early) f_early <= 1'b1;
            fault <= fault || s_fault || n_col || n_run || n_stale || n_early;
        end
    end
endmodule
