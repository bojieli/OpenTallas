`timescale 1ns/1ps
// =====================================================================================================================
// MU-D2D-OVL 2026-10-19 (coordinator 0ki): calendar sequencer for OVERLAPPING request / response link segments.
// One instance beside each OVL link end (compute qfd_d2d_static_ovl, KV qkd_d2d_static_ovl); it is the only producer of
// the end's cfg_* / cal_start / cal_seg / cal_start_rx / cal_seg_rx / cal_user_tx / cal_user_rx inputs.
//   INIT + ADMISSION: the unchanged ot_qwen_d2d_cal_seq (images as constants, ADM run once per epoch, token starts
//     disabled: tok_go 0, AUTO 0); its cal_start starts BOTH directions (user 0), as in the as-built end.
//   NORMAL MODE: two start-list players (TX, RX), each reading its compiled list from a ROM port (one 32-b word an
//     entry, tools/qwen_static_schedule/mu_d2d_ovl.py):  [31:12] dt (edges after the previous entry; the first entry
//     counts from the anchor), [11] go (0 = wait-only entry), [10] seg, [9:8] user, [7] wrap (the next entry is word 0:
//     the frame repeats), [6:0] 0.  Both players start on the anchor edge = FIRST_OFS edges after the epoch strobe
//     (EP_SKEW aligns the two dies on one absolute edge, as ot_qwen_d2d_cal_seq AUTO), so every start of both dies is
//     a compiled absolute edge.  No valid / ready / credit selects a cycle.
//   FAULTS (sticky): an entry with dt < 4 or nonzero reserved bits, a list word not prefetched in time, the anchor
//     before cal_ready / adm_done or while the players run, an admission start and a list start on one edge, a list
//     start while the end's playhead of that direction runs (that one is the calendar's own fault in the end:
//     collision = fault).  halt (the end's epoch_abort) stops both players; the next epoch strobe re-anchors.
// ROM ports: synchronous read (q = mem[addr] one edge after addr); the die GEN binds one ROM macro per list.
// =====================================================================================================================
module ot_qwen_d2d_list_play #(parameter integer AW = 11, parameter integer MIN_DT = 4) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire          go,            // anchor: entry 0's dt counts from this edge
    input  wire          halt,
    output wire [AW-1:0] rom_addr,
    input  wire [31:0]   rom_q,
    output reg           start,
    output reg           seg,
    output reg  [1:0]    user,
    output reg           running,
    output reg           fault
);
    reg [AW-1:0] addr;
    reg [31:0]   nxt;
    reg          nv;
    reg [1:0]    age;
    reg [19:0]   cnt;
    reg [31:0]   cur;
    assign rom_addr = addr;
    wire bad_n = (nxt[31:12] < MIN_DT) || (|nxt[6:0]);
    always @(posedge ck or negedge rst_n) begin
        if (!rst_n) begin
            addr <= '0; nxt <= 32'd0; nv <= 1'b0; age <= 2'd0; cnt <= 20'd0; cur <= 32'd0;
            start <= 1'b0; seg <= 1'b0; user <= 2'd0; running <= 1'b0; fault <= 1'b0;
        end else begin
            start <= 1'b0;
            // prefetch: the ROM word of addr is stable two edges after addr moved
            if (!nv) begin
                if (age == 2'd2) begin nxt <= rom_q; nv <= 1'b1; end
                else age <= age + 2'd1;
            end
            if (halt) running <= 1'b0;
            else if (go || (running && cnt == 20'd1)) begin
                if (go && running) fault <= 1'b1;
                if (!go && cur[11]) begin start <= 1'b1; seg <= cur[10]; user <= cur[9:8]; end
                if (!nv || bad_n) fault <= 1'b1;
                running <= 1'b1;
                cur <= nxt; cnt <= nxt[31:12]; nv <= 1'b0; age <= 2'd0;
                addr <= nxt[7] ? '0 : addr + 1'b1;
            end else if (running) cnt <= cnt - 20'd1;
        end
    end
endmodule

module ot_qwen_d2d_ovl_seq #(
    parameter integer NE = 32,
    parameter integer AW = 11,           // list ROM address width (2,048 words: one 4-user frame is 1,703 a list)
    parameter [32*NE-1:0] TX_IMG = '0,
    parameter [32*NE-1:0] RX_IMG = '0,
    parameter [31:0]      TX_SEG1 = '0,  // segment-1 bases (token head); ADM = 1: the admission bases first
    parameter [31:0]      RX_SEG1 = '0,
    parameter integer ADM = 0,
    parameter [31:0]      TX_SEG2 = '0,
    parameter [31:0]      RX_SEG2 = '0,
    parameter integer ADM_OFS = 72,
    parameter integer ADM_LEN = 1100,
    parameter integer FIRST_OFS = 1176,  // anchor edge of the start lists, edges after the anchored epoch strobe
    parameter integer EP_SKEW = 0
) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire          reload,
    input  wire          epoch_go,
    input  wire          halt,
    output wire          cfg_tx_we,
    output wire          cfg_rx_we,
    output wire [5:0]    cfg_addr,
    output wire [31:0]   cfg_data,
    output wire          cal_start,
    output wire          cal_seg,
    output wire          cal_start_rx,
    output wire          cal_seg_rx,
    output wire [1:0]    cal_user_tx,
    output wire [1:0]    cal_user_rx,
    output wire [AW-1:0] tx_rom_addr,
    input  wire [31:0]   tx_rom_q,
    output wire [AW-1:0] rx_rom_addr,
    input  wire [31:0]   rx_rom_q,
    output wire          cal_ready,
    output wire          adm_done,
    output wire          running,
    output reg           fault
);
    localparam integer E_GO = EP_SKEW + FIRST_OFS;
    wire s_start, s_seg, s_run, s_fault, s_ready, s_adm;
    ot_qwen_d2d_cal_seq #(.NE(NE), .NL(1), .TX_IMG(TX_IMG), .RX_IMG(RX_IMG), .TX_SEG1(TX_SEG1), .RX_SEG1(RX_SEG1),
        .START('0), .ADM(ADM), .TX_SEG2(TX_SEG2), .RX_SEG2(RX_SEG2), .ADM_OFS(ADM_OFS), .ADM_LEN(ADM_LEN), .AUTO(0),
        .EP_SKEW(EP_SKEW)) u_seq (
        .ck(ck), .rst_n(rst_n), .reload(reload), .tok_go(1'b0), .epoch_go(epoch_go), .halt(halt),
        .cfg_tx_we(cfg_tx_we), .cfg_rx_we(cfg_rx_we), .cfg_addr(cfg_addr), .cfg_data(cfg_data),
        .cal_start(s_start), .cal_seg(s_seg), .cal_ready(s_ready), .running(s_run), .layer(), .adm_done(s_adm),
        .tok_start(), .fault(s_fault));
    assign cal_ready = s_ready;
    assign adm_done = s_adm;
    // anchor: the epoch strobe's rising edge + E_GO edges (the same absolute edge on both dies)
    reg ep_q, act; reg [31:0] e;
    wire go = act && e == E_GO;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin ep_q <= 1'b0; act <= 1'b0; e <= 32'd0; end
        else begin
            ep_q <= epoch_go;
            if (halt) act <= 1'b0;
            else if (epoch_go && !ep_q) begin act <= 1'b1; e <= 32'd1; end
            else if (act) begin e <= e + 32'd1; if (go) act <= 1'b0; end
        end
    wire t_start, t_seg, r_start, r_seg, t_run, r_run, t_f, r_f; wire [1:0] t_u, r_u;
    ot_qwen_d2d_list_play #(.AW(AW)) u_tx (.ck(ck), .rst_n(rst_n), .go(go), .halt(halt), .rom_addr(tx_rom_addr),
        .rom_q(tx_rom_q), .start(t_start), .seg(t_seg), .user(t_u), .running(t_run), .fault(t_f));
    ot_qwen_d2d_list_play #(.AW(AW)) u_rx (.ck(ck), .rst_n(rst_n), .go(go), .halt(halt), .rom_addr(rx_rom_addr),
        .rom_q(rx_rom_q), .start(r_start), .seg(r_seg), .user(r_u), .running(r_run), .fault(r_f));
    assign cal_start    = s_start | t_start;
    assign cal_seg      = s_start ? s_seg : t_seg;
    assign cal_start_rx = s_start | r_start;
    assign cal_seg_rx   = s_start ? s_seg : r_seg;
    assign cal_user_tx  = s_start ? 2'd0 : t_u;
    assign cal_user_rx  = s_start ? 2'd0 : r_u;
    assign running = s_run | t_run | r_run;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) fault <= 1'b0;
        else if (s_fault || t_f || r_f || (s_start && (t_start || r_start)) || (go && (!s_ready || !s_adm || t_run || r_run)))
            fault <= 1'b1;
endmodule
