`timescale 1ns/1ps
// Actual mapped provider boundary witness. C_RX events are supplied at the
// explicit model boundary (checked decoder outputs); this does not qualify FACE
// transport. The proposed R=P+63 prefix must fail before any row can arrive.
module tb_mu_cold_provider;
 reg ck=0,rst_n=0;always #0.5 ck=~ck;
 reg word_v=0,word_scale=0,fill_begin=0,core_start=0,re=0;
 reg[511:0] data=0;reg[5:0] wi=0;reg[23:0] addr=0;
 wire[511:0] q;wire[15:0] sq;wire fault;
 qfd_embedding_word_provider dut(.ck(ck),.rst_n(rst_n),.word_v(word_v),.word_data(data),.word_token(18'd777),.word_index(wi),.word_scale(word_scale),.word_epoch(16'hbeef),
 .expected_word_slot(word_v),.expected_token(18'd777),.expected_word(wi),.expected_scale(word_scale),.expected_epoch(16'hbeef),
 .fill_begin(fill_begin),.fill_token(18'd777),.fill_epoch(16'hbeef),.core_start(core_start),.core_token(18'd777),.core_epoch(16'hbeef),
 .embed_code_re(re),.embed_code_addr(addr),.embed_code_q(q),.embed_scale_re(1'b0),.embed_scale_addr(18'd777),.embed_scale_q(sq),.fault(fault));
 integer c,R,P=1000,w,mode=0,complete_at=-1,first_fault=-1;
 function automatic[511:0] row(input integer i);row={16{32'hcafeb000+32'(i)}};endfunction
 initial begin
 w=$value$plusargs("MODE=%d",mode);
 // Mode0 reproduces the proposed head reference. Mode1 has a deliberately early
 // prefetch, proving the provider itself works when data precedes core_start.
 R=mode==0?P+63:P-300;
 repeat(4)@(negedge ck);rst_n=1;
 for(c=0;c<P+500;c++)begin
 @(negedge ck);word_v=0;fill_begin=0;core_start=0;re=0;
 if(c==R+204)fill_begin=1;
 if(c==R+209)begin word_v=1;word_scale=1;wi=0;data=16'h3f80;end
 if(c>=R+210&&c<R+274)begin word_v=1;word_scale=0;wi=6'(c-(R+210));data=row(c-(R+210));end
 // Actual core_start samples the already-registered GI output on the next edge.
 if(c==P+64)core_start=1;
 if(mode==1&&c>=P+70&&c<P+134)begin re=1;addr={18'd777,6'(c-(P+70))};end
 @(posedge ck);#0.1;
 if(complete_at<0&&dut.store.complete)complete_at=c;
 if(first_fault<0&&fault)first_fault=c;
 if(mode==1&&c>=P+70&&c<P+134&&q!==row(c-(P+70)))begin $fatal(1,"COLD_PROVIDER_FAIL readback c=%0d",c);end
 end
 if(mode==0&&first_fault==P+64&&complete_at>P+64)
  $display("COLD_PROVIDER_LATE_PREFIX_DETECTED raw_INIT=%0d raw_GI_emb_pin=%0d provider_core_sample=%0d head_reference=%0d provider_complete=%0d first_fault=%0d",P,P+63,P+64,R,complete_at,first_fault);
 else if(mode==1&&first_fault<0&&complete_at<P+64)
  $display("COLD_PROVIDER_EARLY_PREFETCH_PASS raw_INIT=%0d core_sample=%0d head_reference=%0d provider_complete=%0d compared=64",P,P+64,R,complete_at);
 else $fatal(1,"COLD_PROVIDER_FAIL mode=%0d complete=%0d first_fault=%0d",mode,complete_at,first_fault);
 $finish;
 end
endmodule
