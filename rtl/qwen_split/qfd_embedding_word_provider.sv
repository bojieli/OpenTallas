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
    wire fb, slot, pv, ps, ff, sf;
    wire [17:0] ft, pt; wire [15:0] fe, pe; wire [5:0] pw; wire [511:0] pd;
    qkd_embedding_static_preload_face face (.ck(ck), .rst_n(rst_n), .word_v(word_v), .word_data(word_data),
        .word_token(word_token), .word_index(word_index), .word_scale(word_scale), .word_epoch(word_epoch),
        .expected_slot(expected_word_slot), .expected_token(expected_token), .expected_word(expected_word),
        .expected_scale(expected_scale), .expected_epoch(expected_epoch), .i_fill_begin(fill_begin), .i_fill_token(fill_token),
        .i_fill_epoch(fill_epoch), .fill_begin(fb), .fill_token(ft), .fill_epoch(fe), .preload_slot(slot), .preload_v(pv),
        .preload_scale(ps), .preload_word(pw), .preload_token(pt), .preload_epoch(pe), .preload_data(pd), .fault(ff));
    qkd_embedding_static_core_store store (.ck(ck), .rst_n(rst_n), .fill_begin(fb), .fill_token(ft), .fill_epoch(fe),
        .preload_slot(slot), .preload_v(pv), .preload_scale(ps), .preload_word(pw), .preload_token(pt), .preload_epoch(pe),
        .preload_data(pd), .core_start(core_start), .core_token(core_token), .core_epoch(core_epoch),
        .embed_code_re(embed_code_re), .embed_code_addr(embed_code_addr), .embed_code_q(embed_code_q),
        .embed_scale_re(embed_scale_re), .embed_scale_addr(embed_scale_addr), .embed_scale_q(embed_scale_q), .fault(sf));
    assign fault = ff | sf;
endmodule
