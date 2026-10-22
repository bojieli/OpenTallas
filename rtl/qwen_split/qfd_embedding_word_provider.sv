`timescale 1ns/1ps
// qfd_embedding_word_provider -- compute-die embedding row store under its die name (Q-NETLIST, 2026-10-16).
// Replaces qkd_embedding_static_core_provider on the COMPUTE die: that provider starts with the HBM half-beat join
// (qkd_embedding_static_join, 256-b low/high halves), which belongs beside the HBM on the KV/system die.  On the compute
// die the row arrives as whole 512-b words over the static D2D link (one word per edge, kinds 6/7, plus the kind-8 row
// header carrying the BF16 scale), decoded by qfd_sys_face.  This master is the existing word-level part of the provider,
// unchanged: qkd_embedding_static_preload_face (actual word vs compiler slot / identity check, one register edge) and
// qkd_embedding_static_core_store (the mapped ot_sram_1r1w_64x512_m1_r2c2 row SRAM + the BF16 scale register serving the
// sequencer's embed_code / embed_scale ROM ports).  Same core / embed / fault ports as the old provider (the die join's
// edges to the sequencer and the SU are unchanged); the beat_* inputs become word_* inputs.
// REGIONAL RESET (Q-EMBPROV rr1 2026-10-17, die standard item "regional reset"; structural fix of the ec1 native pin
// audit FAIL rst_n capture 251.7 ps > 190: the port's async clear fanned straight out to the 104 reset flops of both
// children): the rst_n port drives only the in-line ot_rst_relay structure (2 synchroniser flops + one kept relay flop
// per region, assert asynchronous, release synchronous); each region resets from its own relay flop, placed with its
// loads.  Regions: 0 preload face (4 flops, E face), 1 core store (100 flops: row-filled map / resident identity /
// fault, beside the row SRAM).  Release is 3 edges after the port, the same edge in both regions (initialisation only;
// every production event is anchored to fill_begin / the preload slots / core_start, never to the reset edge).
module qfd_embedding_word_provider #(parameter integer ROPE = 0) (
    input  wire         ck, rst_n,
    input  wire         word_v,
    input  wire [511:0] word_data,
    input  wire [17:0]  word_token,
    input  wire [5:0]   word_index,
    input  wire         word_scale,
    input  wire [15:0]  word_epoch,
    input  wire         expected_word_slot,
    input  wire [17:0]  expected_token,
    input  wire [5:0]   expected_word,
    input  wire         expected_scale,
    input  wire [15:0]  expected_epoch,
    input  wire         fill_begin,
    input  wire [17:0]  fill_token,
    input  wire [15:0]  fill_epoch,
    input  wire         core_start,
    input  wire [17:0]  core_token,
    input  wire [15:0]  core_epoch,
    input  wire         embed_code_re,
    input  wire [23:0]  embed_code_addr,
    output wire [511:0] embed_code_q,
    input  wire         embed_scale_re,
    input  wire [17:0]  embed_scale_addr,
    output wire [15:0]  embed_scale_q,
    output wire         fault
);
    // ================================================================ regional reset relay (ot_rst_relay, in line)
    localparam integer RST_REGIONS = 2;
    (* async_reg = "true" *) reg [1:0] rr_s;
    (* keep = "true", dont_touch = "true" *) reg [RST_REGIONS-1:0] rr_q;   // one kept relay flop per region
    always @(posedge ck or negedge rst_n) begin
        if (!rst_n) begin rr_s <= 2'b00; rr_q <= {RST_REGIONS{1'b0}}; end
        else begin rr_s <= {rr_s[0], 1'b1}; rr_q <= {RST_REGIONS{rr_s[1]}}; end
    end
    wire rst_face = rr_q[0], rst_store = rr_q[1];

    // RoPE uses the existing scale/index pins: scale/index 0 is the BF16
    // header; scale/index 1..8 are the eight 512-bit RoPE words. The unused code-address tail selects the RoPE SRAM, preserving the
    // existing atomic code-read address/enable bundle and the die port ABI.
    wire wr_rope = ROPE && word_scale && word_index != 0;
    wire ex_rope = ROPE && expected_scale && expected_word != 0;
    localparam [23:0] ROPE_BASE = 24'd9723904; // 151936 embedding tokens * 64 code words
    wire rd_rope = ROPE && embed_code_re && embed_code_addr >= ROPE_BASE;
    wire [23:0] rope_addr = embed_code_addr - ROPE_BASE;
    wire [511:0] code_q, rope_q;
    wire [15:0] scale_q;
    wire rf;
    wire fb, slot, pv, ps, ff, sf;
    wire [17:0] ft, pt; wire [15:0] fe, pe; wire [5:0] pw; wire [511:0] pd;
    qkd_embedding_static_preload_face face (.ck(ck), .rst_n(rst_face), .word_v(word_v && !wr_rope), .word_data(word_data),
        .word_token(word_token), .word_index(word_index), .word_scale(word_scale), .word_epoch(word_epoch),
        .expected_slot(expected_word_slot && !ex_rope), .expected_token(expected_token), .expected_word(expected_word),
        .expected_scale(expected_scale), .expected_epoch(expected_epoch), .i_fill_begin(fill_begin), .i_fill_token(fill_token),
        .i_fill_epoch(fill_epoch), .fill_begin(fb), .fill_token(ft), .fill_epoch(fe), .preload_slot(slot), .preload_v(pv),
        .preload_scale(ps), .preload_word(pw), .preload_token(pt), .preload_epoch(pe), .preload_data(pd), .fault(ff));
    qkd_embedding_static_core_store store (.ck(ck), .rst_n(rst_store), .fill_begin(fb), .fill_token(ft), .fill_epoch(fe),
        .preload_slot(slot), .preload_v(pv), .preload_scale(ps), .preload_word(pw), .preload_token(pt), .preload_epoch(pe),
        .preload_data(pd), .core_start(core_start), .core_token(core_token), .core_epoch(core_epoch),
        .embed_code_re(embed_code_re && !rd_rope), .embed_code_addr(embed_code_addr), .embed_code_q(code_q),
        .embed_scale_re(embed_scale_re && !rd_rope), .embed_scale_addr(embed_scale_addr), .embed_scale_q(scale_q), .fault(sf));
    assign fault = ff | sf | rf;
    assign embed_scale_q = scale_q;
    generate if (ROPE) begin : g_rope
        reg [7:0] filled;
        reg bad;
        // Payload identity is data, reset only the validity/control state.
        reg [17:0] resident_token;
        reg [15:0] resident_epoch;
        reg selected;
        wire valid_word = word_index >= 1 && word_index <= 8;
        wire [5:0] write_addr = word_index - 6'd1;
        always @(posedge ck) begin
            if (fill_begin) begin resident_token <= fill_token; resident_epoch <= fill_epoch; end
            if (embed_code_re) selected <= rd_rope;
        end
        always @(posedge ck or negedge rst_store)
            if (!rst_store) begin filled <= 0; bad <= 0; end
            else begin
                if (fill_begin) begin
                    filled <= 0;
                    if (word_v || expected_word_slot || core_start || embed_code_re || embed_scale_re) bad <= 1;
                end
                if ((word_v && wr_rope) != (expected_word_slot && ex_rope)) bad <= 1;
                if (word_v && wr_rope) begin
                    if (!valid_word || word_index != expected_word || !expected_scale ||
                        word_token != expected_token || word_epoch != expected_epoch ||
                        word_token != resident_token || word_epoch != resident_epoch || fill_begin) bad <= 1;
                    if (valid_word) begin
                        if (filled[write_addr[2:0]]) bad <= 1;
                        filled[write_addr[2:0]] <= 1;
                    end
                end
                if (core_start && (!(&filled) || core_token != resident_token || core_epoch != resident_epoch)) bad <= 1;
                if (rd_rope && (!(&filled) || rope_addr >= 24'd1215488 || rope_addr[20:3] != resident_token || word_v || fill_begin)) bad <= 1;
            end
        // Reuse the closed row SRAM primitive; only addresses 0..7 are used.
        ot_sram_1r1w_64x512_m1_r2c2 ropes (
            .clk(ck), .r_ce_in(rd_rope), .r_addr_in({3'd0,rope_addr[2:0]}), .rd_out(rope_q),
            .w_ce_in(word_v && wr_rope && valid_word), .w_addr_in(write_addr), .wd_in(word_data),
            .w_mask_in({512{1'b1}}), .rr_en(2'b00), .rr_addr(12'd0), .cr_en(2'b00), .cr_sel(18'd0));
        assign embed_code_q = selected ? rope_q : code_q;
        assign rf = bad;
    end else begin : g_no_rope
        assign embed_code_q = code_q;
        assign rope_q = 512'd0;
        assign rf = 1'b0;
    end endgenerate
endmodule
