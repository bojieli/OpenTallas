`timescale 1ns/1ps
// =====================================================================================================================
// Qwen3-8B TP8 split: static D2D link CALENDAR SEQUENCER (Q-DVM+LINK, 2026-10-15; r2 2026-10-16 admission run + epoch
// anchor). One instance beside each link end (compute die qfd_d2d_static, KV/system die qkd_d2d_static). It is the only
// producer of the link end's control inputs (cfg_tx_we, cfg_rx_we, cfg_addr, cfg_data, cal_start, cal_seg):
//
//   INIT MODE (after reset, and again on reload while idle): the compiler's calendar images (tools/qwen_split/
//     d2d_link_calendar.py --profile program, constants from tools/qwen_split/d2d_cal_seq_image.py) are written through
//     the end's cfg port: TX entry i, RX entry i for i = 0..NE-1, then the TX and RX segment-1 bases (the ADMISSION
//     segment base when ADM = 1, else the token-run base).  2*NE+2 edges, then cal_ready.
//   EPOCH ANCHOR (ADM = 1): every epoch strobe (epoch_go rising: the forwarded epoch strobe, the same package event on
//     both dies, seen EP_SKEW edges apart; EP_SKEW makes both dies count from one absolute edge) starts a counter e:
//       e = 1, 2              the segment-1 bases go back to the admission segment (only if a token base is loaded)
//       e = ADM_OFS           ADMISSION run (cal_seg = 1): BEGIN / AUTH S->C, the compiled admission WITNESS C->S;
//                             once per epoch (boot and every recovery epoch: BEGIN re-installs the program)
//       e = ADM_OFS + ADM_LEN the segment-1 bases switch to the token run (two cfg edges, all calendars idle)
//       e = FIRST_OFS         AUTO = 1: the first token start; then one every PERIOD edges (compiled token period)
//     AUTO = 0: the token start is tok_go (the compute face's token loop, which follows the same anchor rule).
//   NORMAL MODE: a token start issues cal_start with cal_seg = 1 GO_OFS + 1 edges after the go (token run: terminal
//     RESULT, CONTEXT/WITNESS records, embedding header + row, L0), then cal_start with cal_seg = 0 at every compiled
//     layer start L1..L35 (START[l] edges after the token cal_start).  No valid / ready / credit selects a cycle.
//   FAULTS (sticky, never stretch the schedule): a go before cal_ready or before the epoch's admission completed, a go
//     while a program runs, an admission start that finds the calendars busy or the bases not loaded.
//     halt (the link end's epoch_abort) stops the program and the anchor at once; the next epoch strobe restarts both.
// =====================================================================================================================
module ot_qwen_d2d_cal_seq #(
    parameter integer NE = 32,
    parameter integer NL = 36,          // layer runs per token (start 0 = token run incl. L0)
    parameter integer TW = 20,          // start-cycle width (token program 246,329 cycles < 2^18)
    parameter integer GO_OFS = 0,       // extra fixed edges from tok_go to the token cal_start (die go-path latency)
    parameter [32*NE-1:0] TX_IMG = '0,  // entry i at [32*i +: 32]
    parameter [32*NE-1:0] RX_IMG = '0,
    parameter [31:0]      TX_SEG1 = '0,
    parameter [31:0]      RX_SEG1 = '0,
    parameter [TW*NL-1:0] START = '0,   // START[0] = 0 (token run), START[l] = compiled layer-l start, increasing
    parameter integer ADM = 0,          // 1: admission run once per epoch (segment-1 base = admission segment first)
    parameter [31:0]      TX_SEG2 = '0, // admission segment bases
    parameter [31:0]      RX_SEG2 = '0,
    parameter integer ADM_OFS = 72,     // admission cal_start: edges after the anchored epoch strobe (> 2 NE + 2)
    parameter integer ADM_LEN = 1100,   // admission run length (every calendar idle after it)
    parameter integer AUTO = 0,         // 1: token starts from the anchor (FIRST_OFS, then every PERIOD)
    parameter integer FIRST_OFS = 1176, // first token cal_start, edges after the anchored epoch strobe
    parameter integer PERIOD = 249431,  // compiled token period
    parameter integer EP_SKEW = 0       // edges from this die's epoch_go to the common anchor edge
) (
    input  wire        ck,
    input  wire        rst_n,
    input  wire        reload,          // exceptional: HOST re-writes the images (only while idle)
    input  wire        tok_go,          // AUTO = 0: token start
    input  wire        epoch_go,        // forwarded epoch strobe (level; its rising edge anchors the epoch)
    input  wire        halt,
    output reg         cfg_tx_we,
    output reg         cfg_rx_we,
    output reg  [5:0]  cfg_addr,
    output reg  [31:0] cfg_data,
    output reg         cal_start,
    output reg         cal_seg,
    output reg         cal_ready,
    output reg         running,
    output reg  [5:0]  layer,           // run index of the last cal_start (0 = token run, 63 = admission)
    output reg         adm_done,        // this epoch's admission run is complete (token starts are legal)
    output reg         tok_start,       // AUTO: the internal token go (for the die's token-loop consumers)
    output reg         fault
);
    localparam integer NI = 2 * NE + 2;
    localparam integer IW = $clog2(NI + 1);
    localparam integer GW = (GO_OFS > 0) ? GO_OFS : 1;
    localparam integer E_ADM = EP_SKEW + ADM_OFS, E_SW = E_ADM + ADM_LEN, E_TOK = EP_SKEW + FIRST_OFS;
    localparam [31:0] TXB0 = ADM ? TX_SEG2 : TX_SEG1, RXB0 = ADM ? RX_SEG2 : RX_SEG1;
    initial begin
        if (ADM && ADM_OFS <= NI + 4) $error("ADM_OFS must exceed the image load (2 NE + 2) + 2");
        if (ADM && AUTO && FIRST_OFS < ADM_OFS + ADM_LEN + 4) $error("FIRST_OFS must follow the admission run + base switch");
    end
    reg          init;
    reg [IW-1:0] ip;
    reg [TW-1:0] t;
    reg [5:0]    li;
    reg [GW:0]   go_d;
    reg          ep_q, eact, tokbase, adm_pend, adm_run;
    reg [31:0]   e, pcnt;
    reg          auto_go, prun;
    wire         go_in = AUTO ? auto_go : tok_go;
    reg [GW:0]   gd;
    wire         go_now = (GO_OFS > 0) ? go_d[GO_OFS-1] : go_in;
    wire [TW-1:0] nxt = START[TW*li +: TW];
    wire         ep_rise = epoch_go && !ep_q;

    integer x;
    always @(posedge ck or negedge rst_n) begin
        if (!rst_n) begin
            init <= 1'b1; ip <= '0; cal_ready <= 1'b0; running <= 1'b0; fault <= 1'b0;
            cfg_tx_we <= 1'b0; cfg_rx_we <= 1'b0; cfg_addr <= '0; cfg_data <= '0;
            cal_start <= 1'b0; cal_seg <= 1'b0; t <= '0; li <= '0; layer <= '0; go_d <= '0;
            ep_q <= 1'b0; eact <= 1'b0; e <= 32'd0; tokbase <= 1'b0; adm_pend <= 1'b0; adm_run <= 1'b0;
            adm_done <= (ADM == 0); auto_go <= 1'b0; pcnt <= 32'd0; prun <= 1'b0; tok_start <= 1'b0;
        end else begin
            go_d <= {go_d[GW-1:0], go_in};
            ep_q <= epoch_go;
            cfg_tx_we <= 1'b0; cfg_rx_we <= 1'b0; cal_start <= 1'b0; cal_seg <= 1'b0;
            auto_go <= 1'b0; tok_start <= 1'b0;
            // ---- epoch anchor
            if (ep_rise && ADM) begin
                eact <= 1'b1; e <= 32'd1; adm_pend <= 1'b1; adm_done <= 1'b0; prun <= 1'b0;
            end else if (eact) e <= e + 32'd1;
            if (halt) begin eact <= 1'b0; prun <= 1'b0; adm_run <= 1'b0; end
            // ---- AUTO token anchor: first token at E_TOK, then every PERIOD
            if (AUTO && eact && !halt) begin
                if (e == E_TOK - GO_OFS - 2) begin auto_go <= 1'b1; prun <= 1'b1; pcnt <= 32'd1; tok_start <= 1'b1; end
                else if (prun) begin
                    if (pcnt == PERIOD) begin auto_go <= 1'b1; pcnt <= 32'd1; tok_start <= 1'b1; end
                    else pcnt <= pcnt + 32'd1;
                end
            end
            if (init) begin
                // TX entry i (even step), RX entry i (odd step), then the two segment-1 bases
                x = ip >> 1;
                if (ip < 2 * NE) begin
                    cfg_addr <= {1'b0, 5'(x)};
                    cfg_data <= ip[0] ? RX_IMG[32*x +: 32] : TX_IMG[32*x +: 32];
                    cfg_tx_we <= ~ip[0]; cfg_rx_we <= ip[0];
                end else begin
                    cfg_addr <= 6'b100000;
                    cfg_data <= ip[0] ? RXB0 : TXB0;
                    cfg_tx_we <= ~ip[0]; cfg_rx_we <= ip[0];
                end
                ip <= ip + 1'b1;
                if (ip == NI - 1) begin init <= 1'b0; cal_ready <= 1'b1; tokbase <= (ADM == 0); end
                if (go_in) fault <= 1'b1;
            end else if (halt) begin
                running <= 1'b0;                            // exceptional mode: the HOST replays from the next epoch
            end else if (ADM && eact && (e == 32'd1 || e == 32'd2) && tokbase) begin
                // new epoch: back to the admission segment (the calendars are stopped after the epoch begin)
                cfg_addr <= 6'b100000; cfg_data <= (e == 32'd1) ? TX_SEG2 : RX_SEG2;
                cfg_tx_we <= (e == 32'd1); cfg_rx_we <= (e == 32'd2);
                if (e == 32'd2) tokbase <= 1'b0;
                if (running) fault <= 1'b1;
            end else if (ADM && eact && e == E_ADM && adm_pend) begin
                if (!cal_ready || tokbase || running) fault <= 1'b1;
                cal_start <= 1'b1; cal_seg <= 1'b1; layer <= 6'h3f; adm_run <= 1'b1;
            end else if (ADM && eact && (e == E_SW || e == E_SW + 1) && adm_run) begin
                // admission over: segment-1 bases to the token run
                cfg_addr <= 6'b100000; cfg_data <= (e == E_SW) ? TX_SEG1 : RX_SEG1;
                cfg_tx_we <= (e == E_SW); cfg_rx_we <= (e == E_SW + 1);
                if (e == E_SW + 1) begin tokbase <= 1'b1; adm_run <= 1'b0; adm_pend <= 1'b0; adm_done <= 1'b1; end
            end else if (running) begin
                if (go_now) fault <= 1'b1;                  // a second token start inside a running program
                t <= t + 1'b1;
                if (t + 1'b1 == nxt) begin
                    cal_start <= 1'b1; cal_seg <= 1'b0; layer <= li;
                    if (li == NL - 1) running <= 1'b0; else li <= li + 1'b1;
                end
            end else if (go_now) begin
                if (!cal_ready || !adm_done || !tokbase) fault <= 1'b1;
                cal_start <= 1'b1; cal_seg <= 1'b1; layer <= '0;
                running <= (NL > 1); t <= '0; li <= 6'd1;
            end else if (reload) begin
                init <= 1'b1; ip <= '0; cal_ready <= 1'b0; tokbase <= 1'b0;
            end
        end
    end
endmodule
