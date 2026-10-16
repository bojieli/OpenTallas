`timescale 1ns/1ps
module tb_hbm_su_static_pinned_bank;
 parameter integer MUT_COHERENCE=0,MUT_RETURN=0,MUT_RESET=0;
 reg halt_macro5=0,halt_rd=0;
 wire[5:0]clk_macro={clk&&!halt_macro5,{5{clk}}};
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0;reg[5:0]rv=0;reg[53:0]ra=0;
 wire[191:0]rd;wire[5:0]ret;
 reg wv=0;reg[8:0]wa=0;reg[31:0]wd=0;
 integer c,r,checks=0,errors=0;
 ot_hbm_su_static_bank6_clock_physical #(.MUT_COHERENCE(MUT_COHERENCE),.MUT_RETURN(MUT_RETURN),.MUT_RESET(MUT_RESET))d(
 .clk(clk),.clk_rd(clk&&!halt_rd),.clk_macro0(clk_macro[0]),.clk_macro1(clk_macro[1]),.clk_macro2(clk_macro[2]),.clk_macro3(clk_macro[3]),.clk_macro4(clk_macro[4]),.clk_macro5(clk_macro[5]),.rst_n(rst_n),.read_v(rv),.read_addr(ra),.read_data(rd),.read_return(ret),
 .write_v(wv),.write_addr(wa),.write_data(wd));
 function automatic[31:0]word(input integer row);word=32'h12340000+32'(row*31+1);endfunction
 initial begin
  repeat(3)@(negedge clk);rst_n=1;wv=1;
  for(c=0;c<512;c=c+1)begin wa=9'(c);wd=word(c);@(negedge clk);end
  wv=0;@(posedge clk);#1;@(negedge clk);
  for(c=0;c<514;c=c+1)begin
   halt_macro5=$test$plusargs("MUT_CLOCK_HALT")&&(c>=64&&c<80);
   halt_rd=$test$plusargs("MUT_RD_HALT")&&(c>=96&&c<100);   // r7 read-face root must be live
   rv=c<512?6'h3f:0;
   for(r=0;r<6;r=r+1)ra[r*9+:9]=9'((c+17*r)%512);
   @(posedge clk);#1;
   checks=checks+1;if(ret!==(c>=2?6'h3f:6'h00))errors=errors+1;
   if(c>=2)for(r=0;r<6;r=r+1)begin
    checks=checks+1;
    if(rd[r*32+:32]!==word((c-2+17*r)%512))begin
     if(errors<4)$display("ERR c=%0d replica=%0d data=%h",c,r,rd[r*32+:32]);errors=errors+1;
    end
   end
   @(negedge clk);
  end
  rv=6'h3f;wv=1;wa=511;wd=32'hdeadbeef;
  for(r=0;r<6;r=r+1)ra[r*9+:9]=511;
  @(posedge clk);#1;@(negedge clk);wv=0;
  @(posedge clk);#1;@(negedge clk);
  @(posedge clk);#1;
  for(r=0;r<6;r=r+1)begin checks=checks+1;if(rd[r*32+:32]!==word(511))errors=errors+1;end
  @(negedge clk);@(posedge clk);#1;
  for(r=0;r<6;r=r+1)begin checks=checks+1;if(rd[r*32+:32]!==32'hdeadbeef)errors=errors+1;end
  // r10 reset phase: commands issued while rst_n is low must neither return nor write (row 0 keeps word(0))
  // reset is entered from idle (PIN_RST: reads issued before the asserting edge still return for <= 2 edges)
  @(negedge clk);rv=0;wv=0;repeat(3)@(negedge clk);rst_n=0;
  for(c=0;c<4;c=c+1)begin
   rv=6'h3f;wv=1;wa=0;wd=32'hbad0bad0;for(r=0;r<6;r=r+1)ra[r*9+:9]=0;
   @(posedge clk);#1;checks=checks+1;if(ret!==6'h00)errors=errors+1;@(negedge clk);
  end
  rv=0;wv=0;rst_n=1;
  for(c=0;c<3;c=c+1)begin @(posedge clk);#1;checks=checks+1;if(ret!==6'h00)errors=errors+1;@(negedge clk);end
  rv=6'h3f;for(r=0;r<6;r=r+1)ra[r*9+:9]=0;@(negedge clk);rv=0;   // sampled at n, returned at n+2
  @(posedge clk);#1;checks=checks+1;if(ret!==6'h00)errors=errors+1;@(negedge clk);
  @(posedge clk);#1;
  checks=checks+1;if(ret!==6'h3f)errors=errors+1;
  for(r=0;r<6;r=r+1)begin checks=checks+1;
   if(rd[r*32+:32]!==word(0))begin if(errors<8)$display("ERR reset-write landed replica=%0d data=%h",r,rd[r*32+:32]);errors=errors+1;end
  end
  if(errors)$fatal(1,"SU_PINNED_BANK FAIL checks=%0d errors=%0d",checks,errors);
  $display("SU_PINNED_BANK PASS actual_SRAMs=6 independent_macro_ports=6 checks=%0d read_latency=2 write_commit_latency=1 II=1 coherence prewrite",checks);$finish;
 end
endmodule
