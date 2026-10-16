`timescale 1ns/1ps
module tb_host_boot300;
 parameter integer MUT=0;
 reg ck=0,ckv=0,rst=1;always #3 ck=~ck;
 integer phase=0,stop_boot=0,overload=0;
 initial begin
  if(!$value$plusargs("serial_phase=%d",phase))phase=0;
  if(!$value$plusargs("stop_boot=%d",stop_boot))stop_boot=0;
  if(!$value$plusargs("overload=%d",overload))overload=0;
  #(3+phase);ckv=1;forever begin #4 ckv=0;#4 ckv=1;end
 end
 reg[1:0]boot_div=1;always @(posedge ck)if(!stop_boot)boot_div<=boot_div+1'b1;
 wire ck_boot=stop_boot?1'b0:boot_div[1];
 reg[514:0]f=0;wire[76:0]t;wire[35:0]sp,pq;wire[7:0]plen;wire[291:0]hw;
 dsfd_host_c #(.MUT(MUT))dut(.ck(ck),.ckv(ckv),.ck_boot(ck_boot),.rst(rst),.rsv(rst),.ck_ingest({ck,ck}),
  .f_collective(f),.t_collective(t),.f_lf(4'b0101),.t_sseq_pw(sp),.t_pq_pw(pq),.t_sseq_plen(plen),.f_sseq_st(6'd0),.f_wfc_ft(4'd0),.hw(hw),.hc(9'd0));
 integer cyc=0,sent=0,got=0,expected_type;reg[34:0]exp[0:95];reg[95:0]types;
 initial begin
  for(integer i=0;i<96;i=i+1)begin exp[i]={7'(i),28'(32'hcae5+i*337)};types[i]=i%3==1;end
  #1 rst=0;#59 rst=1;
 end
 always @(negedge ck)if(rst)begin:tx
  reg[511:0]word;
  cyc=cyc+1;f<=0;
  if(cyc==100)begin word=0;word[7:0]=8'h11;word[39:32]=96;f<={2'd0,word,1'b1};end
  if(cyc>120&&sent<96&&(overload||cyc%12==0))begin
   word=0;word[7:0]=types[sent]?8'h12:8'h10;word[102:96]=exp[sent][34:28];word[59:32]=exp[sent][27:0];f<={2'd0,word,1'b1};sent=sent+1;
  end
  if(cyc==1600)begin
   if(stop_boot||overload)begin
    if(!t[75])$fatal(1,"BOOT300 FAIL missing clock/capacity fault");
    $display("BOOT300 FAIL_EXPECTED detected stop=%0d overload=%0d fault=%b words=%0d",stop_boot,overload,t[75],got);$finish;
   end
   if(sent!=96||got!=96||plen!=96||t[75])$fatal(1,"BOOT300 FAIL completion sent=%0d got=%0d plen=%0d fault=%b",sent,got,plen,t[75]);
   $display("BOOT300 PASS phase=%0d payload_identity=%0d length=%0d normal_clock_ratio=4:3 boot=1:4",phase,got,plen);$finish;
  end
 end
 always @(posedge ckv)if(rst&&(sp[35]||pq[35]))begin
  if(sp[35]&&pq[35])$fatal(1,"BOOT300 FAIL duplicate kind");
  if(got>=96||(pq[35]!==types[got])||(pq[35]?pq[34:0]:sp[34:0])!==exp[got])
   if(!(stop_boot||overload))$fatal(1,"BOOT300 FAIL payload/kind got=%0d actual=%h expected=%h",got,pq[35]?pq:sp,exp[got]);
  got=got+1;
 end
endmodule
