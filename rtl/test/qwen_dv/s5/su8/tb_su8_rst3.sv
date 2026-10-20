`timescale 1ns/1ps
module tb_su8_rst3;
reg ck=0,runck=1,rn=1,start=0;always #1 if(runck)ck=~ck;
reg [456:0] si=0;reg [7:0] lf=0;
wire [243:0] gb0,gb1;wire [2:0] gv0,gv1;wire [7:0] lv0,lv1;
wire [767:0] pd0,pd1;wire nr0,nr1,idle0,idle1,fault0,fault1;wire [15:0] prog0,prog1,rows0,rows1;
qfd_dv_s5_su8 u0(.ck(ck),.rst_n(rn),.start(start),.si(si),.l_retire(1'b0),.l_last(1'b0),.l_fault(lf),.kv_we(8'd0),.rd_v(1'b0),.red_busy(1'b0),.red_fault(1'b0),.lvm_we(8'd0),.gb(gb0),.gv(gv0),.lv1(lv0),.pd1(pd0),.su_nr(nr0),.su_idle(idle0),.su_fault(fault0),.su_prog(prog0),.su_rows(rows0));
qfd_dv_s5_su8_rst3 u1(.ck(ck),.rst_n(rn),.start(start),.si(si),.l_retire(1'b0),.l_last(1'b0),.l_fault(lf),.kv_we(8'd0),.rd_v(1'b0),.red_busy(1'b0),.red_fault(1'b0),.lvm_we(8'd0),.gb(gb1),.gv(gv1),.lv1(lv1),.pd1(pd1),.su_nr(nr1),.su_idle(idle1),.su_fault(fault1),.su_prog(prog1),.su_rows(rows1));
qfd_dv_s5_su8_rst3_dropassert u_bad(.ck(ck),.rst_n(rn),.start(start),.si(si),.l_retire(1'b0),.l_last(1'b0),.l_fault(lf),.kv_we(8'd0),.rd_v(1'b0),.red_busy(1'b0),.red_fault(1'b0),.lvm_we(8'd0),.gb(),.gv(),.lv1(),.pd1(),.su_nr(),.su_idle(),.su_fault(),.su_prog(),.su_rows());
integer mutant_held_fail=0;
integer epoch,e,bad=0,first0,first1,checks=0,active_hits=0,fault_hits=0;
reg [2:0] held_gv0,held_gv1;reg held_fault0,held_fault1;
initial begin
 si[18:1]=2;si[36:19]=256;si[109:86]=1;si[182:159]=3;si[255:232]=5;si[341:318]=7;
 for(epoch=0;epoch<5;epoch=epoch+1)begin
  @(negedge ck);start=0;lf=0;runck=0;
  held_gv0=gv0;held_gv1=gv1;held_fault0=fault0;held_fault1=fault1;
  #0.133;rn=0;#0.017;
  checks=checks+1;
  if(epoch>0 && (u_bad.act_k!==0 || u_bad.fault_q!==0))mutant_held_fail=mutant_held_fail+1;
  if(u0.act_k!==0||u1.act_k!==0||u0.fault_q!==0||u1.fault_q!==0||u1.rst_k!==0||u1.rc_k!==0)bad=bad+1;
  // Output pins retain their last sampled value when ck is held, in BOTH designs.
  if(gv0!==held_gv0||gv1!==held_gv1||fault0!==held_fault0||fault1!==held_fault1)bad=bad+1;
  #3.141;rn=1;#3.017;
  if(u1.rst_k!==0||u1.rs0!==0||u1.rs1!==0)bad=bad+1;
  runck=1;
  for(e=1;e<=8;e=e+1)begin
   @(posedge ck);#0.01;checks=checks+1;
   if(u0.rst_k!==(e>=2?6'b111111:6'b0))bad=bad+1;
   if(u1.rst_k!==(e>=3?6'b111111:6'b0))bad=bad+1;
  end
  // Both boots reserve eight release edges; new leaf release itself costs exactly+1.
  @(negedge ck);start=1;first0=-1;first1=-1;
  for(e=0;e<16;e=e+1)begin
   @(posedge ck);#0.01;
   if(gv0[1]&&first0<0)first0=e;
   if(gv1[1]&&first1<0)first1=e;
   if(e==0)begin @(negedge ck);start=0;end
  end
  if(first0!=first1||first1<0)bad=bad+1;
  if(|u0.act_k && |u1.act_k)active_hits=active_hits+1;else bad=bad+1;
  @(negedge ck);lf=1;
  repeat(7)@(posedge ck);#0.01;
  if(fault0&&fault1)fault_hits=fault_hits+1;else bad=bad+1;
  $display("RST3_EPOCH epoch=%0d first_valid_edge=%0d leaf_release_old=2 new=3 held_clock_async_clear=1",epoch,first1);
 end
 $display("RST3_STATS checks=%0d active=%0d fault=%0d bad=%0d",checks,active_hits,fault_hits,bad);
 $display("RST3_DROPASSERT_MUTANT held_clock_failures=%0d",mutant_held_fail);
 if(checks>=40&&active_hits==5&&fault_hits==5&&bad==0&&mutant_held_fail>=4)$display("SU8_RST3 PASS");else $display("SU8_RST3 FAIL");$finish;
end endmodule
