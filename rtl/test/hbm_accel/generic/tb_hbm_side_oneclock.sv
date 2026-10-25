`timescale 1ns/1ps
// Decision16a temporal miter: unchanged LAT3 arithmetic versus native LAT4,
// one item per clock, fixed function epochs; exact rounded words after priced delay.
module tb_hbm_side_oneclock;
 reg clk=0; always #0.4165 clk=~clk;
 reg rst_n=0,v=0; reg[2:0] fn=0; reg[31:0] x=0;
 wire[31:0] y3,y4,ym; wire f3,f4,fm;
 ot_hbm_su_static_side #(.MLAT(3),.ALAT(3)) ref0({6{clk}},rst_n,v,fn,x,fn,y3,f3);
 ot_hbm_su_static_side #(.MLAT(4),.ALAT(4)) dut({6{clk}},rst_n,v,fn,x,fn,y4,f4);
 ot_hbm_su_static_side #(.MLAT(4),.ALAT(4),.MUT(1)) mutant({6{clk}},rst_n,v,fn,x,fn,ym,fm);
 wire[31:0] core_y,sp_r; wire core_fault,sp_v,sp_fault;
 ot_hbm_su_side_rest_core rest(.clk_r({3{clk}}),.rst_n(rst_n),.v(v),.fn(fn),.x(x),.fn_out(fn),
  .y(core_y),.fault(core_fault),.sp_v(sp_v),.sp_r(sp_r ^ ($test$plusargs("MUT_CUT")?32'd1:32'd0)),.sp_fault(sp_fault));
 ot_hbm_su_side_softplus_core softplus(.clk({3{clk}}),.rst_n(rst_n),.v(sp_v),.x(x),.r(sp_r),.fault(sp_fault));
 reg delayed_sp_fault; always @(posedge clk) delayed_sp_fault<=dut.f_sp;
 wire expected_core_fault=dut.f_rsq|dut.f_sq|delayed_sp_fault|dut.f_eg1|dut.f_eg2|dut.f_eg3|dut.f_eg4;
 reg[31:0] history[0:63]; reg[31:0] expected,actual;
 integer epoch,i,k,delta,checks=0,mutant_diffs=0,seed=17;
 initial begin
  repeat(8)@(negedge clk);rst_n=1;v=1;
  for(epoch=0;epoch<4;epoch=epoch+1)begin
   case(epoch) 0:begin fn=2;delta=12;end 1:begin fn=3;delta=0;end
    2:begin fn=6;delta=36;end 3:begin fn=7;delta=16;end endcase
   for(i=0;i<1800;i=i+1)begin
    // Mix specials, subnormals, signs and finite exponent bands at full II1.
    case(i%16)
     0:x=0;1:x=32'h80000000;2:x=32'h7f800000;3:x=32'hff800000;
     4:x=32'h7fc00001;5:x=32'h00000001;6:x=32'h358637bd;
     default:x={$random(seed)};
    endcase
    @(posedge clk);#0.01;
    expected=delta==0?y3:history[delta-1];
    actual=$test$plusargs("MUT_FN")?ym:y4;
    if(i>300)begin
     checks=checks+1;
     if(core_y!==y4)$fatal(1,"SIDE_ONECLOCK CUT_WORD fn=%0d i=%0d got=%h ref=%h",fn,i,core_y,y4);
     if(core_fault!==expected_core_fault)$fatal(1,"SIDE_ONECLOCK CUT_FAULT fn=%0d i=%0d",fn,i);
     if(actual!==expected)$fatal(1,"SIDE_ONECLOCK mismatch fn=%0d i=%0d got=%h expected=%h delta=%0d",fn,i,actual,expected,delta);
     if(ym!==expected)mutant_diffs=mutant_diffs+1;
    end
    for(k=63;k>0;k=k-1)history[k]=history[k-1];history[0]=y3;
    @(negedge clk);
   end
  end
  if(checks!=5996||mutant_diffs==0)$fatal(1,"SIDE_ONECLOCK coverage checks=%0d mutants=%0d",checks,mutant_diffs);
  $display("SIDE_ONECLOCK PASS checks=%0d mutant_diffs=%0d II=1 added_cycles RSQRT12 SQRT0 SPSQRT36 EGATE16",checks,mutant_diffs);$finish;
 end
endmodule
