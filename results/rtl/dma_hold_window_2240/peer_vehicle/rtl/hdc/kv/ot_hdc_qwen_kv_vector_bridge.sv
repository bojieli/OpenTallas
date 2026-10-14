`timescale 1ns/1ps
// Elastic KV write boundary for the Qwen vector core. The core cannot stall a
// write already in its stream pipeline, so this FIFO holds one entire maximum
// KV-write instruction. The sequencer must wait for `drained` before starting
// the next stream instruction (KV_VEC_WRITE_BRIDGE mode in ot_hdc_core).
// FP32 values include the vector core's FP8 rounding; the shared ingest
// quantizer emits the physical E4M3 byte. BF16-in-FP32 values use the same path.
module ot_hdc_qwen_kv_vector_bridge #(
    parameter integer SW = 8,
    parameter integer AW = 24,
    parameter integer LOG_HD = 7,
    parameter integer LOG_TW = 2,
    parameter integer V0_ELEMENT = 1048576,
    parameter integer FIFO_BEATS = 128,
    parameter integer MAX_KV_OP_ELEMS = 1024 // shipped Qwen: 8 KV heads x 128 dimensions
) (
    input  wire clk, rst_n,
    input  wire [SW-1:0] core_we,
    input  wire [SW*AW-1:0] core_addr,
    input  wire [SW*32-1:0] core_data,
    output wire drained,
    output wire [2*SW-1:0] tl_we,
    output wire [2*SW*AW-1:0] tl_row,
    output wire [2*SW*16-1:0] tl_mask,
    output wire [2*SW*128-1:0] tl_data,
    input  wire fl_v,
    output wire fl_ready,
    input  wire [AW-1:0] fl_word_addr,
    input  wire [127:0] fl_word_data,
    input  wire flush,
    output wire mem_r_v,
    input  wire mem_r_ready,
    output wire [AW-1:0] mem_r_sector,
    input  wire mem_r_resp_v,
    input  wire [255:0] mem_r_resp_data,
    output wire mem_w_v,
    input  wire mem_w_ready,
    output wire [AW-1:0] mem_w_sector,
    output wire [255:0] mem_w_data,
    output wire fault
);
    localparam integer PW = $clog2(FIFO_BEATS);
    localparam integer CW = $clog2(FIFO_BEATS + 1);
    reg [SW-1:0] q_we [0:FIFO_BEATS-1];
    reg [SW*AW-1:0] q_addr [0:FIFO_BEATS-1];
    reg [SW*32-1:0] q_data [0:FIFO_BEATS-1];
    reg [PW-1:0] wp, rp;
    reg [CW-1:0] used;
    reg overflow;
    wire [SW-1:0] head_we = q_we[rp];
    wire [SW*AW-1:0] head_addr = q_addr[rp];
    wire [SW*32-1:0] head_data = q_data[rp];
    wire [SW*8-1:0] head_fp8;
    wire adapter_ready, adapter_idle, adapter_fault;
    wire push = |core_we;
    wire pop = used != 0 && adapter_ready;
    initial if (FIFO_BEATS*SW < MAX_KV_OP_ELEMS)
        $error("KV bridge FIFO cannot hold one complete vector KV instruction");
    genvar lane;
    generate for (lane=0; lane<SW; lane=lane+1) begin : g_fp8
        ot_hdc_ingest_fp8q u_q (.f(head_data[32*lane +: 32]), .q(head_fp8[8*lane +: 8]));
    end endgenerate
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wp <= 0; rp <= 0; used <= 0; overflow <= 0;
        end else begin
            if (push) begin
                if (used == FIFO_BEATS && !pop) overflow <= 1'b1;
                else begin
                    q_we[wp] <= core_we;
                    q_addr[wp] <= core_addr;
                    q_data[wp] <= core_data;
                    wp <= wp == FIFO_BEATS-1 ? 0 : wp + 1'b1;
                end
            end
            if (pop) rp <= rp == FIFO_BEATS-1 ? 0 : rp + 1'b1;
            if (push && (used != FIFO_BEATS || pop) && !pop) used <= used + 1'b1;
            else if (pop && !push) used <= used - 1'b1;
        end
    end
    assign drained = used == 0 && adapter_idle && !fl_v;
    assign fault = overflow || adapter_fault;
    ot_hdc_qwen_kv_write_adapter #(.SW(SW), .AW(AW), .LOG_HD(LOG_HD), .LOG_TW(LOG_TW),
                                   .V0_ELEMENT(V0_ELEMENT)) u_adapter (
        .clk(clk), .rst_n(rst_n), .in_v(used != 0), .in_ready(adapter_ready),
        .in_we(head_we), .in_addr(head_addr), .in_data(head_fp8),
        .tl_we(tl_we), .tl_row(tl_row), .tl_mask(tl_mask), .tl_data(tl_data),
        .fl_v(fl_v), .fl_ready(fl_ready), .fl_word_addr(fl_word_addr), .fl_word_data(fl_word_data),
        .flush(flush), .idle(adapter_idle),
        .mem_r_v(mem_r_v), .mem_r_ready(mem_r_ready), .mem_r_sector(mem_r_sector),
        .mem_r_resp_v(mem_r_resp_v), .mem_r_resp_data(mem_r_resp_data),
        .mem_w_v(mem_w_v), .mem_w_ready(mem_w_ready), .mem_w_sector(mem_w_sector),
        .mem_w_data(mem_w_data), .fault(adapter_fault));
endmodule
