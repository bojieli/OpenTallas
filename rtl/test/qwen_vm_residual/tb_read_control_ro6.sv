`timescale 1ns/1ps
module tb_read_control_ro6;
parameter integer MUT=0;
reg ck=0;always #5 ck=~ck;
reg rst_n=0,re0=0,re1=0;reg[23:0]a0=0,a1=0;
wire[15:0]sb_re;wire[159:0]raw_ra;wire[159:0]sb_ra=raw_ra^160'(MUT!=0);
wire bad,v3,v5,v6,v7,si7;wire[23:0]a5,a6,a7;
ot_qfd_vm_su_read_control #(.AW(24),.SW(64),.NRBS(16),.LAWS(10),.SX(12)) dut(
 .ck(ck),.rst_n(rst_n),.re0(re0),.re1(re1),.a0(a0),.a1(a1),.sb_re(sb_re),.sb_ra(raw_ra),.d2_bad(bad),
 .ov3(v3),.ov5(v5),.ov6(v6),.ov7(v7),.osi7(si7),.oa5(a5),.oa6(a6),.oa7(a7));
// Independent request timeline: issue descriptor, decode one edge later, bank request
// another edge later. 17 fixed descriptor ages; no response can move these slots.
reg pv=0,pr=0,qv=0,qs=0;integer pa=0,pb=0,qa=0,qn=0;
reg[16:0]vs=0,ss=0;reg[23:0]as_[0:16];
reg[15:0]er;reg[159:0]ea;reg eb;
integer i,j,k,bank,row,cyc,checks=0,errors=0;integer da,db;reg dv,dr,ds;
initial begin
 for(i=0;i<17;i=i+1)as_[i]=0;
 for(cyc=0;cyc<1600;cyc=cyc+1)begin
  @(negedge ck);
  rst_n=(cyc>=30 && cyc%137!=0);re0=(cyc%5!=0);re1=cyc%2;
  a0=24'((cyc*7919)%190000);a1=a0+((cyc%11==0)?7:((cyc%3==0)?0:1));
  if(cyc%19==0)a1=a0-1;
  @(posedge ck);
  for(i=16;i>0;i=i-1)begin vs[i]=vs[i-1];ss[i]=ss[i-1];as_[i]=as_[i-1];end
  vs[0]=qv;ss[0]=qs;as_[0]=24'(qa);
  er=0;ea=0;
  for(bank=0;bank<16;bank=bank+1)begin
   k=(bank-(qa/16)%16+16)%16;
   er[bank]=qv && k<qn;
   ea[bank*10+:10]=10'(((qa/16)+k)/16);
  end
  eb=rst_n && pv && pr && (pb-pa!=0) && (pb-pa!=1);
  ds=pr && (pb-pa==1);da=pa;db=pb;dv=pv;dr=pr;
  qv=rst_n && dv;qs=ds;qa=da;qn=ds?((da%16+63)/16+1):1;
  pv=rst_n && re0;pr=re1;pa=a0;pb=a1;
  #1;
  if(cyc>60)begin
   checks=checks+1;
   if(sb_re!==er || sb_ra!==ea || bad!==eb || {v3,v5,v6,v7,si7}!={vs[0],vs[14],vs[15],vs[16],ss[16]} || {a5,a6,a7}!={as_[14],as_[15],as_[16]})begin
    errors=errors+1;
    if(errors<5)$display("MISMATCH read_control cyc=%0d bankre=%h/%h bad=%b/%b",cyc,sb_re,er,bad,eb);
   end
  end
 end
 if(errors)$fatal(1,"FAIL read_control_ro6 checks=%0d errors=%0d",checks,errors);
 $display("PASS read_control_ro6 checks=%0d SX=12 FF=699 banks=16 LAWS=10",checks);$finish;
end
endmodule
