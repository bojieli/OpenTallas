`timescale 1ns/1ps
`ifndef MUT
`define MUT 0
`endif
module tb_rowctx_native32;
 reg ck=0;always #1 ck=~ck;
 reg rst_n=0,fb=0,wv=0,ws=0,slot=0;
 reg [17:0] ft=0,wt=0;reg [15:0] fe=0,we=0;reg [511:0] wd=0;reg [5:0] wi=0;
 // Exact generated wrapper from the immutable CLOSED c1b view: two reset
 // landing stages, every data input one stage and every output one stage.
 wire ov,ofault,oready,oopen;wire [547:0] opayload;
 qkd_embedding_row_tx_ctx_old_view old_body(.ck(ck),.rst_n(rst_n),.fill_begin(fb),.fill_token(ft),.fill_epoch(fe),
  .word_v(wv),.word_data(wd),.word_token(wt),.word_index(wi),.word_scale(ws),.word_epoch(we),
  .emb_tx_slot(slot),.emb_tx_v(ov),.emb_tx_payload(opayload),.fault(ofault),.row_ready(oready),.row_open(oopen));
 wire nv,nfault,nready,nopen;wire [547:0] npayload;
 qkd_embedding_row_tx_ctx_native32 #(.MUT(`MUT)) dut(.ck(ck),.rst_n(rst_n),.fill_begin(fb),.fill_token(ft),.fill_epoch(fe),
  .word_v(wv),.word_data(wd),.word_token(wt),.word_index(wi),.word_scale(ws),.word_epoch(we),
  .emb_tx_slot(slot),.emb_tx_v(nv),.emb_tx_payload(npayload),.fault(nfault),.row_ready(nready),.row_open(nopen));
 wire [551:0] old_view={ov,opayload,ofault,oready,oopen};
 wire [551:0] new_view={nv,npayload,nfault,nready,nopen};
 integer age=0,warm=0,checks=0,errors=0,beats=0,firstuse=0,reset_count=0;
 always @(negedge ck)begin
  age=age+1;
  if(!rst_n)warm=0;else warm=warm+1;
  if(age>20)begin
   checks=checks+1;
   if(old_view!==new_view)begin errors=errors+1;if(errors<7)$display("DIFF t=%0t old=%h new=%h",$time,old_view,new_view);end
   if(nv)beats=beats+1;
  end
 end
 function automatic [511:0] value(input integer token,input integer wordno);
  reg [511:0] d;begin for(integer j=0;j<16;j=j+1)d[j*32+:32]=32'(token*100003+wordno*997+j*37);value=d;end
 endfunction
 task automatic tick;begin @(negedge ck);#0.01;end endtask
 task automatic quiet;begin fb=0;wv=0;slot=0;ws=0;end endtask
 task automatic idle(input integer n);begin quiet();repeat(n)tick();end endtask
 task automatic reset;
  begin quiet();rst_n=0;repeat(5)tick();rst_n=1;repeat(20)tick();reset_count=reset_count+1;end
 endtask
 task automatic begin_row(input integer t,input integer e);
  begin quiet();ft=18'(t);fe=16'(e);fb=1;tick();fb=0;tick();end
 endtask
 task automatic word(input integer t,input integer e,input integer n,input bit sc);
  begin quiet();wt=18'(t);we=16'(e);wi=6'(n);wd=sc?512'h3f80:value(t,n);ws=sc;wv=1;tick();end
 endtask
 task automatic fill(input integer t,input integer e);
  begin begin_row(t,e);for(integer j=0;j<64;j=j+1)word(t,e,j,0);word(t,e,0,1);idle(8);end
 endtask
 task automatic send(input integer gaps);
  begin quiet();for(integer j=0;j<65;j=j+1)begin slot=1;tick();slot=0;if(gaps)repeat(j%gaps)tick();end idle(8);end
 endtask
 task automatic require_fault(input integer which);
  begin idle(8);if(!nfault)begin errors=errors+1;$display("NO_FAULT case=%0d",which);end end
 endtask
 initial begin
  reset();
  for(integer t=0;t<4;t=t+1)begin
   fill(100+t,17+t);send(t%3);
   if(nfault)begin errors=errors+1;$display("LEGAL_FAULT token=%0d",t);end
   firstuse=firstuse+1;
  end
  // Immediate first-use after full reset, independent new payload and identity.
  reset();fill(411,39);send(0);firstuse=firstuse+1;
  // Duplicate, foreign, missing residency, 66th slot, and overlapping fill.
  reset();begin_row(12,4);word(12,4,0,0);word(12,4,0,0);require_fault(1);
  reset();begin_row(13,5);word(14,5,0,0);require_fault(2);
  reset();begin_row(15,6);idle(4);slot=1;tick();require_fault(3);
  reset();fill(16,7);send(0);slot=1;tick();require_fault(4);
  reset();begin_row(17,8);begin_row(18,9);require_fault(5);
  // Mid-fill reset must erase all residency/armed state; the SRAM remains real.
  reset();begin_row(19,10);word(19,10,0,0);reset();fill(20,11);send(1);firstuse=firstuse+1;
  // Illegal simultaneous commands retain deterministic legacy state priority.
  reset();begin_row(21,12);word(21,12,3,0);fb=1;slot=1;wv=1;tick();require_fault(6);
  idle(12);
  if(checks<900||beats<390||firstuse!=6||reset_count<10)begin errors=errors+1;$display("COVERAGE_FAIL checks=%0d beats=%0d",checks,beats);end
  if(errors)$fatal(1,"FAIL ROWCTX_NATIVE32 mut=%0d checks=%0d errors=%0d",`MUT,checks,errors);
  $display("PASS ROWCTX_NATIVE32 mut=%0d checks=%0d beats=%0d firstuse=%0d resets=%0d",`MUT,checks,beats,firstuse,reset_count);$finish;
 end
endmodule
