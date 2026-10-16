`timescale 1ns/1ps
// =====================================================================================================================
// Qwen3-8B TP8 split: static D2D link CALENDAR SEQUENCER (Q-DVM+LINK, 2026-10-15). One instance beside each link end
// (compute die qfd_d2d_static, KV/system die qkd_d2d_static). It is the producer of the six link-end control inputs
// that the die binds had open (cfg_tx_we, cfg_rx_we, cfg_addr, cfg_data, cal_start, cal_seg):
//
//   INIT MODE (once after reset, and again after an epoch abort only if the HOST requests it with reload):
//     the compiler's calendar images (tools/qwen_split/d2d_link_calendar.py --profile program, emitted as a constant
//     include by tools/qwen_split/d2d_cal_seq_image.py) are written through the end's cfg port: TX entry i, RX entry i
//     for i = 0..NE-1, then the TX and RX segment-1 bases.  2*NE+2 cycles, then cal_ready.  The images are model
//     constants (static ROM die: the program never changes), so the table is a constant, not a runtime memory.
//   NORMAL MODE: tok_go (one cycle, the sequencer's token start) starts the token program: cal_start with cal_seg = 1
//     GO_OFS + 1 edges after tok_go (token run: terminal RESULT, embedding row, L0), then cal_start with cal_seg = 0
//     at every compiled layer start L1..L35 (START[l] edges after the token cal_start).  No valid / ready / credit
//     selects a cycle: the start cycles are compiler constants.
//   FAULTS (sticky, never stretch the schedule): tok_go before cal_ready, tok_go while a program is running.
//     halt (the link end's epoch_abort) stops the program at once; the next tok_go (HOST replay) restarts it.
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
    parameter [TW*NL-1:0] START = '0    // START[0] = 0 (token run), START[l] = compiled layer-l start, increasing
) (
    input  wire        ck,
    input  wire        rst_n,
    input  wire        reload,          // exceptional: HOST re-writes the images (only while idle)
    input  wire        tok_go,
    input  wire        halt,
    output reg         cfg_tx_we,
    output reg         cfg_rx_we,
    output reg  [5:0]  cfg_addr,
    output reg  [31:0] cfg_data,
    output reg         cal_start,
    output reg         cal_seg,
    output reg         cal_ready,
    output reg         running,
    output reg  [5:0]  layer,           // run index of the last cal_start (0 = token run)
    output reg         fault
);
    localparam integer NI = 2 * NE + 2;
    localparam integer IW = $clog2(NI + 1);
    localparam integer GW = (GO_OFS > 0) ? GO_OFS : 1;
    reg          init;
    reg [IW-1:0] ip;
    reg [TW-1:0] t;
    reg [5:0]    li;
    reg [GW:0]   go_d;
    wire         go_now = (GO_OFS > 0) ? go_d[GO_OFS-1] : tok_go;
    wire [TW-1:0] nxt = START[TW*li +: TW];

    integer e;
    always @(posedge ck or negedge rst_n) begin
        if (!rst_n) begin
            init <= 1'b1; ip <= '0; cal_ready <= 1'b0; running <= 1'b0; fault <= 1'b0;
            cfg_tx_we <= 1'b0; cfg_rx_we <= 1'b0; cfg_addr <= '0; cfg_data <= '0;
            cal_start <= 1'b0; cal_seg <= 1'b0; t <= '0; li <= '0; layer <= '0; go_d <= '0;
        end else begin
            go_d <= {go_d[GW-1:0], tok_go};
            cfg_tx_we <= 1'b0; cfg_rx_we <= 1'b0; cal_start <= 1'b0; cal_seg <= 1'b0;
            if (init) begin
                // TX entry i (even step), RX entry i (odd step), then the two segment-1 bases
                e = ip >> 1;
                if (ip < 2 * NE) begin
                    cfg_addr <= {1'b0, 5'(e)};
                    cfg_data <= ip[0] ? RX_IMG[32*e +: 32] : TX_IMG[32*e +: 32];
                    cfg_tx_we <= ~ip[0]; cfg_rx_we <= ip[0];
                end else begin
                    cfg_addr <= 6'b100000;
                    cfg_data <= ip[0] ? RX_SEG1 : TX_SEG1;
                    cfg_tx_we <= ~ip[0]; cfg_rx_we <= ip[0];
                end
                ip <= ip + 1'b1;
                if (ip == NI - 1) begin init <= 1'b0; cal_ready <= 1'b1; end
                if (tok_go) fault <= 1'b1;
            end else if (halt) begin
                running <= 1'b0;                            // exceptional mode: the HOST replays with a new tok_go
            end else if (running) begin
                if (go_now) fault <= 1'b1;                  // a second token start inside a running program
                t <= t + 1'b1;
                if (t + 1'b1 == nxt) begin
                    cal_start <= 1'b1; cal_seg <= 1'b0; layer <= li;
                    if (li == NL - 1) running <= 1'b0; else li <= li + 1'b1;
                end
            end else if (go_now) begin
                cal_start <= 1'b1; cal_seg <= 1'b1; layer <= '0;
                running <= (NL > 1); t <= '0; li <= 6'd1;
            end else if (reload) begin
                init <= 1'b1; ip <= '0; cal_ready <= 1'b0;
            end
        end
    end
endmodule
