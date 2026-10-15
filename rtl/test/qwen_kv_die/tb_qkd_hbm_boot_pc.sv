`timescale 1ns/1ps
module tb_qkd_hbm_boot_pc;
 parameter MUT=0;
 reg ck=0;always #5 ck=~ck;
 reg rn=0,start=0;wire[287:0]es;reg[260:0]er=0;
 wire busy,done,ok;wire[3:0]cause;reg[255:0]mem=0;reg corrupt=0,stall=0,ue=0;
 integer nwrite=0,nread=0;
 qkd_hbm_boot_pc #(.TIMEOUT(32),.MUT(MUT))dut(.ck(ck),.rst_n(rn),.start(start),.bank(5'd3),.col(5'd2),.row(19'd0),.es(es),.er(er),.busy(busy),.done(done),.ok(ok),.cause(cause));
 // Ordered static endpoint contract; real qkd_ctrl_pc integration is separate.
 always @(posedge ck)begin
  er<=0;
  if(es[0]&&!stall)begin
   if(es[285:276]!={5'd3,5'd2}||es[275:257]!=0)$fatal(1,"address differs");
   er[259]<=1;
   if(es[286])begin mem<=es[256:1];nwrite<=nwrite+1;end
   else begin er[0]<=1;er[256:1]<=mem^(corrupt?256'b1:256'b0);er[258]<=ue;nread<=nread+1;end
  end
 end
 task kick;
  @(negedge ck);start=1;@(negedge ck);start=0;
  wait(done);@(negedge ck);
 endtask
 initial begin
  repeat(3)@(negedge ck);rn=1;
  kick();if(!ok||nwrite!=2||nread!=2)$fatal(1,"good roundtrip rejected");
  corrupt=1;kick();if(ok||cause!=3)$fatal(1,"corrupt read accepted");
  corrupt=0;ue=1;kick();if(ok||cause!=3)$fatal(1,"UE accepted");
  ue=0;stall=1;kick();if(ok||cause!=2)$fatal(1,"stalled endpoint accepted");
  $display("PASS real read-dependent boot checker: good/corrupt/UE/stall");$finish;
 end
 initial begin #10000;$fatal(1,"watchdog");end
endmodule
