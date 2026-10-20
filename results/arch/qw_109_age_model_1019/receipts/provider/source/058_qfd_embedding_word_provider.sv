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
module qfd_embedding_word_provider (
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

    wire fb, slot, pv, ps, ff, sf;
    wire [17:0] ft, pt; wire [15:0] fe, pe; wire [5:0] pw; wire [511:0] pd;
    qkd_embedding_static_preload_face face (.ck(ck), .rst_n(rst_face), .word_v(word_v), .word_data(word_data),
        .word_token(word_token), .word_index(word_index), .word_scale(word_scale), .word_epoch(word_epoch),
        .expected_slot(expected_word_slot), .expected_token(expected_token), .expected_word(expected_word),
        .expected_scale(expected_scale), .expected_epoch(expected_epoch), .i_fill_begin(fill_begin), .i_fill_token(fill_token),
        .i_fill_epoch(fill_epoch), .fill_begin(fb), .fill_token(ft), .fill_epoch(fe), .preload_slot(slot), .preload_v(pv),
        .preload_scale(ps), .preload_word(pw), .preload_token(pt), .preload_epoch(pe), .preload_data(pd), .fault(ff));
    qkd_embedding_static_core_store store (.ck(ck), .rst_n(rst_store), .fill_begin(fb), .fill_token(ft), .fill_epoch(fe),
        .preload_slot(slot), .preload_v(pv), .preload_scale(ps), .preload_word(pw), .preload_token(pt), .preload_epoch(pe),
        .preload_data(pd), .core_start(core_start), .core_token(core_token), .core_epoch(core_epoch),
        .embed_code_re(embed_code_re), .embed_code_addr(embed_code_addr), .embed_code_q(embed_code_q),
        .embed_scale_re(embed_scale_re), .embed_scale_addr(embed_scale_addr), .embed_scale_q(embed_scale_q), .fault(sf));
    assign fault = ff | sf;
endmodule
