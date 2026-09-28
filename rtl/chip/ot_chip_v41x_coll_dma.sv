`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Collective DMA of the adopted V4.1 layer die (ot_chip_v41x_die.sv): moves a
// collective's words between the tile's vector memory (external word port B)
// and the one-shot collective engine ot_rom_oneshot_die_px.
//
// A command (go: mode, tag, n words from vector-memory word src, results to
// word dst) streams the n local words into the engine (in_valid / in_ready,
// in_last on the last) and writes every result word the engine emits (it has
// no out_ready: every beat is taken the cycle it appears) to dst, dst + 1, ...
// busy falls on the engine's out_last.  Two reads are kept in flight so the
// producer side can run one word a cycle.
//
// Sequencing (when a program segment's producer has written its partial and
// the consumer may start) is the host's / package controller's, as in the
// real-core collective bench (rtl/test/tb_v41x_real_core_collective.sv): the
// adopted core has no collective-issue instruction.
// ---------------------------------------------------------------------------
module ot_chip_v41x_coll_dma #(
    parameter integer WA   = 12,          // vector-memory word address bits
    parameter integer FW   = 512,
    parameter integer TAGW = 32
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire            go,
    input  wire            mode,
    input  wire [TAGW-1:0] tag,
    input  wire [WA-1:0]   src,
    input  wire [WA-1:0]   n,
    input  wire [WA-1:0]   dst,
    output reg             busy,
    output reg  [31:0]     words_out,
    output reg  [31:0]     words_in,
    // vector-memory port (read latency 1)
    output wire            vm_re,
    output wire [WA-1:0]   vm_raddr,
    input  wire [FW-1:0]   vm_rq,
    output wire            vm_we,
    output wire [WA-1:0]   vm_waddr,
    output wire [FW-1:0]   vm_wdata,
    // engine
    output wire            e_valid,
    input  wire            e_ready,
    output wire [FW-1:0]   e_data,
    output wire            e_last,
    output reg             e_mode,
    output reg  [TAGW-1:0] e_tag,
    input  wire            o_valid,
    input  wire [FW-1:0]   o_data,
    input  wire            o_last
);
    reg [WA-1:0] rd_k, n_r, src_r, dst_r, wr_k;
    reg          rd_q;                           // a read issued last cycle
    reg [WA-1:0] rd_qk;
    // two-entry skid of read words
    reg [FW-1:0] sk_d [0:1];
    reg          sk_l [0:1];
    reg [1:0]    sk_n;
    reg          sk_h;                           // head index
    wire         pop  = e_valid && e_ready;
    // a slot is free for a new read when the words held plus the one in flight, less the one leaving, are < 2
    wire [2:0]   held = {1'b0, sk_n} + {2'b0, rd_q} - {2'b0, pop};
    assign vm_re    = busy && (rd_k != n_r) && (held < 3'd2);
    assign vm_raddr = src_r + rd_k;
    assign e_valid  = sk_n != 2'd0;
    assign e_data   = sk_d[sk_h];
    assign e_last   = sk_l[sk_h];
    assign vm_we    = busy && o_valid;
    assign vm_waddr = dst_r + wr_k;
    assign vm_wdata = o_data;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            busy <= 1'b0; rd_k <= 0; n_r <= 0; src_r <= 0; dst_r <= 0; wr_k <= 0; rd_q <= 1'b0; rd_qk <= 0;
            sk_n <= 2'd0; sk_h <= 1'b0; e_mode <= 1'b0; e_tag <= {TAGW{1'b0}};
            words_out <= 0; words_in <= 0;
            sk_d[0] <= {FW{1'b0}}; sk_d[1] <= {FW{1'b0}}; sk_l[0] <= 1'b0; sk_l[1] <= 1'b0;
        end else begin
            if (go && !busy) begin
                busy <= (n != 0); rd_k <= 0; n_r <= n; src_r <= src; dst_r <= dst; wr_k <= 0;
                e_mode <= mode; e_tag <= tag;
            end else begin
                rd_q <= vm_re; rd_qk <= rd_k;
                if (vm_re) rd_k <= rd_k + 1'b1;
                // enqueue the word read last cycle, dequeue the one the engine took
                if (rd_q) begin
                    // tail slot = head + count (mod 2); a pop this cycle moves both and leaves it in place
                    sk_d[sk_h ^ sk_n[0]] <= vm_rq;
                    sk_l[sk_h ^ sk_n[0]] <= (rd_qk == n_r - 1'b1);
                end
                if (pop) begin sk_h <= ~sk_h; words_out <= words_out + 1; end
                sk_n <= sk_n + {1'b0, rd_q} - {1'b0, pop};
                if (vm_we) begin
                    wr_k <= wr_k + 1'b1; words_in <= words_in + 1;
                    if (o_last) busy <= 1'b0;
                end
            end
        end
    end
endmodule
