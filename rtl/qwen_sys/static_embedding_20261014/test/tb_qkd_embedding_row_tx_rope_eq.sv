`timescale 1ns/1ps
module tb_qkd_embedding_row_tx_rope_eq;
 reg ck=0,rst_n=0; always #0.5 ck=~ck;
 reg fb=0,wv=0,ws=0,slot=0; reg [17:0] ft=0,wt=0; reg [15:0] fe=0,we=0; reg [12:0] fp=0; reg [511:0] wd=0; reg [5:0] wi=0;
 wire v0,v1,f0,f1,r0,r1,o0,o1; wire [547:0] p0,p1;
 qkd_embedding_row_tx_rope n(.ck(ck),.rst_n(rst_n),.fill_begin(fb),.fill_token(ft),.fill_epoch(fe),.fill_position(fp),.word_v(wv),.word_data(wd),.word_token(wt),.word_index(wi),.word_scale(ws),.word_epoch(we),.emb_tx_slot(slot),.emb_tx_v(v0),.emb_tx_payload(p0),.fault(f0),.row_ready(r0),.row_open(o0));
 qkd_embedding_row_tx_rope_old o(.ck(ck),.rst_n(rst_n),.fill_begin(fb),.fill_token(ft),.fill_epoch(fe),.fill_position(fp),.word_v(wv),.word_data(wd),.word_token(wt),.word_index(wi),.word_scale(ws),.word_epoch(we),.emb_tx_slot(slot),.emb_tx_v(v1),.emb_tx_payload(p1),.fault(f1),.row_ready(r1),.row_open(o1));
 integer i,err=0,seed=7,sent=0,ropeb=0,ready=0,k,t; reg [17:0] tok; reg [15:0] ep; reg [12:0] pos;
 always @(negedge ck) if(rst_n) begin if({v0,p0,f0,r0,o0}!=={v1,p1,f1,r1,o1}) begin err=err+1; if(err<5)$display("DIFF %0t v%b/%b f%b/%b r%b/%b",$time,v0,v1,f0,f1,r0,r1); end
   if(v0) sent=sent+1; if(v0&&p0[512]) ropeb=ropeb+1; if(r0) ready=ready+1; end
 initial begin
  repeat(20)@(negedge ck); rst_n=1; repeat(20)@(negedge ck);
  for(t=0;t<40;t=t+1) begin
   tok=$random(seed)%151936; if(tok>=151936) tok=5; ep=$random(seed); pos=$random(seed);
   @(negedge ck); fb=1; ft=tok; fe=ep; fp=pos; @(negedge ck); fb=0; repeat(6)@(negedge ck);
   // 64 embedding words, scale, 8 rope words (correct, plus occasional garbage when t%7==3)
   for(k=0;k<64;k=k+1) begin @(negedge ck); wv=1; ws=0; wi=k; wt=tok; we=ep; wd={16{$random(seed)}}; if(t%7==3&&k==5) wt=wt^1; end
   @(negedge ck); wv=1; ws=1; wi=0; wd=$random(seed);
   for(k=0;k<8;k=k+1) begin @(negedge ck); wv=1; ws=0; wi={pos[2:0],3'(k)}; wt=18'd151936+{8'd0,pos[12:3]}; we=ep; wd={16{$random(seed)}}; end
   @(negedge ck); wv=0; repeat(8)@(negedge ck);
   for(k=0;k<80;k=k+1) begin @(negedge ck); slot=($random(seed)&3)!=0; end
   slot=0; repeat(10)@(negedge ck);
   if(t==20) begin rst_n=0; repeat(5)@(negedge ck); rst_n=1; repeat(20)@(negedge ck); end
  end
  for(i=0;i<3000;i=i+1) begin @(negedge ck); fb=($random(seed)&63)==0; wv=$random(seed); ws=$random(seed); slot=$random(seed); wi=$random(seed); wt=$random(seed); wd={16{$random(seed)}}; ft=$random(seed); fp=$random(seed); end
  $display("EQ %s err=%0d sent=%0d rope_beats=%0d ready=%0d", err==0?"PASS":"FAIL", err, sent, ropeb, ready); $finish;
 end
endmodule
