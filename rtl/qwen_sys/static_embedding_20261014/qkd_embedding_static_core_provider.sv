`timescale 1ns/1ps
// Actual retained HBM-return beat -> word join -> registered epoch face ->
// mapped native core code/scale ports. Every expected slot comes from the
// compiler calendar. No fault, valid, ready or credit can move production work.
module qkd_embedding_static_core_provider(
 input wire ck,rst_n,
 input wire beat_slot,beat_v,input wire [255:0] beat_data,
 input wire [17:0] beat_token,input wire [5:0] beat_word,
 input wire beat_half,beat_scale,input wire [15:0] beat_epoch,
 input wire fill_begin,input wire [17:0] fill_token,input wire [15:0] fill_epoch,
 input wire expected_word_slot,input wire [17:0] expected_token,
 input wire [5:0] expected_word,input wire expected_scale,input wire [15:0] expected_epoch,
 input wire core_start,input wire [17:0] core_token,input wire [15:0] core_epoch,
 input wire embed_code_re,input wire [23:0] embed_code_addr,output wire [511:0] embed_code_q,
 input wire embed_scale_re,input wire [17:0] embed_scale_addr,output wire [15:0] embed_scale_q,
 output wire fault
);
 wire wv,ws,jf;wire [511:0] wd;wire [17:0] wt;wire [5:0] wi;wire [15:0] we;
 qkd_embedding_static_join joiner(.ck(ck),.rst_n(rst_n),.beat_slot(beat_slot),.beat_v(beat_v),.beat_data(beat_data),
 .beat_token(beat_token),.beat_word(beat_word),.beat_half(beat_half),.beat_scale(beat_scale),.beat_epoch(beat_epoch),
 .word_v(wv),.word_data(wd),.word_token(wt),.word_index(wi),.word_scale(ws),.word_epoch(we),.fault(jf));
 wire fb,slot,pv,ps,ff,sf;wire [17:0] ft,pt;wire [15:0] fe,pe;wire [5:0] pw;wire [511:0] pd;
 qkd_embedding_static_preload_face face(.ck(ck),.rst_n(rst_n),.word_v(wv),.word_data(wd),.word_token(wt),.word_index(wi),
 .word_scale(ws),.word_epoch(we),.expected_slot(expected_word_slot),.expected_token(expected_token),.expected_word(expected_word),
 .expected_scale(expected_scale),.expected_epoch(expected_epoch),.i_fill_begin(fill_begin),.i_fill_token(fill_token),.i_fill_epoch(fill_epoch),
 .fill_begin(fb),.fill_token(ft),.fill_epoch(fe),.preload_slot(slot),.preload_v(pv),.preload_scale(ps),.preload_word(pw),
 .preload_token(pt),.preload_epoch(pe),.preload_data(pd),.fault(ff));
 qkd_embedding_static_core_store store(.ck(ck),.rst_n(rst_n),.fill_begin(fb),.fill_token(ft),.fill_epoch(fe),
 .preload_slot(slot),.preload_v(pv),.preload_scale(ps),.preload_word(pw),.preload_token(pt),.preload_epoch(pe),.preload_data(pd),
 .core_start(core_start),.core_token(core_token),.core_epoch(core_epoch),.embed_code_re(embed_code_re),.embed_code_addr(embed_code_addr),
 .embed_code_q(embed_code_q),.embed_scale_re(embed_scale_re),.embed_scale_addr(embed_scale_addr),.embed_scale_q(embed_scale_q),.fault(sf));
 assign fault=jf|ff|sf;
endmodule
