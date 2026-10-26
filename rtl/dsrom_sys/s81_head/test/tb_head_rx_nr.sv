`timescale 1ns/1ps
module tb_head_rx_nr;
 reg ck=0;always #5 ck=~ck;reg rn=0,we=0,aa=0,ab=0;reg[3:0]wa=0,ra=0;reg[127:0]wd=0;
 wire[127:0]q,nq,mq;
 ot_sram_showahead_1r1w #(.W(128),.AW(4),.LOCAL_HIT(1),.SB(8),.LOCAL_RA(1),.LOCAL_WA(1),.DEPTH(12))gold(.clk(ck),.rst_n({16{rn}}),.we(we),.wa(wa),.wd(wd),.ra(ra),.q(q),.advance_a(aa),.advance_b(ab));
 ot_sram_showahead_1r1w_head_nr #(.W(128),.AW(4),.LOCAL_HIT(1),.SB(8),.LOCAL_RA(1),.LOCAL_WA(1),.DEPTH(12))nr(.clk(ck),.rst_n({16{rn}}),.we(we),.wa(wa),.wd(wd),.ra(ra),.q(nq),.advance_a(aa),.advance_b(ab));
 ot_sram_showahead_1r1w_head_nr #(.W(128),.AW(4),.LOCAL_HIT(1),.SB(8),.LOCAL_RA(1),.LOCAL_WA(1),.DEPTH(12),.MUT(1))mut(.clk(ck),.rst_n({16{rn}}),.we(we),.wa(wa),.wd(wd),.ra(ra),.q(mq),.advance_a(aa),.advance_b(ab));
 integer checks=0,mutants=0;
 always @(posedge ck)begin #1;
  if(rn)begin
   if(q!==nq)$fatal(1,"NR RX data/cycle mismatch%0d",checks);
   if(mq!==nq)mutants=mutants+1;checks=checks+1;
  end
 end
 initial begin
  repeat(4)@(negedge ck);rn=1;
  for(integer i=0;i<2048;i=i+1)begin
   if(i<32)begin we=1;wa=0;aa=0;ab=0;end
   else begin we=(i%5!=0);wa=4'((i/3)%12);aa=(i%5==0);ab=(i%7==0);end
   wd={$urandom,$urandom,$urandom,$urandom};@(negedge ck);
  end
  we=0;repeat(4)@(negedge ck);
  if(mutants==0)$fatal(1,"current-forward mutant escaped");
  $display("HEAD_RX_NR PASS cycles=%0d depth12 wrap checked forwarding_mutant=%0d extra_cycles=0",checks,mutants);$finish;
 end
endmodule
