`timescale 1ns/1ps
module tb;
 reg ck=0; always #0.4165 ck=~ck;
 reg rst_n=0;
 reg [7:0] re=0,vm_we=0;
 reg [191:0] addr=0,vm_waddr=0;
 reg [255:0] vm_wdata=0;
 reg w16_we=0,w1_we=0; reg [23:0] w16_addr=0,w1_addr=0;
 reg [511:0] w16_data=0; reg [31:0] w1_data=0;
 wire [255:0] q0,q1; wire f0,f1;
 qfd_dv_s8x_vmr #(.MIF(0)) a(.*,.q(q0),.fault(f0));
 qfd_dv_s8x_vmr #(.MIF(1)) b(.*,.q(q1),.fault(f1));
 reg [255:0] pq0; reg [1:0] pwe; reg [9:0] pr0,pr1;
 reg [255:0] pd0,pd1; reg [7:0] pm0,pm1;
 integer c=0,l,checks=0,qmut=0,wmut=0,reads=0;
 always @(posedge ck) begin
  #0.001;
  if(c>20) begin
   if(q1!==pq0) $fatal(1,"READ_DELAY c=%0d q1=%h priorq0=%h",c,q1,pq0);
   if({b.mwe[1],b.mwe[0]}!==pwe) $fatal(1,"WRITE_DELAY c=%0d",c);
   if(pwe[0] && {b.mrow[0],b.mwd[0],b.mms[0]}!=={pr0,pd0,pm0}) $fatal(1,"WRITE_PAYLOAD0 c=%0d",c);
   if(pwe[1] && {b.mrow[1],b.mwd[1],b.mms[1]}!=={pr1,pd1,pm1}) $fatal(1,"WRITE_PAYLOAD1 c=%0d",c);
   if(q1!==q0) qmut=qmut+1;
   if({b.mwe[1],b.mwe[0]}!=={a.mwe[1],a.mwe[0]}) wmut=wmut+1;
   if(q1!=0) reads=reads+1;
   checks=checks+1;
   if(f0 || f1) $fatal(1,"FAULT c=%0d f=%b%b",c,f0,f1);
  end
  pq0=q0; pwe={a.mwe[1],a.mwe[0]}; pr0=a.mrow[0];pr1=a.mrow[1];
  pd0=a.mwd[0];pd1=a.mwd[1];pm0=a.mms[0];pm1=a.mms[1];
  c=c+1;
 end
 task step; @(negedge ck); endtask
 initial begin
  repeat(8) step();rst_n=1;repeat(8) step();
  // Initialise both complete banks, then exercise vector/scalar writes and collision order.
  for(integer n=0;n<8;n=n+1) begin
   w16_we=1;w16_addr=n*16;
   for(integer k=0;k<16;k=k+1) w16_data[k*32+:32]=32'h3f800000+n*16+k;
   step();w16_we=0;repeat(8) step();
  end
  for(integer n=0;n<160;n=n+1) begin
   re=8'hff;
   for(integer k=0;k<8;k=k+1) addr[k*24+:24]=(n%8)*16+(n%2)*8+k;
   vm_we=0;w1_we=0;
   if(n%7==0) begin
    vm_we=8'hff;
    for(integer k=0;k<8;k=k+1) begin vm_waddr[k*24+:24]=(n%8)*16+(n%2)*8+k;vm_wdata[k*32+:32]=32'h40000000+n*8+k;end
   end else if(n%7==3) begin w1_we=1;w1_addr=(n%8)*16+(n%16);w1_data=32'h41000000+n;end
   step();
  end
  re=0;vm_we=0;w1_we=0;repeat(24) step();
  if(checks<200 || qmut<10 || wmut<10 || reads<50) $fatal(1,"INSUFFICIENT checks=%0d qmut=%0d wmut=%0d reads=%0d",checks,qmut,wmut,reads);
  $display("VMR_PROFILE_PASS checks=%0d read_delay=1 write_delay=1 q_sameedge_mutant=%0d write_sameedge_mutant=%0d readbacks=%0d",checks,qmut,wmut,reads);$finish;
 end
endmodule
