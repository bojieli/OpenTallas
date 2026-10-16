`timescale 1ns/1ps
module tb_su_multirate;
 parameter integer MUT_SLOT=0;
 reg serial_clk=0,stream_clk=0,rst_n=0;
 integer phase_mut=0,return_mut=0;
 initial begin phase_mut=$test$plusargs("MUT_PHASE");return_mut=$test$plusargs("MUT_RETURN"); #7;rst_n=1;end
 // q=2ns in simulation; production q=2500/9ps. Coincident epoch t=12ns.
 initial begin #12; forever begin stream_clk=1;#3;stream_clk=0;#3;end end
 initial begin #12; if(phase_mut)#2; forever begin serial_clk=1;#4;serial_clk=0;#4;end end
 localparam integer N=128;
 function automatic [16:0] rq(input integer n);
  rq=(n>=0&&n<N&&n%5!=1) ? {1'b1,16'(n^16'h4567)} : 17'b0;
 endfunction
 function automatic [280:0] wq(input integer n);
  reg [255:0] d;
  begin
   for(integer k=0;k<8;k=k+1)d[k*32+:32]=32'(n*19+k);
   wq=(n>=0&&n<N&&n%7!=2) ? {1'b1,16'(n+1234),d,8'hff} : 281'b0;
  end
 endfunction
 function automatic [256:0] answer(input [16:0] r);
  reg [255:0] d;
  begin
   for(integer k=0;k<8;k=k+1)d[k*32+:32]={16'(k),r[15:0]};
   answer=r[16]?{1'b1,d}:257'b0;
  end
 endfunction
 function automatic integer serial_of_j(input integer j);
  if(j<2 || j%4==1)serial_of_j=-1;
  else if(j%4==0)serial_of_j=3*(j/4)-1;
  else serial_of_j=3*(j/4)+j%4-2;
 endfunction
 reg[16:0] serial_rq=17'h14567;
 reg[280:0] serial_wq;
 initial serial_wq=wq(0);
 wire[256:0] serial_rr;wire serial_done;wire[16:0] stream_rq;wire[280:0]stream_wq;wire fault;
 reg[256:0] rp[0:10];reg wp[0:7];
 wire[256:0] stream_rr=return_mut ? rp[9] : rp[10];wire stream_done=wp[7];
 ot_hbm_su_multirate_bridge #(.MUT_SLOT(MUT_SLOT)) dut(
  .serial_clk(serial_clk),.stream_clk(stream_clk),.rst_n(rst_n),
  .serial_rq(serial_rq),.serial_wq(serial_wq),.serial_rr(serial_rr),.serial_done(serial_done),
  .stream_rq(stream_rq),.stream_wq(stream_wq),.stream_rr(stream_rr),.stream_done(stream_done),.fault(fault));
 integer sn=0,pn=0,reads=0,writes=0;
 initial begin for(integer k=0;k<=10;k=k+1)rp[k]=0;for(integer k=0;k<=7;k=k+1)wp[k]=0;end
 always @(posedge stream_clk)if(rst_n)begin
  integer n;
  n=serial_of_j(pn-1);
  if(stream_rq!==rq(n) || stream_wq!==wq(n))$fatal(1,"SU_MULTIRATE FAIL streamslot p=%0d n=%0d got=%h want=%h",pn,n,stream_rq,rq(n));
  if(stream_rq[16])reads=reads+1;
  if(stream_wq[280])writes=writes+1;
  rp[0]<=answer(stream_rq);for(integer k=1;k<=10;k=k+1)rp[k]<=rp[k-1];
  wp[0]<=stream_wq[280];for(integer k=1;k<=7;k=k+1)wp[k]<=wp[k-1];
  pn=pn+1;
 end
 always @(negedge serial_clk)begin serial_rq=rq(sn);serial_wq=wq(sn);end
 always @(posedge serial_clk)if(rst_n)begin
  integer e;
  e=sn;
  if(($time-12)%8!=0)$fatal(1,"SU_MULTIRATE FAIL clockphase serialtime=%0t",$time);
  #1;
  if(serial_rr!==answer(rq(e-12)) || serial_done!==((e-10>=0)&&(e-10<N)&&((e-10)%7!=2)) || fault)
   $fatal(1,"SU_MULTIRATE FAIL serialedge=%0d rr=%h want=%h done=%b fault=%b",e,serial_rr,answer(rq(e-12)),serial_done,fault);
  sn=sn+1;
  if(sn==N+20)begin
   $display("SU_MULTIRATE PASS serial=%0d stream=%0d reads=%0d writes=%0d readlat=12 acklat=10",sn,pn,reads,writes);$finish;
  end
 end
endmodule
