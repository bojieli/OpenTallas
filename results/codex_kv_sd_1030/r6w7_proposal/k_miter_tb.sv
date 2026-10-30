`timescale 1ps/1ps
module test #(parameter integer INPUT_CASE=1,PHASE=0)(output reg done=0);
reg clk=0,fclk=0;always begin #416 clk=1;#417 clk=0;end
initial begin #(PHASE);forever begin #416 fclk=1;#417 fclk=0;end end
reg tr=0,rr=0;reg [7:0] d=0;integer wc=0,rc=0,epoch=0;
always @(posedge fclk)begin wc<=wc+1;d<=d+1;end
always @(posedge clk)rc<=rc+1;
wire trn,rrn;wire[7:0]q0,q1,qm;wire r0,r1,rm,f0,f1,fm;
reg[6:0]tp=0;reg[5:0]rp=0;
always @(posedge fclk)if(!tr)tp<=0;else tp<={tp[5:0],tr};
always @(posedge clk)if(!rr)rp<=0;else rp<={rp[4:0],rr};
assign trn=INPUT_CASE?tr:tp[6];assign rrn=INPUT_CASE?rp[5]:rr;
localparam integer K0=INPUT_CASE?32:35,K1=INPUT_CASE?26:42;
ot_dp_clk_landing_cas #(.W(8),.DEPTH(4)) gold(fclk,tr,clk,rr,6'(K0),d,q0,r0,f0);
ot_dp_clk_landing_cas #(.W(8),.DEPTH(4)) cand(fclk,trn,clk,rrn,6'(K1),d,q1,r1,f1);
ot_dp_clk_landing_cas #(.W(8),.DEPTH(4)) mutant(fclk,trn,clk,rrn,6'(K0),d,qm,rm,fm);
integer samples=0,bad=0,mut=0,first0=-1,first1=-1;
always @(negedge clk)begin
 if(r0&&r1)begin samples=samples+1;if(q0!==q1||f0||f1)bad=bad+1;end
 if(r0&&(fm||(rm&&qm!==q0)))mut=mut+1;
 if(r0&&first0<0)first0=rc;
 if(r1&&first1<0)first1=rc;
end
initial begin
 repeat(2)begin
  tr=0;rr=0;repeat(20)@(negedge clk);
  if(INPUT_CASE)begin tr=1;repeat(34)@(negedge clk);rr=1;end
  else begin rr=1;repeat(33)@(negedge clk);tr=1;end
  repeat(250)@(negedge clk);
 end
 if(samples<300||bad||!mut)$fatal(1,"CASE%0d PH%0d samples%0d bad%0d mut%0d fault%0b%0b",INPUT_CASE,PHASE,samples,bad,mut,f0,f1);
 $display("PASS CASE%0d PH%0d samples%0d bad%0d mutant%0d firstready%0d/%0d",INPUT_CASE,PHASE,samples,bad,mut,first0,first1);done=1;
end
endmodule
module tb;
wire[7:0]done;
genvar i;generate for(i=0;i<4;i=i+1)begin
test #(.INPUT_CASE(1),.PHASE(i*100)) a(done[i*2]);
test #(.INPUT_CASE(0),.PHASE(i*100)) b(done[i*2+1]);
end endgenerate
initial begin wait(&done);$finish;end
initial begin #1000000;$fatal(1,"timeout");end
endmodule
