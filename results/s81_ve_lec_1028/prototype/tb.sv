`timescale 1ns/1fs
module tb #(parameter MUT=0);
reg clk=0;always #0.4165 clk=~clk;
reg rst_n=0;
reg r_v=0,a_v=0;reg[1:0]r_c=0,a_c=0;
reg[63:0]r_h=0;reg[127:0]r_k=0,r_w=0,a_h=0;reg[255:0]a_val=0;reg[31:0]a_g=0;
wire go_v,gm_v,gm_pre,gfault,no_v,nm_v,nm_pre,nfault;
wire[1:0]go_c,no_c;wire[127:0]go_y,no_y,gm_hh,nm_hh,gm_kk,nm_kk,gm_dd,nm_dd;
ot_s81sl_ve_m_gold gold(.clk(clk),.rst_n(rst_n),.r_v(r_v),.r_c(r_c),.r_h(r_h),.r_k(r_k),.r_w(r_w),
.a_v(a_v),.a_c(a_c),.a_h(a_h),.a_val(a_val),.a_g(a_g),.o_v(go_v),.o_c(go_c),.o_y(go_y),.m_v(gm_v),.m_pre(gm_pre),
.m_hh(gm_hh),.m_kk(gm_kk),.m_dd(gm_dd),.fault(gfault));
ot_s81sl_ve_m #(.MUT(MUT)) trial(.clk(clk),.rst_n(rst_n),.r_v(r_v),.r_c(r_c),.r_h(r_h),.r_k(r_k),.r_w(r_w),
.a_v(a_v),.a_c(a_c),.a_h(a_h),.a_val(a_val),.a_g(a_g),.o_v(no_v),.o_c(no_c),.o_y(no_y),.m_v(nm_v),.m_pre(nm_pre),
.m_hh(nm_hh),.m_kk(nm_kk),.m_dd(nm_dd),.fault(nfault));
wire [517:0] gall={go_v,gm_v,gm_pre,gfault,go_c,go_y,gm_hh,gm_kk,gm_dd};
wire [517:0] nall={no_v,nm_v,nm_pre,nfault,no_c,no_y,nm_hh,nm_kk,nm_dd};
integer bitidx;
integer cyc,checks=0,bad=0,ri=0,ai=0;
initial begin
 for(cyc=0;cyc<256;cyc=cyc+1)begin
  @(negedge clk);rst_n=(cyc>=4);
  r_v=($urandom%4)!=0;a_v=($urandom%4)!=0;
  r_c=(ri>>4)&3;a_c=ai&3;if(r_v)ri=ri+1;if(a_v)ai=ai+1;
  r_h={$urandom,$urandom};r_k={$urandom,$urandom,$urandom,$urandom};r_w={$urandom,$urandom,$urandom,$urandom};
  a_h={$urandom,$urandom,$urandom,$urandom};
  a_val={$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom};a_g=$urandom;
  @(posedge clk);#0.1;
  if(cyc>=4)begin
   for(bitidx=0;bitidx<518;bitidx=bitidx+1)begin
    if((gall[bitidx]===1'b0)||(gall[bitidx]===1'b1))begin
     checks=checks+1;
     if(nall[bitidx]!==gall[bitidx])begin
      bad=bad+1;if(bad<9)$display("DEFINED_DIFF cyc=%0d bit=%0d old=%b new=%b",cyc,bitidx,gall[bitidx],nall[bitidx]);
     end
    end
   end
  end
 end
 $display("VE_ZERO_FOURSTATE mut=%0d checks=%0d bad=%0d",MUT,checks,bad);
 if(checks>20000&&bad==0)$display("VE_ZERO_PASS");else $display("VE_ZERO_FAIL");
 $finish;
end
endmodule
