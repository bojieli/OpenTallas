// Generated behavioral source by tools/qwen_static_kv/gen_dcal_bc4.py; originals untouched.
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
module ot_qwen_d2d_cal_seq_bc4 #(
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
    parameter integer PERIOD = 249600,  // compiled token period (d2d_cal_image.svh D2D_TOKEN_PERIOD, a 768-edge multiple)
    parameter integer EP_SKEW = 0       // edges from this die's epoch_go to the common anchor edge
) (
    input  wire        ck,
    input  wire [15:0] rst_bank_n,
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
    wire [19:0] nxt = {START[20*li_mux4+16 +: 4], START[20*li_mux3+12 +: 4], START[20*li_mux2+8 +: 4], START[20*li_mux1+4 +: 4], START[20*li_mux0+0 +: 4]};
    wire         ep_rise = epoch_go && !ep_q;

    (* keep = 1, dont_touch = 1 *) reg [0:0] ep_q_copy0;
    (* keep = 1, dont_touch = 1 *) reg [0:0] ep_q_copy1;
    (* keep = 1, dont_touch = 1 *) reg [5:0] li_mux0;
    (* keep = 1, dont_touch = 1 *) reg [5:0] li_mux1;
    (* keep = 1, dont_touch = 1 *) reg [5:0] li_mux2;
    (* keep = 1, dont_touch = 1 *) reg [5:0] li_mux3;
    (* keep = 1, dont_touch = 1 *) reg [5:0] li_mux4;
    (* keep = 1, dont_touch = 1 *) reg [6:0] ip_img0;
    (* keep = 1, dont_touch = 1 *) reg [6:0] ip_img1;
    (* keep = 1, dont_touch = 1 *) reg [6:0] ip_img2;
    (* keep = 1, dont_touch = 1 *) reg [6:0] ip_img3;
    (* keep = 1, dont_touch = 1 *) reg [0:0] running_copy0;
    (* keep = 1, dont_touch = 1 *) reg [0:0] running_copy1;
    (* keep = 1, dont_touch = 1 *) reg [0:0] running_copy2;
    (* keep = 1, dont_touch = 1 *) reg [0:0] init_copy0;
    (* keep = 1, dont_touch = 1 *) reg [0:0] init_copy1;
    (* keep = 1, dont_touch = 1 *) reg [0:0] init_copy2;
    initial if (NE != 32 || NL != 36 || TW != 20 || GO_OFS != 0 || ADM != 1 || AUTO != 1)
        $fatal(1, "BC4 unsupported ordinary core profile");
    integer x;
    reg [0:0] init_next;
    reg [6:0] ip_next;
    reg [0:0] cal_ready_next;
    reg [0:0] running_next;
    reg [0:0] fault_next;
    reg [0:0] cfg_tx_we_next;
    reg [0:0] cfg_rx_we_next;
    reg [5:0] cfg_addr_next;
    reg [31:0] cfg_data_next;
    reg [0:0] cal_start_next;
    reg [0:0] cal_seg_next;
    reg [19:0] t_next;
    reg [5:0] li_next;
    reg [5:0] layer_next;
    reg [1:0] go_d_next;
    reg [0:0] ep_q_next;
    reg [0:0] eact_next;
    reg [31:0] e_next;
    reg [0:0] tokbase_next;
    reg [0:0] adm_pend_next;
    reg [0:0] adm_run_next;
    reg [0:0] adm_done_next;
    reg [0:0] auto_go_next;
    reg [31:0] pcnt_next;
    reg [0:0] prun_next;
    reg [0:0] tok_start_next;
    reg [0:0] ep_q_copy0_next;
    reg [0:0] ep_q_copy1_next;
    reg [5:0] li_mux0_next;
    reg [5:0] li_mux1_next;
    reg [5:0] li_mux2_next;
    reg [5:0] li_mux3_next;
    reg [5:0] li_mux4_next;
    reg [6:0] ip_img0_next;
    reg [6:0] ip_img1_next;
    reg [6:0] ip_img2_next;
    reg [6:0] ip_img3_next;
    reg [0:0] running_copy0_next;
    reg [0:0] running_copy1_next;
    reg [0:0] running_copy2_next;
    reg [0:0] init_copy0_next;
    reg [0:0] init_copy1_next;
    reg [0:0] init_copy2_next;
    reg [0:0] init_part0;
    reg [6:0] ip_part0;
    reg [0:0] cal_ready_part0;
    reg [0:0] running_part0;
    reg [0:0] fault_part0;
    reg [0:0] cfg_tx_we_part0;
    reg [0:0] cfg_rx_we_part0;
    reg [5:0] cfg_addr_part0;
    reg [31:0] cfg_data_part0;
    reg [31:0] cfg_data_part1;
    reg [0:0] cal_start_part0;
    reg [0:0] cal_seg_part0;
    reg [19:0] t_part0;
    reg [19:0] t_part1;
    reg [5:0] li_part0;
    reg [5:0] layer_part0;
    reg [1:0] go_d_part0;
    reg [0:0] ep_q_part0;
    reg [0:0] eact_part0;
    reg [31:0] e_part0;
    reg [31:0] e_part1;
    reg [0:0] tokbase_part0;
    reg [0:0] adm_pend_part0;
    reg [0:0] adm_run_part0;
    reg [0:0] adm_done_part0;
    reg [0:0] auto_go_part0;
    reg [31:0] pcnt_part0;
    reg [31:0] pcnt_part1;
    reg [0:0] prun_part0;
    reg [0:0] tok_start_part0;
    always @* begin
        init_part0 = init;
            ;
            ;
            ; ; ; ;
            ; ;
            // ---- epoch anchor
            if (ep_rise && ADM) begin
                ; ; ; ; ;
            end else if (eact) ;
            if (halt) begin ; ; ; end
            // ---- AUTO token anchor: first token at E_TOK, then every PERIOD
            if (AUTO && eact && !halt) begin
                if (e == E_TOK - GO_OFS - 2) begin ; ; ; ; end
                else if (prun) begin
                    if (pcnt == PERIOD) begin ; ; ; end
                    else ;
                end
            end
            if (init_copy0) begin
                // TX entry i (even step), RX entry i (odd step), then the two segment-1 bases
                ;
                if (ip < 2 * NE) begin
                    ;
                    ;
;
;
;
                    ; ;
                end else begin
                    ;
                    ;
                    ; ;
                end
                ;
                if (ip == NI - 1) begin init_part0 = 1'b0; ; ; end
                if (go_in) ;
            end else if (halt) begin
                ;                            // exceptional mode: the HOST replays from the next epoch
            end else if (ADM && eact && (e == 32'd1 || e == 32'd2) && tokbase) begin
                // new epoch: back to the admission segment (the calendars are stopped after the epoch begin)
                ; ;
                ; ;
                if (e == 32'd2) ;
                if (running_copy0) ;
            end else if (ADM && eact && e == E_ADM && adm_pend) begin
                if (!cal_ready || tokbase || running_copy0) ;
                ; ; ; ;
            end else if (ADM && eact && (e == E_SW || e == E_SW + 1) && adm_run) begin
                // admission over: segment-1 bases to the token run
                ; ;
                ; ;
                if (e == E_SW + 1) begin ; ; ; ; end
            end else if (running_copy0) begin
                if (go_now) ;                  // a second token start inside a running_copy0 program
                ;
                if (t + 1'b1 == nxt) begin
                    ; ; ;
                    if (li == NL - 1) ; else ;
                end
            end else if (go_now) begin
                if (!cal_ready || !adm_done || !tokbase) ;
                ; ; ;
                ; ; ;
            end else if (reload) begin
                init_part0 = 1'b1; ; ; ;
            end
        
        init_next[0:0] = init_part0[0:0];
    end
    always @* begin
        ip_part0 = ip;
            ;
            ;
            ; ; ; ;
            ; ;
            // ---- epoch anchor
            if (ep_rise && ADM) begin
                ; ; ; ; ;
            end else if (eact) ;
            if (halt) begin ; ; ; end
            // ---- AUTO token anchor: first token at E_TOK, then every PERIOD
            if (AUTO && eact && !halt) begin
                if (e == E_TOK - GO_OFS - 2) begin ; ; ; ; end
                else if (prun) begin
                    if (pcnt == PERIOD) begin ; ; ; end
                    else ;
                end
            end
            if (init_copy1) begin
                // TX entry i (even step), RX entry i (odd step), then the two segment-1 bases
                ;
                if (ip < 2 * NE) begin
                    ;
                    ;
;
;
;
                    ; ;
                end else begin
                    ;
                    ;
                    ; ;
                end
                ip_part0 = ip + 1'b1;
                if (ip == NI - 1) begin ; ; ; end
                if (go_in) ;
            end else if (halt) begin
                ;                            // exceptional mode: the HOST replays from the next epoch
            end else if (ADM && eact && (e == 32'd1 || e == 32'd2) && tokbase) begin
                // new epoch: back to the admission segment (the calendars are stopped after the epoch begin)
                ; ;
                ; ;
                if (e == 32'd2) ;
                if (running_copy1) ;
            end else if (ADM && eact && e == E_ADM && adm_pend) begin
                if (!cal_ready || tokbase || running_copy1) ;
                ; ; ; ;
            end else if (ADM && eact && (e == E_SW || e == E_SW + 1) && adm_run) begin
                // admission over: segment-1 bases to the token run
                ; ;
                ; ;
                if (e == E_SW + 1) begin ; ; ; ; end
            end else if (running_copy1) begin
                if (go_now) ;                  // a second token start inside a running_copy1 program
                ;
                if (t + 1'b1 == nxt) begin
                    ; ; ;
                    if (li == NL - 1) ; else ;
                end
            end else if (go_now) begin
                if (!cal_ready || !adm_done || !tokbase) ;
                ; ; ;
                ; ; ;
            end else if (reload) begin
                ; ip_part0 = '0; ; ;
            end
        
        ip_next[6:0] = ip_part0[6:0];
    end
    always @* begin
        cal_ready_part0 = cal_ready;
            ;
            ;
            ; ; ; ;
            ; ;
            // ---- epoch anchor
            if (ep_rise && ADM) begin
                ; ; ; ; ;
            end else if (eact) ;
            if (halt) begin ; ; ; end
            // ---- AUTO token anchor: first token at E_TOK, then every PERIOD
            if (AUTO && eact && !halt) begin
                if (e == E_TOK - GO_OFS - 2) begin ; ; ; ; end
                else if (prun) begin
                    if (pcnt == PERIOD) begin ; ; ; end
                    else ;
                end
            end
            if (init_copy2) begin
                // TX entry i (even step), RX entry i (odd step), then the two segment-1 bases
                ;
                if (ip < 2 * NE) begin
                    ;
                    ;
;
;
;
                    ; ;
                end else begin
                    ;
                    ;
                    ; ;
                end
                ;
                if (ip == NI - 1) begin ; cal_ready_part0 = 1'b1; ; end
                if (go_in) ;
            end else if (halt) begin
                ;                            // exceptional mode: the HOST replays from the next epoch
            end else if (ADM && eact && (e == 32'd1 || e == 32'd2) && tokbase) begin
                // new epoch: back to the admission segment (the calendars are stopped after the epoch begin)
                ; ;
                ; ;
                if (e == 32'd2) ;
                if (running_copy2) ;
            end else if (ADM && eact && e == E_ADM && adm_pend) begin
                if (!cal_ready || tokbase || running_copy2) ;
                ; ; ; ;
            end else if (ADM && eact && (e == E_SW || e == E_SW + 1) && adm_run) begin
                // admission over: segment-1 bases to the token run
                ; ;
                ; ;
                if (e == E_SW + 1) begin ; ; ; ; end
            end else if (running_copy2) begin
                if (go_now) ;                  // a second token start inside a running_copy2 program
                ;
                if (t + 1'b1 == nxt) begin
                    ; ; ;
                    if (li == NL - 1) ; else ;
                end
            end else if (go_now) begin
                if (!cal_ready || !adm_done || !tokbase) ;
                ; ; ;
                ; ; ;
            end else if (reload) begin
                ; ; cal_ready_part0 = 1'b0; ;
            end
        
        cal_ready_next[0:0] = cal_ready_part0[0:0];
    end
    always @* begin
        running_part0 = running;
            ;
            ;
            ; ; ; ;
            ; ;
            // ---- epoch anchor
            if (ep_rise && ADM) begin
                ; ; ; ; ;
            end else if (eact) ;
            if (halt) begin ; ; ; end
            // ---- AUTO token anchor: first token at E_TOK, then every PERIOD
            if (AUTO && eact && !halt) begin
                if (e == E_TOK - GO_OFS - 2) begin ; ; ; ; end
                else if (prun) begin
                    if (pcnt == PERIOD) begin ; ; ; end
                    else ;
                end
            end
            if (init_copy0) begin
                // TX entry i (even step), RX entry i (odd step), then the two segment-1 bases
                ;
                if (ip < 2 * NE) begin
                    ;
                    ;
;
;
;
                    ; ;
                end else begin
                    ;
                    ;
                    ; ;
                end
                ;
                if (ip == NI - 1) begin ; ; ; end
                if (go_in) ;
            end else if (halt) begin
                running_part0 = 1'b0;                            // exceptional mode: the HOST replays from the next epoch
            end else if (ADM && eact && (e == 32'd1 || e == 32'd2) && tokbase) begin
                // new epoch: back to the admission segment (the calendars are stopped after the epoch begin)
                ; ;
                ; ;
                if (e == 32'd2) ;
                if (running_copy0) ;
            end else if (ADM && eact && e == E_ADM && adm_pend) begin
                if (!cal_ready || tokbase || running_copy0) ;
                ; ; ; ;
            end else if (ADM && eact && (e == E_SW || e == E_SW + 1) && adm_run) begin
                // admission over: segment-1 bases to the token run
                ; ;
                ; ;
                if (e == E_SW + 1) begin ; ; ; ; end
            end else if (running_copy0) begin
                if (go_now) ;                  // a second token start inside a running_copy0 program
                ;
                if (t + 1'b1 == nxt) begin
                    ; ; ;
                    if (li == NL - 1) running_part0 = 1'b0; else ;
                end
            end else if (go_now) begin
                if (!cal_ready || !adm_done || !tokbase) ;
                ; ; ;
                running_part0 = (NL > 1); ; ;
            end else if (reload) begin
                ; ; ; ;
            end
        
        running_next[0:0] = running_part0[0:0];
    end
    always @* begin
        fault_part0 = fault;
            ;
            ;
            ; ; ; ;
            ; ;
            // ---- epoch anchor
            if (ep_rise && ADM) begin
                ; ; ; ; ;
            end else if (eact) ;
            if (halt) begin ; ; ; end
            // ---- AUTO token anchor: first token at E_TOK, then every PERIOD
            if (AUTO && eact && !halt) begin
                if (e == E_TOK - GO_OFS - 2) begin ; ; ; ; end
                else if (prun) begin
                    if (pcnt == PERIOD) begin ; ; ; end
                    else ;
                end
            end
            if (init_copy1) begin
                // TX entry i (even step), RX entry i (odd step), then the two segment-1 bases
                ;
                if (ip < 2 * NE) begin
                    ;
                    ;
;
;
;
                    ; ;
                end else begin
                    ;
                    ;
                    ; ;
                end
                ;
                if (ip == NI - 1) begin ; ; ; end
                if (go_in) fault_part0 = 1'b1;
            end else if (halt) begin
                ;                            // exceptional mode: the HOST replays from the next epoch
            end else if (ADM && eact && (e == 32'd1 || e == 32'd2) && tokbase) begin
                // new epoch: back to the admission segment (the calendars are stopped after the epoch begin)
                ; ;
                ; ;
                if (e == 32'd2) ;
                if (running_copy1) fault_part0 = 1'b1;
            end else if (ADM && eact && e == E_ADM && adm_pend) begin
                if (!cal_ready || tokbase || running_copy1) fault_part0 = 1'b1;
                ; ; ; ;
            end else if (ADM && eact && (e == E_SW || e == E_SW + 1) && adm_run) begin
                // admission over: segment-1 bases to the token run
                ; ;
                ; ;
                if (e == E_SW + 1) begin ; ; ; ; end
            end else if (running_copy1) begin
                if (go_now) fault_part0 = 1'b1;                  // a second token start inside a running_copy1 program
                ;
                if (t + 1'b1 == nxt) begin
                    ; ; ;
                    if (li == NL - 1) ; else ;
                end
            end else if (go_now) begin
                if (!cal_ready || !adm_done || !tokbase) fault_part0 = 1'b1;
                ; ; ;
                ; ; ;
            end else if (reload) begin
                ; ; ; ;
            end
        
        fault_next[0:0] = fault_part0[0:0];
    end
    always @* begin
        cfg_tx_we_part0 = cfg_tx_we;
            ;
            ;
            cfg_tx_we_part0 = 1'b0; ; ; ;
            ; ;
            // ---- epoch anchor
            if (ep_rise && ADM) begin
                ; ; ; ; ;
            end else if (eact) ;
            if (halt) begin ; ; ; end
            // ---- AUTO token anchor: first token at E_TOK, then every PERIOD
            if (AUTO && eact && !halt) begin
                if (e == E_TOK - GO_OFS - 2) begin ; ; ; ; end
                else if (prun) begin
                    if (pcnt == PERIOD) begin ; ; ; end
                    else ;
                end
            end
            if (init_copy2) begin
                // TX entry i (even step), RX entry i (odd step), then the two segment-1 bases
                ;
                if (ip < 2 * NE) begin
                    ;
                    ;
;
;
;
                    cfg_tx_we_part0 = ~ip[0]; ;
                end else begin
                    ;
                    ;
                    cfg_tx_we_part0 = ~ip[0]; ;
                end
                ;
                if (ip == NI - 1) begin ; ; ; end
                if (go_in) ;
            end else if (halt) begin
                ;                            // exceptional mode: the HOST replays from the next epoch
            end else if (ADM && eact && (e == 32'd1 || e == 32'd2) && tokbase) begin
                // new epoch: back to the admission segment (the calendars are stopped after the epoch begin)
                ; ;
                cfg_tx_we_part0 = (e == 32'd1); ;
                if (e == 32'd2) ;
                if (running_copy2) ;
            end else if (ADM && eact && e == E_ADM && adm_pend) begin
                if (!cal_ready || tokbase || running_copy2) ;
                ; ; ; ;
            end else if (ADM && eact && (e == E_SW || e == E_SW + 1) && adm_run) begin
                // admission over: segment-1 bases to the token run
                ; ;
                cfg_tx_we_part0 = (e == E_SW); ;
                if (e == E_SW + 1) begin ; ; ; ; end
            end else if (running_copy2) begin
                if (go_now) ;                  // a second token start inside a running_copy2 program
                ;
                if (t + 1'b1 == nxt) begin
                    ; ; ;
                    if (li == NL - 1) ; else ;
                end
            end else if (go_now) begin
                if (!cal_ready || !adm_done || !tokbase) ;
                ; ; ;
                ; ; ;
            end else if (reload) begin
                ; ; ; ;
            end
        
        cfg_tx_we_next[0:0] = cfg_tx_we_part0[0:0];
    end
    always @* begin
        cfg_rx_we_part0 = cfg_rx_we;
            ;
            ;
            ; cfg_rx_we_part0 = 1'b0; ; ;
            ; ;
            // ---- epoch anchor
            if (ep_rise && ADM) begin
                ; ; ; ; ;
            end else if (eact) ;
            if (halt) begin ; ; ; end
            // ---- AUTO token anchor: first token at E_TOK, then every PERIOD
            if (AUTO && eact && !halt) begin
                if (e == E_TOK - GO_OFS - 2) begin ; ; ; ; end
                else if (prun) begin
                    if (pcnt == PERIOD) begin ; ; ; end
                    else ;
                end
            end
            if (init_copy0) begin
                // TX entry i (even step), RX entry i (odd step), then the two segment-1 bases
                ;
                if (ip < 2 * NE) begin
                    ;
                    ;
;
;
;
                    ; cfg_rx_we_part0 = ip[0];
                end else begin
                    ;
                    ;
                    ; cfg_rx_we_part0 = ip[0];
                end
                ;
                if (ip == NI - 1) begin ; ; ; end
                if (go_in) ;
            end else if (halt) begin
                ;                            // exceptional mode: the HOST replays from the next epoch
            end else if (ADM && eact && (e == 32'd1 || e == 32'd2) && tokbase) begin
                // new epoch: back to the admission segment (the calendars are stopped after the epoch begin)
                ; ;
                ; cfg_rx_we_part0 = (e == 32'd2);
                if (e == 32'd2) ;
                if (running_copy0) ;
            end else if (ADM && eact && e == E_ADM && adm_pend) begin
                if (!cal_ready || tokbase || running_copy0) ;
                ; ; ; ;
            end else if (ADM && eact && (e == E_SW || e == E_SW + 1) && adm_run) begin
                // admission over: segment-1 bases to the token run
                ; ;
                ; cfg_rx_we_part0 = (e == E_SW + 1);
                if (e == E_SW + 1) begin ; ; ; ; end
            end else if (running_copy0) begin
                if (go_now) ;                  // a second token start inside a running_copy0 program
                ;
                if (t + 1'b1 == nxt) begin
                    ; ; ;
                    if (li == NL - 1) ; else ;
                end
            end else if (go_now) begin
                if (!cal_ready || !adm_done || !tokbase) ;
                ; ; ;
                ; ; ;
            end else if (reload) begin
                ; ; ; ;
            end
        
        cfg_rx_we_next[0:0] = cfg_rx_we_part0[0:0];
    end
    always @* begin
        cfg_addr_part0 = cfg_addr;
            ;
            ;
            ; ; ; ;
            ; ;
            // ---- epoch anchor
            if (ep_rise && ADM) begin
                ; ; ; ; ;
            end else if (eact) ;
            if (halt) begin ; ; ; end
            // ---- AUTO token anchor: first token at E_TOK, then every PERIOD
            if (AUTO && eact && !halt) begin
                if (e == E_TOK - GO_OFS - 2) begin ; ; ; ; end
                else if (prun) begin
                    if (pcnt == PERIOD) begin ; ; ; end
                    else ;
                end
            end
            if (init_copy1) begin
                // TX entry i (even step), RX entry i (odd step), then the two segment-1 bases
                ;
                if (ip < 2 * NE) begin
                    cfg_addr_part0 = {1'b0, 5'((ip >> 1))};
                    ;
;
;
;
                    ; ;
                end else begin
                    cfg_addr_part0 = 6'b100000;
                    ;
                    ; ;
                end
                ;
                if (ip == NI - 1) begin ; ; ; end
                if (go_in) ;
            end else if (halt) begin
                ;                            // exceptional mode: the HOST replays from the next epoch
            end else if (ADM && eact && (e == 32'd1 || e == 32'd2) && tokbase) begin
                // new epoch: back to the admission segment (the calendars are stopped after the epoch begin)
                cfg_addr_part0 = 6'b100000; ;
                ; ;
                if (e == 32'd2) ;
                if (running_copy1) ;
            end else if (ADM && eact && e == E_ADM && adm_pend) begin
                if (!cal_ready || tokbase || running_copy1) ;
                ; ; ; ;
            end else if (ADM && eact && (e == E_SW || e == E_SW + 1) && adm_run) begin
                // admission over: segment-1 bases to the token run
                cfg_addr_part0 = 6'b100000; ;
                ; ;
                if (e == E_SW + 1) begin ; ; ; ; end
            end else if (running_copy1) begin
                if (go_now) ;                  // a second token start inside a running_copy1 program
                ;
                if (t + 1'b1 == nxt) begin
                    ; ; ;
                    if (li == NL - 1) ; else ;
                end
            end else if (go_now) begin
                if (!cal_ready || !adm_done || !tokbase) ;
                ; ; ;
                ; ; ;
            end else if (reload) begin
                ; ; ; ;
            end
        
        cfg_addr_next[5:0] = cfg_addr_part0[5:0];
    end
    always @* begin
        cfg_data_part0 = cfg_data;
            ;
            ;
            ; ; ; ;
            ; ;
            // ---- epoch anchor
            if (ep_rise && ADM) begin
                ; ; ; ; ;
            end else if (eact) ;
            if (halt) begin ; ; ; end
            // ---- AUTO token anchor: first token at E_TOK, then every PERIOD
            if (AUTO && eact && !halt) begin
                if (e == E_TOK - GO_OFS - 2) begin ; ; ; ; end
                else if (prun) begin
                    if (pcnt == PERIOD) begin ; ; ; end
                    else ;
                end
            end
            if (init_copy2) begin
                // TX entry i (even step), RX entry i (odd step), then the two segment-1 bases
                ;
                if (ip < 2 * NE) begin
                    ;
                    cfg_data_part0[0 +: 8] = ip_img0[0] ? RX_IMG[32*(ip_img0 >> 1)+0 +: 8] : TX_IMG[32*(ip_img0 >> 1)+0 +: 8];
cfg_data_part0[8 +: 8] = ip_img1[0] ? RX_IMG[32*(ip_img1 >> 1)+8 +: 8] : TX_IMG[32*(ip_img1 >> 1)+8 +: 8];
cfg_data_part0[16 +: 8] = ip_img2[0] ? RX_IMG[32*(ip_img2 >> 1)+16 +: 8] : TX_IMG[32*(ip_img2 >> 1)+16 +: 8];
cfg_data_part0[24 +: 8] = ip_img3[0] ? RX_IMG[32*(ip_img3 >> 1)+24 +: 8] : TX_IMG[32*(ip_img3 >> 1)+24 +: 8];
                    ; ;
                end else begin
                    ;
                    cfg_data_part0 = ip[0] ? RXB0 : TXB0;
                    ; ;
                end
                ;
                if (ip == NI - 1) begin ; ; ; end
                if (go_in) ;
            end else if (halt) begin
                ;                            // exceptional mode: the HOST replays from the next epoch
            end else if (ADM && eact && (e == 32'd1 || e == 32'd2) && tokbase) begin
                // new epoch: back to the admission segment (the calendars are stopped after the epoch begin)
                ; cfg_data_part0 = (e == 32'd1) ? TX_SEG2 : RX_SEG2;
                ; ;
                if (e == 32'd2) ;
                if (running_copy2) ;
            end else if (ADM && eact && e == E_ADM && adm_pend) begin
                if (!cal_ready || tokbase || running_copy2) ;
                ; ; ; ;
            end else if (ADM && eact && (e == E_SW || e == E_SW + 1) && adm_run) begin
                // admission over: segment-1 bases to the token run
                ; cfg_data_part0 = (e == E_SW) ? TX_SEG1 : RX_SEG1;
                ; ;
                if (e == E_SW + 1) begin ; ; ; ; end
            end else if (running_copy2) begin
                if (go_now) ;                  // a second token start inside a running_copy2 program
                ;
                if (t + 1'b1 == nxt) begin
                    ; ; ;
                    if (li == NL - 1) ; else ;
                end
            end else if (go_now) begin
                if (!cal_ready || !adm_done || !tokbase) ;
                ; ; ;
                ; ; ;
            end else if (reload) begin
                ; ; ; ;
            end
        
        cfg_data_next[15:0] = cfg_data_part0[15:0];
    end
    always @* begin
        cfg_data_part1 = cfg_data;
            ;
            ;
            ; ; ; ;
            ; ;
            // ---- epoch anchor
            if (ep_rise && ADM) begin
                ; ; ; ; ;
            end else if (eact) ;
            if (halt) begin ; ; ; end
            // ---- AUTO token anchor: first token at E_TOK, then every PERIOD
            if (AUTO && eact && !halt) begin
                if (e == E_TOK - GO_OFS - 2) begin ; ; ; ; end
                else if (prun) begin
                    if (pcnt == PERIOD) begin ; ; ; end
                    else ;
                end
            end
            if (init_copy0) begin
                // TX entry i (even step), RX entry i (odd step), then the two segment-1 bases
                ;
                if (ip < 2 * NE) begin
                    ;
                    cfg_data_part1[0 +: 8] = ip_img0[0] ? RX_IMG[32*(ip_img0 >> 1)+0 +: 8] : TX_IMG[32*(ip_img0 >> 1)+0 +: 8];
cfg_data_part1[8 +: 8] = ip_img1[0] ? RX_IMG[32*(ip_img1 >> 1)+8 +: 8] : TX_IMG[32*(ip_img1 >> 1)+8 +: 8];
cfg_data_part1[16 +: 8] = ip_img2[0] ? RX_IMG[32*(ip_img2 >> 1)+16 +: 8] : TX_IMG[32*(ip_img2 >> 1)+16 +: 8];
cfg_data_part1[24 +: 8] = ip_img3[0] ? RX_IMG[32*(ip_img3 >> 1)+24 +: 8] : TX_IMG[32*(ip_img3 >> 1)+24 +: 8];
                    ; ;
                end else begin
                    ;
                    cfg_data_part1 = ip[0] ? RXB0 : TXB0;
                    ; ;
                end
                ;
                if (ip == NI - 1) begin ; ; ; end
                if (go_in) ;
            end else if (halt) begin
                ;                            // exceptional mode: the HOST replays from the next epoch
            end else if (ADM && eact && (e == 32'd1 || e == 32'd2) && tokbase) begin
                // new epoch: back to the admission segment (the calendars are stopped after the epoch begin)
                ; cfg_data_part1 = (e == 32'd1) ? TX_SEG2 : RX_SEG2;
                ; ;
                if (e == 32'd2) ;
                if (running_copy0) ;
            end else if (ADM && eact && e == E_ADM && adm_pend) begin
                if (!cal_ready || tokbase || running_copy0) ;
                ; ; ; ;
            end else if (ADM && eact && (e == E_SW || e == E_SW + 1) && adm_run) begin
                // admission over: segment-1 bases to the token run
                ; cfg_data_part1 = (e == E_SW) ? TX_SEG1 : RX_SEG1;
                ; ;
                if (e == E_SW + 1) begin ; ; ; ; end
            end else if (running_copy0) begin
                if (go_now) ;                  // a second token start inside a running_copy0 program
                ;
                if (t + 1'b1 == nxt) begin
                    ; ; ;
                    if (li == NL - 1) ; else ;
                end
            end else if (go_now) begin
                if (!cal_ready || !adm_done || !tokbase) ;
                ; ; ;
                ; ; ;
            end else if (reload) begin
                ; ; ; ;
            end
        
        cfg_data_next[31:16] = cfg_data_part1[31:16];
    end
    always @* begin
        cal_start_part0 = cal_start;
            ;
            ;
            ; ; cal_start_part0 = 1'b0; ;
            ; ;
            // ---- epoch anchor
            if (ep_rise && ADM) begin
                ; ; ; ; ;
            end else if (eact) ;
            if (halt) begin ; ; ; end
            // ---- AUTO token anchor: first token at E_TOK, then every PERIOD
            if (AUTO && eact && !halt) begin
                if (e == E_TOK - GO_OFS - 2) begin ; ; ; ; end
                else if (prun) begin
                    if (pcnt == PERIOD) begin ; ; ; end
                    else ;
                end
            end
            if (init_copy0) begin
                // TX entry i (even step), RX entry i (odd step), then the two segment-1 bases
                ;
                if (ip < 2 * NE) begin
                    ;
                    ;
;
;
;
                    ; ;
                end else begin
                    ;
                    ;
                    ; ;
                end
                ;
                if (ip == NI - 1) begin ; ; ; end
                if (go_in) ;
            end else if (halt) begin
                ;                            // exceptional mode: the HOST replays from the next epoch
            end else if (ADM && eact && (e == 32'd1 || e == 32'd2) && tokbase) begin
                // new epoch: back to the admission segment (the calendars are stopped after the epoch begin)
                ; ;
                ; ;
                if (e == 32'd2) ;
                if (running_copy0) ;
            end else if (ADM && eact && e == E_ADM && adm_pend) begin
                if (!cal_ready || tokbase || running_copy0) ;
                cal_start_part0 = 1'b1; ; ; ;
            end else if (ADM && eact && (e == E_SW || e == E_SW + 1) && adm_run) begin
                // admission over: segment-1 bases to the token run
                ; ;
                ; ;
                if (e == E_SW + 1) begin ; ; ; ; end
            end else if (running_copy0) begin
                if (go_now) ;                  // a second token start inside a running_copy0 program
                ;
                if (t + 1'b1 == nxt) begin
                    cal_start_part0 = 1'b1; ; ;
                    if (li == NL - 1) ; else ;
                end
            end else if (go_now) begin
                if (!cal_ready || !adm_done || !tokbase) ;
                cal_start_part0 = 1'b1; ; ;
                ; ; ;
            end else if (reload) begin
                ; ; ; ;
            end
        
        cal_start_next[0:0] = cal_start_part0[0:0];
    end
    always @* begin
        cal_seg_part0 = cal_seg;
            ;
            ;
            ; ; ; cal_seg_part0 = 1'b0;
            ; ;
            // ---- epoch anchor
            if (ep_rise && ADM) begin
                ; ; ; ; ;
            end else if (eact) ;
            if (halt) begin ; ; ; end
            // ---- AUTO token anchor: first token at E_TOK, then every PERIOD
            if (AUTO && eact && !halt) begin
                if (e == E_TOK - GO_OFS - 2) begin ; ; ; ; end
                else if (prun) begin
                    if (pcnt == PERIOD) begin ; ; ; end
                    else ;
                end
            end
            if (init_copy1) begin
                // TX entry i (even step), RX entry i (odd step), then the two segment-1 bases
                ;
                if (ip < 2 * NE) begin
                    ;
                    ;
;
;
;
                    ; ;
                end else begin
                    ;
                    ;
                    ; ;
                end
                ;
                if (ip == NI - 1) begin ; ; ; end
                if (go_in) ;
            end else if (halt) begin
                ;                            // exceptional mode: the HOST replays from the next epoch
            end else if (ADM && eact && (e == 32'd1 || e == 32'd2) && tokbase) begin
                // new epoch: back to the admission segment (the calendars are stopped after the epoch begin)
                ; ;
                ; ;
                if (e == 32'd2) ;
                if (running_copy1) ;
            end else if (ADM && eact && e == E_ADM && adm_pend) begin
                if (!cal_ready || tokbase || running_copy1) ;
                ; cal_seg_part0 = 1'b1; ; ;
            end else if (ADM && eact && (e == E_SW || e == E_SW + 1) && adm_run) begin
                // admission over: segment-1 bases to the token run
                ; ;
                ; ;
                if (e == E_SW + 1) begin ; ; ; ; end
            end else if (running_copy1) begin
                if (go_now) ;                  // a second token start inside a running_copy1 program
                ;
                if (t + 1'b1 == nxt) begin
                    ; cal_seg_part0 = 1'b0; ;
                    if (li == NL - 1) ; else ;
                end
            end else if (go_now) begin
                if (!cal_ready || !adm_done || !tokbase) ;
                ; cal_seg_part0 = 1'b1; ;
                ; ; ;
            end else if (reload) begin
                ; ; ; ;
            end
        
        cal_seg_next[0:0] = cal_seg_part0[0:0];
    end
    always @* begin
        t_part0 = t;
            ;
            ;
            ; ; ; ;
            ; ;
            // ---- epoch anchor
            if (ep_rise && ADM) begin
                ; ; ; ; ;
            end else if (eact) ;
            if (halt) begin ; ; ; end
            // ---- AUTO token anchor: first token at E_TOK, then every PERIOD
            if (AUTO && eact && !halt) begin
                if (e == E_TOK - GO_OFS - 2) begin ; ; ; ; end
                else if (prun) begin
                    if (pcnt == PERIOD) begin ; ; ; end
                    else ;
                end
            end
            if (init_copy2) begin
                // TX entry i (even step), RX entry i (odd step), then the two segment-1 bases
                ;
                if (ip < 2 * NE) begin
                    ;
                    ;
;
;
;
                    ; ;
                end else begin
                    ;
                    ;
                    ; ;
                end
                ;
                if (ip == NI - 1) begin ; ; ; end
                if (go_in) ;
            end else if (halt) begin
                ;                            // exceptional mode: the HOST replays from the next epoch
            end else if (ADM && eact && (e == 32'd1 || e == 32'd2) && tokbase) begin
                // new epoch: back to the admission segment (the calendars are stopped after the epoch begin)
                ; ;
                ; ;
                if (e == 32'd2) ;
                if (running_copy2) ;
            end else if (ADM && eact && e == E_ADM && adm_pend) begin
                if (!cal_ready || tokbase || running_copy2) ;
                ; ; ; ;
            end else if (ADM && eact && (e == E_SW || e == E_SW + 1) && adm_run) begin
                // admission over: segment-1 bases to the token run
                ; ;
                ; ;
                if (e == E_SW + 1) begin ; ; ; ; end
            end else if (running_copy2) begin
                if (go_now) ;                  // a second token start inside a running_copy2 program
                t_part0 = t + 1'b1;
                if (t + 1'b1 == nxt) begin
                    ; ; ;
                    if (li == NL - 1) ; else ;
                end
            end else if (go_now) begin
                if (!cal_ready || !adm_done || !tokbase) ;
                ; ; ;
                ; t_part0 = '0; ;
            end else if (reload) begin
                ; ; ; ;
            end
        
        t_next[15:0] = t_part0[15:0];
    end
    always @* begin
        t_part1 = t;
            ;
            ;
            ; ; ; ;
            ; ;
            // ---- epoch anchor
            if (ep_rise && ADM) begin
                ; ; ; ; ;
            end else if (eact) ;
            if (halt) begin ; ; ; end
            // ---- AUTO token anchor: first token at E_TOK, then every PERIOD
            if (AUTO && eact && !halt) begin
                if (e == E_TOK - GO_OFS - 2) begin ; ; ; ; end
                else if (prun) begin
                    if (pcnt == PERIOD) begin ; ; ; end
                    else ;
                end
            end
            if (init_copy0) begin
                // TX entry i (even step), RX entry i (odd step), then the two segment-1 bases
                ;
                if (ip < 2 * NE) begin
                    ;
                    ;
;
;
;
                    ; ;
                end else begin
                    ;
                    ;
                    ; ;
                end
                ;
                if (ip == NI - 1) begin ; ; ; end
                if (go_in) ;
            end else if (halt) begin
                ;                            // exceptional mode: the HOST replays from the next epoch
            end else if (ADM && eact && (e == 32'd1 || e == 32'd2) && tokbase) begin
                // new epoch: back to the admission segment (the calendars are stopped after the epoch begin)
                ; ;
                ; ;
                if (e == 32'd2) ;
                if (running_copy0) ;
            end else if (ADM && eact && e == E_ADM && adm_pend) begin
                if (!cal_ready || tokbase || running_copy0) ;
                ; ; ; ;
            end else if (ADM && eact && (e == E_SW || e == E_SW + 1) && adm_run) begin
                // admission over: segment-1 bases to the token run
                ; ;
                ; ;
                if (e == E_SW + 1) begin ; ; ; ; end
            end else if (running_copy0) begin
                if (go_now) ;                  // a second token start inside a running_copy0 program
                t_part1 = t + 1'b1;
                if (t + 1'b1 == nxt) begin
                    ; ; ;
                    if (li == NL - 1) ; else ;
                end
            end else if (go_now) begin
                if (!cal_ready || !adm_done || !tokbase) ;
                ; ; ;
                ; t_part1 = '0; ;
            end else if (reload) begin
                ; ; ; ;
            end
        
        t_next[19:16] = t_part1[19:16];
    end
    always @* begin
        li_part0 = li;
            ;
            ;
            ; ; ; ;
            ; ;
            // ---- epoch anchor
            if (ep_rise && ADM) begin
                ; ; ; ; ;
            end else if (eact) ;
            if (halt) begin ; ; ; end
            // ---- AUTO token anchor: first token at E_TOK, then every PERIOD
            if (AUTO && eact && !halt) begin
                if (e == E_TOK - GO_OFS - 2) begin ; ; ; ; end
                else if (prun) begin
                    if (pcnt == PERIOD) begin ; ; ; end
                    else ;
                end
            end
            if (init_copy0) begin
                // TX entry i (even step), RX entry i (odd step), then the two segment-1 bases
                ;
                if (ip < 2 * NE) begin
                    ;
                    ;
;
;
;
                    ; ;
                end else begin
                    ;
                    ;
                    ; ;
                end
                ;
                if (ip == NI - 1) begin ; ; ; end
                if (go_in) ;
            end else if (halt) begin
                ;                            // exceptional mode: the HOST replays from the next epoch
            end else if (ADM && eact && (e == 32'd1 || e == 32'd2) && tokbase) begin
                // new epoch: back to the admission segment (the calendars are stopped after the epoch begin)
                ; ;
                ; ;
                if (e == 32'd2) ;
                if (running_copy0) ;
            end else if (ADM && eact && e == E_ADM && adm_pend) begin
                if (!cal_ready || tokbase || running_copy0) ;
                ; ; ; ;
            end else if (ADM && eact && (e == E_SW || e == E_SW + 1) && adm_run) begin
                // admission over: segment-1 bases to the token run
                ; ;
                ; ;
                if (e == E_SW + 1) begin ; ; ; ; end
            end else if (running_copy0) begin
                if (go_now) ;                  // a second token start inside a running_copy0 program
                ;
                if (t + 1'b1 == nxt) begin
                    ; ; ;
                    if (li == NL - 1) ; else li_part0 = li + 1'b1;
                end
            end else if (go_now) begin
                if (!cal_ready || !adm_done || !tokbase) ;
                ; ; ;
                ; ; li_part0 = 6'd1;
            end else if (reload) begin
                ; ; ; ;
            end
        
        li_next[5:0] = li_part0[5:0];
    end
    always @* begin
        layer_part0 = layer;
            ;
            ;
            ; ; ; ;
            ; ;
            // ---- epoch anchor
            if (ep_rise && ADM) begin
                ; ; ; ; ;
            end else if (eact) ;
            if (halt) begin ; ; ; end
            // ---- AUTO token anchor: first token at E_TOK, then every PERIOD
            if (AUTO && eact && !halt) begin
                if (e == E_TOK - GO_OFS - 2) begin ; ; ; ; end
                else if (prun) begin
                    if (pcnt == PERIOD) begin ; ; ; end
                    else ;
                end
            end
            if (init_copy1) begin
                // TX entry i (even step), RX entry i (odd step), then the two segment-1 bases
                ;
                if (ip < 2 * NE) begin
                    ;
                    ;
;
;
;
                    ; ;
                end else begin
                    ;
                    ;
                    ; ;
                end
                ;
                if (ip == NI - 1) begin ; ; ; end
                if (go_in) ;
            end else if (halt) begin
                ;                            // exceptional mode: the HOST replays from the next epoch
            end else if (ADM && eact && (e == 32'd1 || e == 32'd2) && tokbase) begin
                // new epoch: back to the admission segment (the calendars are stopped after the epoch begin)
                ; ;
                ; ;
                if (e == 32'd2) ;
                if (running_copy1) ;
            end else if (ADM && eact && e == E_ADM && adm_pend) begin
                if (!cal_ready || tokbase || running_copy1) ;
                ; ; layer_part0 = 6'h3f; ;
            end else if (ADM && eact && (e == E_SW || e == E_SW + 1) && adm_run) begin
                // admission over: segment-1 bases to the token run
                ; ;
                ; ;
                if (e == E_SW + 1) begin ; ; ; ; end
            end else if (running_copy1) begin
                if (go_now) ;                  // a second token start inside a running_copy1 program
                ;
                if (t + 1'b1 == nxt) begin
                    ; ; layer_part0 = li;
                    if (li == NL - 1) ; else ;
                end
            end else if (go_now) begin
                if (!cal_ready || !adm_done || !tokbase) ;
                ; ; layer_part0 = '0;
                ; ; ;
            end else if (reload) begin
                ; ; ; ;
            end
        
        layer_next[5:0] = layer_part0[5:0];
    end
    always @* begin
        go_d_part0 = go_d;
            go_d_part0 = {go_d[GW-1:0], go_in};
            ;
            ; ; ; ;
            ; ;
            // ---- epoch anchor
            if (ep_rise && ADM) begin
                ; ; ; ; ;
            end else if (eact) ;
            if (halt) begin ; ; ; end
            // ---- AUTO token anchor: first token at E_TOK, then every PERIOD
            if (AUTO && eact && !halt) begin
                if (e == E_TOK - GO_OFS - 2) begin ; ; ; ; end
                else if (prun) begin
                    if (pcnt == PERIOD) begin ; ; ; end
                    else ;
                end
            end
            if (init_copy2) begin
                // TX entry i (even step), RX entry i (odd step), then the two segment-1 bases
                ;
                if (ip < 2 * NE) begin
                    ;
                    ;
;
;
;
                    ; ;
                end else begin
                    ;
                    ;
                    ; ;
                end
                ;
                if (ip == NI - 1) begin ; ; ; end
                if (go_in) ;
            end else if (halt) begin
                ;                            // exceptional mode: the HOST replays from the next epoch
            end else if (ADM && eact && (e == 32'd1 || e == 32'd2) && tokbase) begin
                // new epoch: back to the admission segment (the calendars are stopped after the epoch begin)
                ; ;
                ; ;
                if (e == 32'd2) ;
                if (running_copy2) ;
            end else if (ADM && eact && e == E_ADM && adm_pend) begin
                if (!cal_ready || tokbase || running_copy2) ;
                ; ; ; ;
            end else if (ADM && eact && (e == E_SW || e == E_SW + 1) && adm_run) begin
                // admission over: segment-1 bases to the token run
                ; ;
                ; ;
                if (e == E_SW + 1) begin ; ; ; ; end
            end else if (running_copy2) begin
                if (go_now) ;                  // a second token start inside a running_copy2 program
                ;
                if (t + 1'b1 == nxt) begin
                    ; ; ;
                    if (li == NL - 1) ; else ;
                end
            end else if (go_now) begin
                if (!cal_ready || !adm_done || !tokbase) ;
                ; ; ;
                ; ; ;
            end else if (reload) begin
                ; ; ; ;
            end
        
        go_d_next[1:0] = go_d_part0[1:0];
    end
    always @* begin
        ep_q_part0 = ep_q;
            ;
            ep_q_part0 = epoch_go;
            ; ; ; ;
            ; ;
            // ---- epoch anchor
            if (ep_rise && ADM) begin
                ; ; ; ; ;
            end else if (eact) ;
            if (halt) begin ; ; ; end
            // ---- AUTO token anchor: first token at E_TOK, then every PERIOD
            if (AUTO && eact && !halt) begin
                if (e == E_TOK - GO_OFS - 2) begin ; ; ; ; end
                else if (prun) begin
                    if (pcnt == PERIOD) begin ; ; ; end
                    else ;
                end
            end
            if (init_copy0) begin
                // TX entry i (even step), RX entry i (odd step), then the two segment-1 bases
                ;
                if (ip < 2 * NE) begin
                    ;
                    ;
;
;
;
                    ; ;
                end else begin
                    ;
                    ;
                    ; ;
                end
                ;
                if (ip == NI - 1) begin ; ; ; end
                if (go_in) ;
            end else if (halt) begin
                ;                            // exceptional mode: the HOST replays from the next epoch
            end else if (ADM && eact && (e == 32'd1 || e == 32'd2) && tokbase) begin
                // new epoch: back to the admission segment (the calendars are stopped after the epoch begin)
                ; ;
                ; ;
                if (e == 32'd2) ;
                if (running_copy0) ;
            end else if (ADM && eact && e == E_ADM && adm_pend) begin
                if (!cal_ready || tokbase || running_copy0) ;
                ; ; ; ;
            end else if (ADM && eact && (e == E_SW || e == E_SW + 1) && adm_run) begin
                // admission over: segment-1 bases to the token run
                ; ;
                ; ;
                if (e == E_SW + 1) begin ; ; ; ; end
            end else if (running_copy0) begin
                if (go_now) ;                  // a second token start inside a running_copy0 program
                ;
                if (t + 1'b1 == nxt) begin
                    ; ; ;
                    if (li == NL - 1) ; else ;
                end
            end else if (go_now) begin
                if (!cal_ready || !adm_done || !tokbase) ;
                ; ; ;
                ; ; ;
            end else if (reload) begin
                ; ; ; ;
            end
        
        ep_q_next[0:0] = ep_q_part0[0:0];
    end
    always @* begin
        eact_part0 = eact;
            ;
            ;
            ; ; ; ;
            ; ;
            // ---- epoch anchor
            if (ep_rise && ADM) begin
                eact_part0 = 1'b1; ; ; ; ;
            end else if (eact) ;
            if (halt) begin eact_part0 = 1'b0; ; ; end
            // ---- AUTO token anchor: first token at E_TOK, then every PERIOD
            if (AUTO && eact && !halt) begin
                if (e == E_TOK - GO_OFS - 2) begin ; ; ; ; end
                else if (prun) begin
                    if (pcnt == PERIOD) begin ; ; ; end
                    else ;
                end
            end
            if (init_copy1) begin
                // TX entry i (even step), RX entry i (odd step), then the two segment-1 bases
                ;
                if (ip < 2 * NE) begin
                    ;
                    ;
;
;
;
                    ; ;
                end else begin
                    ;
                    ;
                    ; ;
                end
                ;
                if (ip == NI - 1) begin ; ; ; end
                if (go_in) ;
            end else if (halt) begin
                ;                            // exceptional mode: the HOST replays from the next epoch
            end else if (ADM && eact && (e == 32'd1 || e == 32'd2) && tokbase) begin
                // new epoch: back to the admission segment (the calendars are stopped after the epoch begin)
                ; ;
                ; ;
                if (e == 32'd2) ;
                if (running_copy1) ;
            end else if (ADM && eact && e == E_ADM && adm_pend) begin
                if (!cal_ready || tokbase || running_copy1) ;
                ; ; ; ;
            end else if (ADM && eact && (e == E_SW || e == E_SW + 1) && adm_run) begin
                // admission over: segment-1 bases to the token run
                ; ;
                ; ;
                if (e == E_SW + 1) begin ; ; ; ; end
            end else if (running_copy1) begin
                if (go_now) ;                  // a second token start inside a running_copy1 program
                ;
                if (t + 1'b1 == nxt) begin
                    ; ; ;
                    if (li == NL - 1) ; else ;
                end
            end else if (go_now) begin
                if (!cal_ready || !adm_done || !tokbase) ;
                ; ; ;
                ; ; ;
            end else if (reload) begin
                ; ; ; ;
            end
        
        eact_next[0:0] = eact_part0[0:0];
    end
    always @* begin
        e_part0 = e;
            ;
            ;
            ; ; ; ;
            ; ;
            // ---- epoch anchor
            if ((epoch_go && !ep_q_copy0) && ADM) begin
                ; e_part0 = 32'd1; ; ; ;
            end else if (eact) e_part0 = e + 32'd1;
            if (halt) begin ; ; ; end
            // ---- AUTO token anchor: first token at E_TOK, then every PERIOD
            if (AUTO && eact && !halt) begin
                if (e == E_TOK - GO_OFS - 2) begin ; ; ; ; end
                else if (prun) begin
                    if (pcnt == PERIOD) begin ; ; ; end
                    else ;
                end
            end
            if (init_copy2) begin
                // TX entry i (even step), RX entry i (odd step), then the two segment-1 bases
                ;
                if (ip < 2 * NE) begin
                    ;
                    ;
;
;
;
                    ; ;
                end else begin
                    ;
                    ;
                    ; ;
                end
                ;
                if (ip == NI - 1) begin ; ; ; end
                if (go_in) ;
            end else if (halt) begin
                ;                            // exceptional mode: the HOST replays from the next epoch
            end else if (ADM && eact && (e == 32'd1 || e == 32'd2) && tokbase) begin
                // new epoch: back to the admission segment (the calendars are stopped after the epoch begin)
                ; ;
                ; ;
                if (e == 32'd2) ;
                if (running_copy2) ;
            end else if (ADM && eact && e == E_ADM && adm_pend) begin
                if (!cal_ready || tokbase || running_copy2) ;
                ; ; ; ;
            end else if (ADM && eact && (e == E_SW || e == E_SW + 1) && adm_run) begin
                // admission over: segment-1 bases to the token run
                ; ;
                ; ;
                if (e == E_SW + 1) begin ; ; ; ; end
            end else if (running_copy2) begin
                if (go_now) ;                  // a second token start inside a running_copy2 program
                ;
                if (t + 1'b1 == nxt) begin
                    ; ; ;
                    if (li == NL - 1) ; else ;
                end
            end else if (go_now) begin
                if (!cal_ready || !adm_done || !tokbase) ;
                ; ; ;
                ; ; ;
            end else if (reload) begin
                ; ; ; ;
            end
        
        e_next[15:0] = e_part0[15:0];
    end
    always @* begin
        e_part1 = e;
            ;
            ;
            ; ; ; ;
            ; ;
            // ---- epoch anchor
            if ((epoch_go && !ep_q_copy1) && ADM) begin
                ; e_part1 = 32'd1; ; ; ;
            end else if (eact) e_part1 = e + 32'd1;
            if (halt) begin ; ; ; end
            // ---- AUTO token anchor: first token at E_TOK, then every PERIOD
            if (AUTO && eact && !halt) begin
                if (e == E_TOK - GO_OFS - 2) begin ; ; ; ; end
                else if (prun) begin
                    if (pcnt == PERIOD) begin ; ; ; end
                    else ;
                end
            end
            if (init_copy0) begin
                // TX entry i (even step), RX entry i (odd step), then the two segment-1 bases
                ;
                if (ip < 2 * NE) begin
                    ;
                    ;
;
;
;
                    ; ;
                end else begin
                    ;
                    ;
                    ; ;
                end
                ;
                if (ip == NI - 1) begin ; ; ; end
                if (go_in) ;
            end else if (halt) begin
                ;                            // exceptional mode: the HOST replays from the next epoch
            end else if (ADM && eact && (e == 32'd1 || e == 32'd2) && tokbase) begin
                // new epoch: back to the admission segment (the calendars are stopped after the epoch begin)
                ; ;
                ; ;
                if (e == 32'd2) ;
                if (running_copy0) ;
            end else if (ADM && eact && e == E_ADM && adm_pend) begin
                if (!cal_ready || tokbase || running_copy0) ;
                ; ; ; ;
            end else if (ADM && eact && (e == E_SW || e == E_SW + 1) && adm_run) begin
                // admission over: segment-1 bases to the token run
                ; ;
                ; ;
                if (e == E_SW + 1) begin ; ; ; ; end
            end else if (running_copy0) begin
                if (go_now) ;                  // a second token start inside a running_copy0 program
                ;
                if (t + 1'b1 == nxt) begin
                    ; ; ;
                    if (li == NL - 1) ; else ;
                end
            end else if (go_now) begin
                if (!cal_ready || !adm_done || !tokbase) ;
                ; ; ;
                ; ; ;
            end else if (reload) begin
                ; ; ; ;
            end
        
        e_next[31:16] = e_part1[31:16];
    end
    always @* begin
        tokbase_part0 = tokbase;
            ;
            ;
            ; ; ; ;
            ; ;
            // ---- epoch anchor
            if (ep_rise && ADM) begin
                ; ; ; ; ;
            end else if (eact) ;
            if (halt) begin ; ; ; end
            // ---- AUTO token anchor: first token at E_TOK, then every PERIOD
            if (AUTO && eact && !halt) begin
                if (e == E_TOK - GO_OFS - 2) begin ; ; ; ; end
                else if (prun) begin
                    if (pcnt == PERIOD) begin ; ; ; end
                    else ;
                end
            end
            if (init_copy0) begin
                // TX entry i (even step), RX entry i (odd step), then the two segment-1 bases
                ;
                if (ip < 2 * NE) begin
                    ;
                    ;
;
;
;
                    ; ;
                end else begin
                    ;
                    ;
                    ; ;
                end
                ;
                if (ip == NI - 1) begin ; ; tokbase_part0 = (ADM == 0); end
                if (go_in) ;
            end else if (halt) begin
                ;                            // exceptional mode: the HOST replays from the next epoch
            end else if (ADM && eact && (e == 32'd1 || e == 32'd2) && tokbase) begin
                // new epoch: back to the admission segment (the calendars are stopped after the epoch begin)
                ; ;
                ; ;
                if (e == 32'd2) tokbase_part0 = 1'b0;
                if (running_copy0) ;
            end else if (ADM && eact && e == E_ADM && adm_pend) begin
                if (!cal_ready || tokbase || running_copy0) ;
                ; ; ; ;
            end else if (ADM && eact && (e == E_SW || e == E_SW + 1) && adm_run) begin
                // admission over: segment-1 bases to the token run
                ; ;
                ; ;
                if (e == E_SW + 1) begin tokbase_part0 = 1'b1; ; ; ; end
            end else if (running_copy0) begin
                if (go_now) ;                  // a second token start inside a running_copy0 program
                ;
                if (t + 1'b1 == nxt) begin
                    ; ; ;
                    if (li == NL - 1) ; else ;
                end
            end else if (go_now) begin
                if (!cal_ready || !adm_done || !tokbase) ;
                ; ; ;
                ; ; ;
            end else if (reload) begin
                ; ; ; tokbase_part0 = 1'b0;
            end
        
        tokbase_next[0:0] = tokbase_part0[0:0];
    end
    always @* begin
        adm_pend_part0 = adm_pend;
            ;
            ;
            ; ; ; ;
            ; ;
            // ---- epoch anchor
            if (ep_rise && ADM) begin
                ; ; adm_pend_part0 = 1'b1; ; ;
            end else if (eact) ;
            if (halt) begin ; ; ; end
            // ---- AUTO token anchor: first token at E_TOK, then every PERIOD
            if (AUTO && eact && !halt) begin
                if (e == E_TOK - GO_OFS - 2) begin ; ; ; ; end
                else if (prun) begin
                    if (pcnt == PERIOD) begin ; ; ; end
                    else ;
                end
            end
            if (init_copy1) begin
                // TX entry i (even step), RX entry i (odd step), then the two segment-1 bases
                ;
                if (ip < 2 * NE) begin
                    ;
                    ;
;
;
;
                    ; ;
                end else begin
                    ;
                    ;
                    ; ;
                end
                ;
                if (ip == NI - 1) begin ; ; ; end
                if (go_in) ;
            end else if (halt) begin
                ;                            // exceptional mode: the HOST replays from the next epoch
            end else if (ADM && eact && (e == 32'd1 || e == 32'd2) && tokbase) begin
                // new epoch: back to the admission segment (the calendars are stopped after the epoch begin)
                ; ;
                ; ;
                if (e == 32'd2) ;
                if (running_copy1) ;
            end else if (ADM && eact && e == E_ADM && adm_pend) begin
                if (!cal_ready || tokbase || running_copy1) ;
                ; ; ; ;
            end else if (ADM && eact && (e == E_SW || e == E_SW + 1) && adm_run) begin
                // admission over: segment-1 bases to the token run
                ; ;
                ; ;
                if (e == E_SW + 1) begin ; ; adm_pend_part0 = 1'b0; ; end
            end else if (running_copy1) begin
                if (go_now) ;                  // a second token start inside a running_copy1 program
                ;
                if (t + 1'b1 == nxt) begin
                    ; ; ;
                    if (li == NL - 1) ; else ;
                end
            end else if (go_now) begin
                if (!cal_ready || !adm_done || !tokbase) ;
                ; ; ;
                ; ; ;
            end else if (reload) begin
                ; ; ; ;
            end
        
        adm_pend_next[0:0] = adm_pend_part0[0:0];
    end
    always @* begin
        adm_run_part0 = adm_run;
            ;
            ;
            ; ; ; ;
            ; ;
            // ---- epoch anchor
            if (ep_rise && ADM) begin
                ; ; ; ; ;
            end else if (eact) ;
            if (halt) begin ; ; adm_run_part0 = 1'b0; end
            // ---- AUTO token anchor: first token at E_TOK, then every PERIOD
            if (AUTO && eact && !halt) begin
                if (e == E_TOK - GO_OFS - 2) begin ; ; ; ; end
                else if (prun) begin
                    if (pcnt == PERIOD) begin ; ; ; end
                    else ;
                end
            end
            if (init_copy2) begin
                // TX entry i (even step), RX entry i (odd step), then the two segment-1 bases
                ;
                if (ip < 2 * NE) begin
                    ;
                    ;
;
;
;
                    ; ;
                end else begin
                    ;
                    ;
                    ; ;
                end
                ;
                if (ip == NI - 1) begin ; ; ; end
                if (go_in) ;
            end else if (halt) begin
                ;                            // exceptional mode: the HOST replays from the next epoch
            end else if (ADM && eact && (e == 32'd1 || e == 32'd2) && tokbase) begin
                // new epoch: back to the admission segment (the calendars are stopped after the epoch begin)
                ; ;
                ; ;
                if (e == 32'd2) ;
                if (running_copy2) ;
            end else if (ADM && eact && e == E_ADM && adm_pend) begin
                if (!cal_ready || tokbase || running_copy2) ;
                ; ; ; adm_run_part0 = 1'b1;
            end else if (ADM && eact && (e == E_SW || e == E_SW + 1) && adm_run) begin
                // admission over: segment-1 bases to the token run
                ; ;
                ; ;
                if (e == E_SW + 1) begin ; adm_run_part0 = 1'b0; ; ; end
            end else if (running_copy2) begin
                if (go_now) ;                  // a second token start inside a running_copy2 program
                ;
                if (t + 1'b1 == nxt) begin
                    ; ; ;
                    if (li == NL - 1) ; else ;
                end
            end else if (go_now) begin
                if (!cal_ready || !adm_done || !tokbase) ;
                ; ; ;
                ; ; ;
            end else if (reload) begin
                ; ; ; ;
            end
        
        adm_run_next[0:0] = adm_run_part0[0:0];
    end
    always @* begin
        adm_done_part0 = adm_done;
            ;
            ;
            ; ; ; ;
            ; ;
            // ---- epoch anchor
            if (ep_rise && ADM) begin
                ; ; ; adm_done_part0 = 1'b0; ;
            end else if (eact) ;
            if (halt) begin ; ; ; end
            // ---- AUTO token anchor: first token at E_TOK, then every PERIOD
            if (AUTO && eact && !halt) begin
                if (e == E_TOK - GO_OFS - 2) begin ; ; ; ; end
                else if (prun) begin
                    if (pcnt == PERIOD) begin ; ; ; end
                    else ;
                end
            end
            if (init_copy0) begin
                // TX entry i (even step), RX entry i (odd step), then the two segment-1 bases
                ;
                if (ip < 2 * NE) begin
                    ;
                    ;
;
;
;
                    ; ;
                end else begin
                    ;
                    ;
                    ; ;
                end
                ;
                if (ip == NI - 1) begin ; ; ; end
                if (go_in) ;
            end else if (halt) begin
                ;                            // exceptional mode: the HOST replays from the next epoch
            end else if (ADM && eact && (e == 32'd1 || e == 32'd2) && tokbase) begin
                // new epoch: back to the admission segment (the calendars are stopped after the epoch begin)
                ; ;
                ; ;
                if (e == 32'd2) ;
                if (running_copy0) ;
            end else if (ADM && eact && e == E_ADM && adm_pend) begin
                if (!cal_ready || tokbase || running_copy0) ;
                ; ; ; ;
            end else if (ADM && eact && (e == E_SW || e == E_SW + 1) && adm_run) begin
                // admission over: segment-1 bases to the token run
                ; ;
                ; ;
                if (e == E_SW + 1) begin ; ; ; adm_done_part0 = 1'b1; end
            end else if (running_copy0) begin
                if (go_now) ;                  // a second token start inside a running_copy0 program
                ;
                if (t + 1'b1 == nxt) begin
                    ; ; ;
                    if (li == NL - 1) ; else ;
                end
            end else if (go_now) begin
                if (!cal_ready || !adm_done || !tokbase) ;
                ; ; ;
                ; ; ;
            end else if (reload) begin
                ; ; ; ;
            end
        
        adm_done_next[0:0] = adm_done_part0[0:0];
    end
    always @* begin
        auto_go_part0 = auto_go;
            ;
            ;
            ; ; ; ;
            auto_go_part0 = 1'b0; ;
            // ---- epoch anchor
            if (ep_rise && ADM) begin
                ; ; ; ; ;
            end else if (eact) ;
            if (halt) begin ; ; ; end
            // ---- AUTO token anchor: first token at E_TOK, then every PERIOD
            if (AUTO && eact && !halt) begin
                if (e == E_TOK - GO_OFS - 2) begin auto_go_part0 = 1'b1; ; ; ; end
                else if (prun) begin
                    if (pcnt == PERIOD) begin auto_go_part0 = 1'b1; ; ; end
                    else ;
                end
            end
            if (init_copy1) begin
                // TX entry i (even step), RX entry i (odd step), then the two segment-1 bases
                ;
                if (ip < 2 * NE) begin
                    ;
                    ;
;
;
;
                    ; ;
                end else begin
                    ;
                    ;
                    ; ;
                end
                ;
                if (ip == NI - 1) begin ; ; ; end
                if (go_in) ;
            end else if (halt) begin
                ;                            // exceptional mode: the HOST replays from the next epoch
            end else if (ADM && eact && (e == 32'd1 || e == 32'd2) && tokbase) begin
                // new epoch: back to the admission segment (the calendars are stopped after the epoch begin)
                ; ;
                ; ;
                if (e == 32'd2) ;
                if (running_copy1) ;
            end else if (ADM && eact && e == E_ADM && adm_pend) begin
                if (!cal_ready || tokbase || running_copy1) ;
                ; ; ; ;
            end else if (ADM && eact && (e == E_SW || e == E_SW + 1) && adm_run) begin
                // admission over: segment-1 bases to the token run
                ; ;
                ; ;
                if (e == E_SW + 1) begin ; ; ; ; end
            end else if (running_copy1) begin
                if (go_now) ;                  // a second token start inside a running_copy1 program
                ;
                if (t + 1'b1 == nxt) begin
                    ; ; ;
                    if (li == NL - 1) ; else ;
                end
            end else if (go_now) begin
                if (!cal_ready || !adm_done || !tokbase) ;
                ; ; ;
                ; ; ;
            end else if (reload) begin
                ; ; ; ;
            end
        
        auto_go_next[0:0] = auto_go_part0[0:0];
    end
    always @* begin
        pcnt_part0 = pcnt;
            ;
            ;
            ; ; ; ;
            ; ;
            // ---- epoch anchor
            if (ep_rise && ADM) begin
                ; ; ; ; ;
            end else if (eact) ;
            if (halt) begin ; ; ; end
            // ---- AUTO token anchor: first token at E_TOK, then every PERIOD
            if (AUTO && eact && !halt) begin
                if (e == E_TOK - GO_OFS - 2) begin ; ; pcnt_part0 = 32'd1; ; end
                else if (prun) begin
                    if (pcnt == PERIOD) begin ; pcnt_part0 = 32'd1; ; end
                    else pcnt_part0 = pcnt + 32'd1;
                end
            end
            if (init_copy2) begin
                // TX entry i (even step), RX entry i (odd step), then the two segment-1 bases
                ;
                if (ip < 2 * NE) begin
                    ;
                    ;
;
;
;
                    ; ;
                end else begin
                    ;
                    ;
                    ; ;
                end
                ;
                if (ip == NI - 1) begin ; ; ; end
                if (go_in) ;
            end else if (halt) begin
                ;                            // exceptional mode: the HOST replays from the next epoch
            end else if (ADM && eact && (e == 32'd1 || e == 32'd2) && tokbase) begin
                // new epoch: back to the admission segment (the calendars are stopped after the epoch begin)
                ; ;
                ; ;
                if (e == 32'd2) ;
                if (running_copy2) ;
            end else if (ADM && eact && e == E_ADM && adm_pend) begin
                if (!cal_ready || tokbase || running_copy2) ;
                ; ; ; ;
            end else if (ADM && eact && (e == E_SW || e == E_SW + 1) && adm_run) begin
                // admission over: segment-1 bases to the token run
                ; ;
                ; ;
                if (e == E_SW + 1) begin ; ; ; ; end
            end else if (running_copy2) begin
                if (go_now) ;                  // a second token start inside a running_copy2 program
                ;
                if (t + 1'b1 == nxt) begin
                    ; ; ;
                    if (li == NL - 1) ; else ;
                end
            end else if (go_now) begin
                if (!cal_ready || !adm_done || !tokbase) ;
                ; ; ;
                ; ; ;
            end else if (reload) begin
                ; ; ; ;
            end
        
        pcnt_next[15:0] = pcnt_part0[15:0];
    end
    always @* begin
        pcnt_part1 = pcnt;
            ;
            ;
            ; ; ; ;
            ; ;
            // ---- epoch anchor
            if (ep_rise && ADM) begin
                ; ; ; ; ;
            end else if (eact) ;
            if (halt) begin ; ; ; end
            // ---- AUTO token anchor: first token at E_TOK, then every PERIOD
            if (AUTO && eact && !halt) begin
                if (e == E_TOK - GO_OFS - 2) begin ; ; pcnt_part1 = 32'd1; ; end
                else if (prun) begin
                    if (pcnt == PERIOD) begin ; pcnt_part1 = 32'd1; ; end
                    else pcnt_part1 = pcnt + 32'd1;
                end
            end
            if (init_copy0) begin
                // TX entry i (even step), RX entry i (odd step), then the two segment-1 bases
                ;
                if (ip < 2 * NE) begin
                    ;
                    ;
;
;
;
                    ; ;
                end else begin
                    ;
                    ;
                    ; ;
                end
                ;
                if (ip == NI - 1) begin ; ; ; end
                if (go_in) ;
            end else if (halt) begin
                ;                            // exceptional mode: the HOST replays from the next epoch
            end else if (ADM && eact && (e == 32'd1 || e == 32'd2) && tokbase) begin
                // new epoch: back to the admission segment (the calendars are stopped after the epoch begin)
                ; ;
                ; ;
                if (e == 32'd2) ;
                if (running_copy0) ;
            end else if (ADM && eact && e == E_ADM && adm_pend) begin
                if (!cal_ready || tokbase || running_copy0) ;
                ; ; ; ;
            end else if (ADM && eact && (e == E_SW || e == E_SW + 1) && adm_run) begin
                // admission over: segment-1 bases to the token run
                ; ;
                ; ;
                if (e == E_SW + 1) begin ; ; ; ; end
            end else if (running_copy0) begin
                if (go_now) ;                  // a second token start inside a running_copy0 program
                ;
                if (t + 1'b1 == nxt) begin
                    ; ; ;
                    if (li == NL - 1) ; else ;
                end
            end else if (go_now) begin
                if (!cal_ready || !adm_done || !tokbase) ;
                ; ; ;
                ; ; ;
            end else if (reload) begin
                ; ; ; ;
            end
        
        pcnt_next[31:16] = pcnt_part1[31:16];
    end
    always @* begin
        prun_part0 = prun;
            ;
            ;
            ; ; ; ;
            ; ;
            // ---- epoch anchor
            if (ep_rise && ADM) begin
                ; ; ; ; prun_part0 = 1'b0;
            end else if (eact) ;
            if (halt) begin ; prun_part0 = 1'b0; ; end
            // ---- AUTO token anchor: first token at E_TOK, then every PERIOD
            if (AUTO && eact && !halt) begin
                if (e == E_TOK - GO_OFS - 2) begin ; prun_part0 = 1'b1; ; ; end
                else if (prun) begin
                    if (pcnt == PERIOD) begin ; ; ; end
                    else ;
                end
            end
            if (init_copy0) begin
                // TX entry i (even step), RX entry i (odd step), then the two segment-1 bases
                ;
                if (ip < 2 * NE) begin
                    ;
                    ;
;
;
;
                    ; ;
                end else begin
                    ;
                    ;
                    ; ;
                end
                ;
                if (ip == NI - 1) begin ; ; ; end
                if (go_in) ;
            end else if (halt) begin
                ;                            // exceptional mode: the HOST replays from the next epoch
            end else if (ADM && eact && (e == 32'd1 || e == 32'd2) && tokbase) begin
                // new epoch: back to the admission segment (the calendars are stopped after the epoch begin)
                ; ;
                ; ;
                if (e == 32'd2) ;
                if (running_copy0) ;
            end else if (ADM && eact && e == E_ADM && adm_pend) begin
                if (!cal_ready || tokbase || running_copy0) ;
                ; ; ; ;
            end else if (ADM && eact && (e == E_SW || e == E_SW + 1) && adm_run) begin
                // admission over: segment-1 bases to the token run
                ; ;
                ; ;
                if (e == E_SW + 1) begin ; ; ; ; end
            end else if (running_copy0) begin
                if (go_now) ;                  // a second token start inside a running_copy0 program
                ;
                if (t + 1'b1 == nxt) begin
                    ; ; ;
                    if (li == NL - 1) ; else ;
                end
            end else if (go_now) begin
                if (!cal_ready || !adm_done || !tokbase) ;
                ; ; ;
                ; ; ;
            end else if (reload) begin
                ; ; ; ;
            end
        
        prun_next[0:0] = prun_part0[0:0];
    end
    always @* begin
        tok_start_part0 = tok_start;
            ;
            ;
            ; ; ; ;
            ; tok_start_part0 = 1'b0;
            // ---- epoch anchor
            if (ep_rise && ADM) begin
                ; ; ; ; ;
            end else if (eact) ;
            if (halt) begin ; ; ; end
            // ---- AUTO token anchor: first token at E_TOK, then every PERIOD
            if (AUTO && eact && !halt) begin
                if (e == E_TOK - GO_OFS - 2) begin ; ; ; tok_start_part0 = 1'b1; end
                else if (prun) begin
                    if (pcnt == PERIOD) begin ; ; tok_start_part0 = 1'b1; end
                    else ;
                end
            end
            if (init_copy1) begin
                // TX entry i (even step), RX entry i (odd step), then the two segment-1 bases
                ;
                if (ip < 2 * NE) begin
                    ;
                    ;
;
;
;
                    ; ;
                end else begin
                    ;
                    ;
                    ; ;
                end
                ;
                if (ip == NI - 1) begin ; ; ; end
                if (go_in) ;
            end else if (halt) begin
                ;                            // exceptional mode: the HOST replays from the next epoch
            end else if (ADM && eact && (e == 32'd1 || e == 32'd2) && tokbase) begin
                // new epoch: back to the admission segment (the calendars are stopped after the epoch begin)
                ; ;
                ; ;
                if (e == 32'd2) ;
                if (running_copy1) ;
            end else if (ADM && eact && e == E_ADM && adm_pend) begin
                if (!cal_ready || tokbase || running_copy1) ;
                ; ; ; ;
            end else if (ADM && eact && (e == E_SW || e == E_SW + 1) && adm_run) begin
                // admission over: segment-1 bases to the token run
                ; ;
                ; ;
                if (e == E_SW + 1) begin ; ; ; ; end
            end else if (running_copy1) begin
                if (go_now) ;                  // a second token start inside a running_copy1 program
                ;
                if (t + 1'b1 == nxt) begin
                    ; ; ;
                    if (li == NL - 1) ; else ;
                end
            end else if (go_now) begin
                if (!cal_ready || !adm_done || !tokbase) ;
                ; ; ;
                ; ; ;
            end else if (reload) begin
                ; ; ; ;
            end
        
        tok_start_next[0:0] = tok_start_part0[0:0];
    end
    always @* ep_q_copy0_next = ep_q_next;
    always @* ep_q_copy1_next = ep_q_next;
    always @* li_mux0_next = li_next;
    always @* li_mux1_next = li_next;
    always @* li_mux2_next = li_next;
    always @* li_mux3_next = li_next;
    always @* li_mux4_next = li_next;
    always @* ip_img0_next = ip_next;
    always @* ip_img1_next = ip_next;
    always @* ip_img2_next = ip_next;
    always @* ip_img3_next = ip_next;
    always @* running_copy0_next = running_next;
    always @* running_copy1_next = running_next;
    always @* running_copy2_next = running_next;
    always @* init_copy0_next = init_next;
    always @* init_copy1_next = init_next;
    always @* init_copy2_next = init_next;
    always @(posedge ck or negedge rst_bank_n[0])
        if (!rst_bank_n[0]) init <= 1'b1;
        else init <= init_next;
    always @(posedge ck or negedge rst_bank_n[0])
        if (!rst_bank_n[0]) ip[6:0] <= ((7'('0)) >> 0);
        else ip[6:0] <= ip_next[6:0];
    always @(posedge ck or negedge rst_bank_n[0])
        if (!rst_bank_n[0]) cal_ready <= 1'b0;
        else cal_ready <= cal_ready_next;
    always @(posedge ck or negedge rst_bank_n[0])
        if (!rst_bank_n[0]) running <= 1'b0;
        else running <= running_next;
    always @(posedge ck or negedge rst_bank_n[0])
        if (!rst_bank_n[0]) fault <= 1'b0;
        else fault <= fault_next;
    always @(posedge ck or negedge rst_bank_n[0])
        if (!rst_bank_n[0]) cfg_tx_we <= 1'b0;
        else cfg_tx_we <= cfg_tx_we_next;
    always @(posedge ck or negedge rst_bank_n[0])
        if (!rst_bank_n[0]) cfg_rx_we <= 1'b0;
        else cfg_rx_we <= cfg_rx_we_next;
    always @(posedge ck or negedge rst_bank_n[0])
        if (!rst_bank_n[0]) cfg_addr[2:0] <= ((6'('0)) >> 0);
        else cfg_addr[2:0] <= cfg_addr_next[2:0];
    always @(posedge ck or negedge rst_bank_n[1])
        if (!rst_bank_n[1]) cfg_addr[5:3] <= ((6'('0)) >> 3);
        else cfg_addr[5:3] <= cfg_addr_next[5:3];
    always @(posedge ck or negedge rst_bank_n[1])
        if (!rst_bank_n[1]) cfg_data[12:0] <= ((32'('0)) >> 0);
        else cfg_data[12:0] <= cfg_data_next[12:0];
    always @(posedge ck or negedge rst_bank_n[2])
        if (!rst_bank_n[2]) cfg_data[28:13] <= ((32'('0)) >> 13);
        else cfg_data[28:13] <= cfg_data_next[28:13];
    always @(posedge ck or negedge rst_bank_n[3])
        if (!rst_bank_n[3]) cfg_data[31:29] <= ((32'('0)) >> 29);
        else cfg_data[31:29] <= cfg_data_next[31:29];
    always @(posedge ck or negedge rst_bank_n[3])
        if (!rst_bank_n[3]) cal_start <= 1'b0;
        else cal_start <= cal_start_next;
    always @(posedge ck or negedge rst_bank_n[3])
        if (!rst_bank_n[3]) cal_seg <= 1'b0;
        else cal_seg <= cal_seg_next;
    always @(posedge ck or negedge rst_bank_n[3])
        if (!rst_bank_n[3]) t[10:0] <= ((20'('0)) >> 0);
        else t[10:0] <= t_next[10:0];
    always @(posedge ck or negedge rst_bank_n[4])
        if (!rst_bank_n[4]) t[19:11] <= ((20'('0)) >> 11);
        else t[19:11] <= t_next[19:11];
    always @(posedge ck or negedge rst_bank_n[4])
        if (!rst_bank_n[4]) li[5:0] <= ((6'('0)) >> 0);
        else li[5:0] <= li_next[5:0];
    always @(posedge ck or negedge rst_bank_n[4])
        if (!rst_bank_n[4]) layer[0:0] <= ((6'('0)) >> 0);
        else layer[0:0] <= layer_next[0:0];
    always @(posedge ck or negedge rst_bank_n[5])
        if (!rst_bank_n[5]) layer[5:1] <= ((6'('0)) >> 1);
        else layer[5:1] <= layer_next[5:1];
    always @(posedge ck or negedge rst_bank_n[5])
        if (!rst_bank_n[5]) go_d[1:0] <= ((2'('0)) >> 0);
        else go_d[1:0] <= go_d_next[1:0];
    always @(posedge ck or negedge rst_bank_n[5])
        if (!rst_bank_n[5]) ep_q <= 1'b0;
        else ep_q <= ep_q_next;
    always @(posedge ck or negedge rst_bank_n[5])
        if (!rst_bank_n[5]) eact <= 1'b0;
        else eact <= eact_next;
    always @(posedge ck or negedge rst_bank_n[5])
        if (!rst_bank_n[5]) e[6:0] <= ((32'(32'd0)) >> 0);
        else e[6:0] <= e_next[6:0];
    always @(posedge ck or negedge rst_bank_n[6])
        if (!rst_bank_n[6]) e[22:7] <= ((32'(32'd0)) >> 7);
        else e[22:7] <= e_next[22:7];
    always @(posedge ck or negedge rst_bank_n[7])
        if (!rst_bank_n[7]) e[31:23] <= ((32'(32'd0)) >> 23);
        else e[31:23] <= e_next[31:23];
    always @(posedge ck or negedge rst_bank_n[7])
        if (!rst_bank_n[7]) tokbase <= 1'b0;
        else tokbase <= tokbase_next;
    always @(posedge ck or negedge rst_bank_n[7])
        if (!rst_bank_n[7]) adm_pend <= 1'b0;
        else adm_pend <= adm_pend_next;
    always @(posedge ck or negedge rst_bank_n[7])
        if (!rst_bank_n[7]) adm_run <= 1'b0;
        else adm_run <= adm_run_next;
    always @(posedge ck or negedge rst_bank_n[7])
        if (!rst_bank_n[7]) adm_done <= (ADM == 0);
        else adm_done <= adm_done_next;
    always @(posedge ck or negedge rst_bank_n[7])
        if (!rst_bank_n[7]) auto_go <= 1'b0;
        else auto_go <= auto_go_next;
    always @(posedge ck or negedge rst_bank_n[7])
        if (!rst_bank_n[7]) pcnt[1:0] <= ((32'(32'd0)) >> 0);
        else pcnt[1:0] <= pcnt_next[1:0];
    always @(posedge ck or negedge rst_bank_n[8])
        if (!rst_bank_n[8]) pcnt[17:2] <= ((32'(32'd0)) >> 2);
        else pcnt[17:2] <= pcnt_next[17:2];
    always @(posedge ck or negedge rst_bank_n[9])
        if (!rst_bank_n[9]) pcnt[31:18] <= ((32'(32'd0)) >> 18);
        else pcnt[31:18] <= pcnt_next[31:18];
    always @(posedge ck or negedge rst_bank_n[9])
        if (!rst_bank_n[9]) prun <= 1'b0;
        else prun <= prun_next;
    always @(posedge ck or negedge rst_bank_n[9])
        if (!rst_bank_n[9]) tok_start <= 1'b0;
        else tok_start <= tok_start_next;
    always @(posedge ck or negedge rst_bank_n[10])
        if (!rst_bank_n[10]) ep_q_copy0 <= 1'b0;
        else ep_q_copy0 <= ep_q_copy0_next;
    always @(posedge ck or negedge rst_bank_n[10])
        if (!rst_bank_n[10]) ep_q_copy1 <= 1'b0;
        else ep_q_copy1 <= ep_q_copy1_next;
    always @(posedge ck or negedge rst_bank_n[10])
        if (!rst_bank_n[10]) li_mux0[5:0] <= ((6'('0)) >> 0);
        else li_mux0[5:0] <= li_mux0_next[5:0];
    always @(posedge ck or negedge rst_bank_n[10])
        if (!rst_bank_n[10]) li_mux1[5:0] <= ((6'('0)) >> 0);
        else li_mux1[5:0] <= li_mux1_next[5:0];
    always @(posedge ck or negedge rst_bank_n[10])
        if (!rst_bank_n[10]) li_mux2[1:0] <= ((6'('0)) >> 0);
        else li_mux2[1:0] <= li_mux2_next[1:0];
    always @(posedge ck or negedge rst_bank_n[11])
        if (!rst_bank_n[11]) li_mux2[5:2] <= ((6'('0)) >> 2);
        else li_mux2[5:2] <= li_mux2_next[5:2];
    always @(posedge ck or negedge rst_bank_n[11])
        if (!rst_bank_n[11]) li_mux3[5:0] <= ((6'('0)) >> 0);
        else li_mux3[5:0] <= li_mux3_next[5:0];
    always @(posedge ck or negedge rst_bank_n[11])
        if (!rst_bank_n[11]) li_mux4[5:0] <= ((6'('0)) >> 0);
        else li_mux4[5:0] <= li_mux4_next[5:0];
    always @(posedge ck or negedge rst_bank_n[12])
        if (!rst_bank_n[12]) ip_img0[6:0] <= ((7'('0)) >> 0);
        else ip_img0[6:0] <= ip_img0_next[6:0];
    always @(posedge ck or negedge rst_bank_n[12])
        if (!rst_bank_n[12]) ip_img1[6:0] <= ((7'('0)) >> 0);
        else ip_img1[6:0] <= ip_img1_next[6:0];
    always @(posedge ck or negedge rst_bank_n[12])
        if (!rst_bank_n[12]) ip_img2[1:0] <= ((7'('0)) >> 0);
        else ip_img2[1:0] <= ip_img2_next[1:0];
    always @(posedge ck or negedge rst_bank_n[13])
        if (!rst_bank_n[13]) ip_img2[6:2] <= ((7'('0)) >> 2);
        else ip_img2[6:2] <= ip_img2_next[6:2];
    always @(posedge ck or negedge rst_bank_n[13])
        if (!rst_bank_n[13]) ip_img3[6:0] <= ((7'('0)) >> 0);
        else ip_img3[6:0] <= ip_img3_next[6:0];
    always @(posedge ck or negedge rst_bank_n[13])
        if (!rst_bank_n[13]) running_copy0 <= 1'b0;
        else running_copy0 <= running_copy0_next;
    always @(posedge ck or negedge rst_bank_n[13])
        if (!rst_bank_n[13]) running_copy1 <= 1'b0;
        else running_copy1 <= running_copy1_next;
    always @(posedge ck or negedge rst_bank_n[13])
        if (!rst_bank_n[13]) running_copy2 <= 1'b0;
        else running_copy2 <= running_copy2_next;
    always @(posedge ck or negedge rst_bank_n[13])
        if (!rst_bank_n[13]) init_copy0 <= 1'b1;
        else init_copy0 <= init_copy0_next;
    always @(posedge ck or negedge rst_bank_n[14])
        if (!rst_bank_n[14]) init_copy1 <= 1'b1;
        else init_copy1 <= init_copy1_next;
    always @(posedge ck or negedge rst_bank_n[14])
        if (!rst_bank_n[14]) init_copy2 <= 1'b1;
        else init_copy2 <= init_copy2_next;
endmodule
