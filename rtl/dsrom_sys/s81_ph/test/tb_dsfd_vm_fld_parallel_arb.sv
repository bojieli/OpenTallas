`timescale 1ns/1ps
`include "dsfd_vm_fld_pick2.svh"
module fld_arb_probe(input wire[3:0] ptr,input wire[9:0] requests,
 output wire[9:0] take,output wire[1:0] valid,output wire[7:0] selected);
 localparam NLL=10;wire[3:0] ll_ptr=ptr;wire[6:0] lc[0:9];reg[9:0] ll_tk;reg[1:0] lsel_v;reg[3:0] lsel[0:1];
 generate for(genvar g=0;g<10;g=g+1)begin:gn assign lc[g]=requests[g]?7'd1:7'd0;end endgenerate
 `include "dsfd_vm_fld_parallel_arb.svh"
 assign take=ll_tk;assign valid=lsel_v;assign selected={lsel[1],lsel[0]};
endmodule
module tb_dsfd_vm_fld_parallel_arb;
 reg[3:0] ptr;reg[9:0] requests;wire[9:0] take;wire[1:0] valid;wire[7:0] selected;
 fld_arb_probe dut(ptr,requests,take,valid,selected);
 integer p,r,i,j,k;reg[9:0] expected_take;reg[1:0] expected_valid;reg[3:0] s0,s1;
 initial begin
  for(p=0;p<16;p=p+1)for(r=0;r<1024;r=r+1)begin
   ptr=p;requests=r;expected_take=0;expected_valid=0;s0=0;s1=0;k=0;
   for(i=0;i<10;i=i+1)begin j=(p+i)%10;
    if(requests[j]&&k<2&&!(j>=2&&j<6))begin expected_take[j]=1;expected_valid[k]=1;if(k==0)s0=j;else s1=j;k=k+1;end
   end
   for(i=0;i<4;i=i+1)begin j=2+i;
    if(requests[j]&&k<2)begin expected_take[j]=1;expected_valid[k]=1;if(k==0)s0=j;else s1=j;k=k+1;end
   end
   #1;
   if({take,valid,selected}!={expected_take,expected_valid,s1,s0})$fatal(1,"ARB_BAD ptr%0d req%h got%h/%b/%h expected%h/%b/%h",p,r,take,valid,selected,expected_take,expected_valid,{s1,s0});
  end
  if(p!=16 || r!=1024 || $time!=16384)$fatal(1,"ARB_INCOMPLETE p%0d r%0d elapsed%0t",p,r,$time);
  $display("ARB_PASS checks=16384 finalptr=%0d finalreq=%0d elapsed=%0t",p,r,$time);$finish;
 end
endmodule
