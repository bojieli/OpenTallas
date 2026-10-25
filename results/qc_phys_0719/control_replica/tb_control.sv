`timescale 1ns/1ps
module replicated_control #(parameter integer MUT=0, parameter [15:0] MASK=16'hABBF)(
 input wire ck,input wire d, output wire [15:0] q, output wire c0,output wire c1);
 wire delayed_d;
 qfd_dv_s8x_kff #(.W(1),.ID(3399)) u_delay(.ck(ck),.d(d),.q(delayed_d));
 qfd_dv_s8x_kff #(.W(1),.ID(3400)) u_c1_w0(.ck(ck),.d(d),.q(c0));
 qfd_dv_s8x_kff #(.W(1),.ID(3400)) u_c1_w1(.ck(ck),.d(MUT==1 ? ~d : MUT==2 ? delayed_d : d),.q(c1));
 for(genvar gk=0;gk<16;gk=gk+1) begin:g_cbk
  qfd_dv_s8x_kff #(.W(1),.ID(3500+gk)) u(.ck(ck),.d(MASK[gk] ? c1 : c0),.q(q[gk]));
 end
endmodule
module tb_control;
 reg ck=0;always #5 ck=~ck;
 reg d=1;
 wire c1_bank;wire [15:0] ref_q;
 qfd_dv_s8x_kff #(.W(1),.ID(3400)) u_c1(.ck(ck),.d(d),.q(c1_bank));
 for(genvar gk=0;gk<16;gk=gk+1) begin:g_cbk
  qfd_dv_s8x_kff #(.W(1),.ID(3500+gk)) u(.ck(ck),.d(c1_bank),.q(ref_q[gk]));
 end
 wire [15:0] good_q[0:5];wire [1:0] good_c[0:5];
 replicated_control #(.MASK(16'hABBF)) u_actual(.ck(ck),.d(d),.q(good_q[0]),.c0(good_c[0][0]),.c1(good_c[0][1]));
 replicated_control #(.MASK(16'h0000)) u_all0(.ck(ck),.d(d),.q(good_q[1]),.c0(good_c[1][0]),.c1(good_c[1][1]));
 replicated_control #(.MASK(16'hFFFF)) u_all1(.ck(ck),.d(d),.q(good_q[2]),.c0(good_c[2][0]),.c1(good_c[2][1]));
 replicated_control #(.MASK(16'hAAAA)) u_even(.ck(ck),.d(d),.q(good_q[3]),.c0(good_c[3][0]),.c1(good_c[3][1]));
 replicated_control #(.MASK(16'h5555)) u_odd(.ck(ck),.d(d),.q(good_q[4]),.c0(good_c[4][0]),.c1(good_c[4][1]));
 replicated_control #(.MASK(16'h8421)) u_sparse(.ck(ck),.d(d),.q(good_q[5]),.c0(good_c[5][0]),.c1(good_c[5][1]));
 wire [15:0] bad_d_q,bad_cycle_q;
 replicated_control #(.MUT(1)) u_bad_d(.ck(ck),.d(d),.q(bad_d_q),.c0(),.c1());
 replicated_control #(.MUT(2)) u_bad_cycle(.ck(ck),.d(d),.q(bad_cycle_q),.c0(),.c1());
 reg [31:0] rng=32'h572b3ac1;integer mode=0,checks=0;
 initial begin
  if($value$plusargs("MODE=%d",mode)) begin end
  for(integer cycle=0;cycle<4098;cycle=cycle+1) begin
   @(negedge ck);
   if(cycle>=2) begin
    if(mode==0) begin
     for(integer m=0;m<6;m=m+1) begin
      if(good_c[m] !== {2{c1_bank}} || good_q[m] !== ref_q)
       $fatal(1,"CONTROL_REPLICA FAIL nominal cycle%0d maskcase%0d ref%h got%h",cycle,m,ref_q,good_q[m]);
      checks=checks+1;
     end
    end else if(mode==1 && bad_d_q !== ref_q)
     $fatal(1,"CONTROL_REPLICA MUTANT_D caught cycle%0d expected%h got%h",cycle,ref_q,bad_d_q);
    else if(mode==2 && bad_cycle_q !== ref_q)
     $fatal(1,"CONTROL_REPLICA MUTANT_CYCLE caught cycle%0d expected%h got%h",cycle,ref_q,bad_cycle_q);
   end
   rng={rng[30:0],rng[31]^rng[21]^rng[1]^rng[0]};
   d=(cycle<32) ? cycle[0] : rng[0];
  end
  if(mode!=0) $fatal(1,"CONTROL_REPLICA invalid test: mutant not caught");
  $display("CONTROL_REPLICA PASS cycles4096 masks6 checks%0d actualmaskABBF cycles_added0",checks);
  $finish;
 end
endmodule
