`timescale 1ns/1ps
module tb;
localparam integer W=515, NC=9;
real PH=0.29;
reg clk=0,fclk=0,rst=0;reg[W-1:0] d=0;
always #0.4165 clk=~clk;
initial begin if(!$value$plusargs("PH=%f",PH))PH=0.29;#PH;forever #0.4165 fclk=~fclk;end
always @(posedge fclk)begin d[511:0]<={16{$urandom}};d[514:512]<=3'($urandom);end
wire[W-1:0]qr,qn;wire rr,rn,fr,fn;
cl_ref #(.W(W),.WNEG(1))R(.fclk(fclk),.clk(clk),.rst_n(rst),.d(d),.q(qr),.ready(rr),.fault(fr));
cl_new #(.W(W),.WNEG(1))N(.fclk(fclk),.clk(clk),.rst_n(rst),.d(d),.q(qn),.ready(rn),.fault(fn));
integer checks=0,errors=0,epochs=0,ep;
always @(posedge clk)begin #0.001;
 if(rst)begin
  if(rn!==rr||fn!==fr)begin errors++;if(errors<5)$display("BAD controls t=%0t",$time);end
  if(N.ring_on_v!=={NC{R.on}}||N.ring_align_v!=={NC{R.align}})begin errors++;if(errors<5)$display("BAD local copies t=%0t",$time);end
  if(rn&&rr)begin checks++;if(qn!==qr)begin errors++;if(errors<5)$display("BAD payload t=%0t",$time);end end
 end
end
initial begin
 for(ep=0;ep<5;ep++)begin
  rst=0;repeat(10+ep)@(negedge clk);rst=1;
  repeat(600)@(negedge clk);if(rr)epochs++;
 end
 $display("CLON_RESULT W=%0d WNEG=1 PH=%0.3f checks=%0d errors=%0d epochs=%0d fault_ref=%b",W,PH,checks,errors,epochs,fr);
 if(errors||checks<2500||epochs!=5||fr)$fatal(1,"CLON lockstep FAIL");
 $display("CLON lockstep PASS");$finish;
end
endmodule
