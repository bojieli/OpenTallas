`timescale 1ns/1ps
// CONTRACT TEST ONLY: numerical producer is a deterministic 186-edge stub.
// Tests finite capture/transpose/order/identity; NOT numerical SwiGLU exactness.
module ot_dsrom_su_swiglu #(parameter W=64,ROUTED=1,NIN=33,NOUT=23,LM=5,LA=4,QLAT=5)(
 input clk,rst_n,v,input [2047:0] g,u,w,input [31:0] lim,
 output vo,output [511:0] q,output [19:0] e,output [1023:0] y,output fault);
 reg [185:0] valid=0;reg [531:0] d[0:185];integer i;
 always @(posedge clk)begin
  if(!rst_n)valid<=0;else valid<={valid[184:0],v};
  d[0]<={w[19:10],u[255:0],w[9:0],g[255:0]};
  for(i=1;i<186;i=i+1)d[i]<=d[i-1];
 end
 assign vo=valid[185];assign q={d[185][521:266],d[185][255:0]};
 assign e={d[185][531:522],d[185][265:256]};assign y=0;assign fault=0;
endmodule
module tb;
 reg clk=0;always #0.5 clk=~clk;
 reg rst_n=0,start=0,permit=1;reg [72:0] frame=73'h712345;
 wire [6:0] ix,xa,xg;wire [4:0] fx;wire [2047:0] xd;
 wire xe,done,fault;integer writes=0,admitted=0,cyc=0,admission_cycle=-1,done_cycle=-1;
 wire [2047:0] g=2048'(2*ix),u=2048'(2*ix+1);
 wire [2047:0] w={2028'd0,10'(2*ix+1),10'(2*ix)};
 ot_hubble_swiglu_w2_capture #(.ENABLE(1)) dut(clk,rst_n,start,permit,frame,32'd0,32'd1,
  g,u,w,32'h41200000,{944{1'b1}},ix,fx,xe,xa,xg,xd,done,fault);
 wire offxe,offdone,offfault;wire [6:0] offix,offxa,offxg;wire [4:0] offfx;wire [2047:0] offxd;
 ot_hubble_swiglu_w2_capture disabled(clk,rst_n,start,permit,frame,32'd0,32'd1,
  g,u,w,32'h41200000,{944{1'b1}},offix,offfx,offxe,offxa,offxg,offxd,offdone,offfault);
 function automatic [4095:0] want(input integer f);
  integer j,b;reg [4095:0] z;
  begin z={{944{1'b1}},3152'd0};
   for(j=0;j<8;j=j+1)begin
    b=(((f%16)/8)*8+j)*8+f%8;
    if(b<72)z[266*j+:266]={10'((f/16)*72+b),256'((f/16)*72+b)};
   end want=z;end
 endfunction
 reg [4095:0] expected;
 always @(posedge clk)if(rst_n)begin
  cyc=cyc+1;
  if(start)admission_cycle=cyc;
  if(dut.g_on.pv)admitted=admitted+1;
  if(offxe||offdone||offfault||offxd!==0)$fatal(1,"default off not inert");
  if(xe)begin
   if(fault||xa!=writes/2||xg!=writes%2||fx!=writes/2)$fatal(1,"xwrite order/identity");
   expected=want(writes/2);
   if(xd!==expected[(writes%2)*2048+:2048])$fatal(1,"packet transpose/padding mismatch %0d",writes);
   writes=writes+1;
  end
 end
 initial begin
  repeat(3)@(negedge clk);rst_n=1;@(negedge clk);start=1;@(negedge clk);start=0;
  wait(done);@(negedge clk);done_cycle=cyc;
  if(fault||writes!=64||admitted!=72||dut.g_on.captured!=72||dut.g_on.seen!={72{1'b1}})
   $fatal(1,"finite mechanism counts");
  $display("CAPTURE_CONTROL_SMOKE_PASS packets=144 inputs=72 capture_words=72 xwrites=64 admission_to_done=%0d",done_cycle-admission_cycle);
  // Reset then change current owner during drain: sticky rejection, no writes.
  rst_n=0;@(negedge clk);rst_n=1;writes=0;admitted=0;@(negedge clk);start=1;@(negedge clk);start=0;
  repeat(80)@(negedge clk);frame=frame+1;repeat(3)@(negedge clk);
  if(!fault||xe||done||writes!=0)$fatal(1,"changed owner not rejected");
  $display("OWNER_REJECTION_AND_DEFAULT_OFF_PASS");$finish;
 end
 // Capacity-derived bound for this tiny deterministic test, not a job deadline.
 initial begin repeat(500)@(negedge clk);$fatal(1,"contract smoke failed to complete expected fixed calendar");end
endmodule
