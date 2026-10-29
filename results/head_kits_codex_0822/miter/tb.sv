`timescale 1ns/1ps
module tb;
reg clk=0,rst=0,start=0;always #5 clk=~clk;
reg[514:0]ui=0;reg[512:0]di=0;wire[514:0]uo,un,um;wire[512:0]do_,dn,dm;wire[1:0]ro,rn,rm,so,sn,sm;
reg[513:0]pu0,pu1;reg[511:0]pd0,pd1;reg eu0,eu1,ed0,ed1;
integer i,b,seed=12345,checks=0,caught=0,settle=0;reg[31:0]a,c;
old_ft gold (.clk(clk),.clk_t1(clk),.clk_t2(clk),.clk_t3(clk),.clk_t4(clk),.arst_n(rst),.start_i(start),.u_i(ui),.d_i(di),.u_o(uo),.d_o(do_),.rst_o_0(ro[0]),.rst_o_1(ro[1]),.start_o_0(so[0]),.start_o_1(so[1]));
new_ft dut (.clk(clk),.clk_t1(clk),.clk_t2(clk),.clk_t3(clk),.clk_t4(clk),.clk_t5(clk),.clk_t6(clk),.clk_t7(clk),.clk_t8(clk),.clk_t9(clk),.clk_t10(clk),.clk_t11(clk),.clk_t12(clk),.clk_t13(clk),.clk_t14(clk),.clk_t15(clk),.arst_n(rst),.start_i(start),.u_i(ui),.d_i(di),.u_o(un),.d_o(dn),.rst_o_0(rn[0]),.rst_o_1(rn[1]),.start_o_0(sn[0]),.start_o_1(sn[1]));
mut_ft mutant (.clk(clk),.clk_t1(clk),.clk_t2(clk),.clk_t3(clk),.clk_t4(clk),.clk_t5(clk),.clk_t6(clk),.clk_t7(clk),.clk_t8(clk),.clk_t9(clk),.clk_t10(clk),.clk_t11(clk),.clk_t12(clk),.clk_t13(clk),.clk_t14(clk),.clk_t15(clk),.arst_n(rst),.start_i(start),.u_i(ui),.d_i(di),.u_o(um),.d_o(dm),.rst_o_0(rm[0]),.rst_o_1(rm[1]),.start_o_0(sm[0]),.start_o_1(sm[1]));
initial begin
for(i=0;i<4096;i=i+1)begin
 @(negedge clk);rst=!(i<12 || (i>=2020 && i<2032));start=!(i<18 || (i>=2020 && i<2038));
 a=$random(seed);c=$random(seed);ui={i[0],a[1:0],{16{a}}};di={!i[0],{16{c}}};
 @(posedge clk);#1;
 if(i>8)begin
  if(un[513:0]!==pu1 || dn[511:0]!==pd1)$fatal(1,"payload miter i=%0d",i);
  if(um[513:0]!==pu1)caught=caught+1;
  if(ro!==rn || so!==sn)$fatal(1,"boot depth changed i=%0d",i);
  if(!rst || !start)settle=0;else settle=settle+1;
  if(settle>20)begin
   if(un[514]!==eu1 || dn[512]!==ed1)$fatal(1,"epoch miter i=%0d",i);
  end
  if(rn==0 && (un[514]!==0 || dn[512]!==0))$fatal(1,"reset epoch i=%0d",i);
  checks=checks+1;
 end
 pu1=pu0;pu0=uo[513:0];pd1=pd0;pd0=do_[511:0];eu1=eu0;eu0=uo[514];ed1=ed0;ed0=do_[512];
end
if(caught==0)$fatal(1,"mutant escaped");
$display("PASS lockstep payload1026bits +epoch/reset: checks=%0d mutant_caught=%0d added_data_cycles=2 boot_delta=0",checks,caught);$finish;
end
endmodule
