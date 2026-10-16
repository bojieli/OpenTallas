`timescale 1ns/1ps
module tb_vmwrite_v6_mapping;
 parameter integer MAP_MUT=0;
 reg [3:0] cd=0;
 reg cc=0,ct=0,cm=0,cb=0; reg [7:0] co=0;
 reg rst_n=0;reg[1:0] sid=0;reg[3:0] rv=0;reg[159:0] ra=0;reg[2047:0] rd=0;
 reg vm=0,tv=0;reg[567:0] td=0;reg[4:0] slot=0;reg[7:0] sv=0;reg[31:0] so=0;
 wire[2247:0] kq;wire[4:0] done;wire fault;
 wire[3:0] mapped=MAP_MUT ? {cd[2],cd[3],cd[1:0]} : cd;
 ot_hgi_coll_static_vmwrite_roots_v7_sid2 dut(.clk_rgx_data0(mapped[0]),.clk_rgx_data1(mapped[1]),.clk_rgx_data2(mapped[2]),.clk_rgx_data3(mapped[3]),.clk_rgx_ctrl(cc),.clk_tkw(ct),.clk_meta(cm),.clk_body(cb),.clk_bank0(co[0]),.clk_bank1(co[1]),.clk_bank2(co[2]),.clk_bank3(co[3]),.clk_bank4(co[4]),.clk_bank5(co[5]),.clk_bank6(co[6]),.clk_bank7(co[7]),.rst_n(rst_n),.rgx_v(rv),.rgx_addr(ra),.rgx_data0(rd[0+:512]),.rgx_data1(rd[512+:512]),.rgx_data2(rd[1024+:512]),.rgx_data3(rd[1536+:512]),.rgx_vm(vm),.tkw_v(tv),.tkw_d(td),.ingress_slot(slot),.slot_valid(sv),.slot_owner(so),.kq0(kq[0+:281]),.kq1(kq[281+:281]),.kq2(kq[562+:281]),.kq3(kq[843+:281]),.kq4(kq[1124+:281]),.kq5(kq[1405+:281]),.kq6(kq[1686+:281]),.kq7(kq[1967+:281]),.launch_done(done),.fault(fault));
 integer n,j,checks=0;
 reg[2047:0] old;
 initial begin
  // Establish known capture values, then pulse ONE physical entry at a time.
  #1; cd=15;cc=1;ct=1;cm=1;cb=1;co=255; #1;
  cd=0;cc=0;ct=0;cm=0;cb=0;co=0;rst_n=1; #1;cm=1;#1;cm=0;
  for(n=0;n<4;n=n+1)begin
   rd[n*512+:512]={16{32'h12340000+n}};
   old=dut.core.d0[2047:0];#1;cd[n]=1;#1;cd[n]=0;
   for(j=0;j<4;j=j+1)begin
    if(dut.core.d0[j*512+:512] !== (j==n ? rd[j*512+:512] : old[j*512+:512]))$fatal(1,"capture clock mapping root=%0d lane=%0d",n,j);
    checks=checks+1;
   end
  end
  ra={5{32'h87654321}};rv=15;#1;cc=1;#1;cc=0;
  if(dut.core.a0[159:0]!==ra || dut.core.v0[3:0]!==rv)$fatal(1,"RGX control capture root");checks=checks+1;
  td={17{32'haabbccdd}};tv=1;#1;ct=1;#1;ct=0;
  if({dut.core.a0[199:160],dut.core.m0[79:64],dut.core.d0[2559:2048]}!==td || dut.core.v0[4]!==tv)$fatal(1,"TKW capture root");checks=checks+1;
  sid=2;vm=1;slot=21;sv=8'hb5;so=32'h456789ab;#1;cm=1;#1;cm=0;
  if({dut.core.sid_q,dut.core.vm_q,dut.core.islot_q,dut.core.sv_q,dut.core.so_q}!=={sid,vm,slot,sv,so})$fatal(1,"metadata capture root");checks=checks+1;
  $display("VMWRITE_V6_MAPPING PASS checks=%0d capture_roots=7 swap_detected=required",checks);$finish;
 end
endmodule
