`timescale 1ns/1ps
// RTL KV FP8 finish: the head's actual fp8r / fp8r_pre / fp8r_fin functions (verbatim from qfd_dv_lane_h_su_mem9.sv)
module tb;
`include "funcs.sv"
 integer fd,od,rc;reg[31:0]v,a,b,c;integer n=0,bad=0;
 initial begin
  fd=$fopen("vec.hex","r");od=$fopen("rtl_out.hex","w");
  while(!$feof(fd))begin rc=$fscanf(fd,"%h\n",v);if(rc==1)begin a=fp8r(v);b=fp8r_fin(fp8r_pre(v));$fwrite(od,"%08x %08x\n",a,b);n=n+1;if(a!==b)bad=bad+1;end end
  $display("FP8R_DONE n=%0d pre_fin_vs_fp8r_mismatch=%0d",n,bad);$finish;
 end
endmodule
