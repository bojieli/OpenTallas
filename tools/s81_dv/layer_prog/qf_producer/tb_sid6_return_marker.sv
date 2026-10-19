`timescale 1ps/1ps
// Phase marker only. Existing selected routes; logical G=R0 experiment.
// Native clock insertion/reset dates are unqualified. No Q value stimulus.
module tb_sid6_return_marker;
 reg ck=0,rs=0,en=0; integer n=-1,mut=0; reg [69:0] src=0;
 always #417 ck=~ck;
 function automatic [69:0] mark(input integer s);
  mark={3'd0,(32'h53160000^s),32'(s),2'b11,1'b1};
 endfunction
 wire gck;
 ICGx4_ASAP7_75t_R gate0(.CLK(ck),.ENA(en),.SE(1'b0),.GCLK(gck));
 wire [69:0] sn,ns0,ns1,one,two;
 wire snck,nsck0,nsck1; wire f1,f2;
 dsfd_dvrlyh_70_SN s1(.ck(gck),.rs(rs),.i(src),.o(sn),.ck_o(snck));
 dsfd_dvland_70 l1(.ck_f(snck),.i(sn),.ck(ck),.rs(rs),.k(3'd2),.o(one),.fault(f1));
 dsfd_dvrlyh_70_NS s20(.ck(gck),.rs(rs),.i(src),.o(ns0),.ck_o(nsck0));
 dsfd_dvrlyh_70_NS s21(.ck(nsck0),.rs(rs),.i(ns0),.o(ns1),.ck_o(nsck1));
 dsfd_dvland_70 l2(.ck_f(nsck1),.i(ns1),.ck(ck),.rs(rs),.k(3'd2),.o(two),.fault(f2));
 integer ages[0:2];integer cnt[0:2];integer prev[0:2];integer j,id,age; reg[69:0] w;
 initial begin
  void'($value$plusargs("MUT=%d",mut));
  for(integer k=0;k<3;k++)begin ages[k]=-1;cnt[k]=0;prev[k]=-1;end
  #1 rs=0;
 end
 always @(negedge ck) begin
  if(n==5)rs<=1;
  if(n==5+(mut==1)-(mut==2))en<=1;
  if(mut==3 && n==40)en<=0;
  if(mut==3 && n==41)en<=1;
 end
 always @(posedge ck) begin
  n=n+1;src<=mark(n+(mut==4));
  #1;
  if(n>=32 && n<64)begin
   for(j=0;j<3;j++)begin
    case(j)0:w=src;1:w=one;2:w=two;endcase
    id=int'(w[34:3]);age=n+1-id;
    if(w!==mark(id))$fatal(1,"SID6_MARKER_FAIL word lane%0d n%0d",j,n);
    if(ages[j]<0)ages[j]=age;
    if(age!=(j==0?1:j==1?4:5))$fatal(1,"SID6_MARKER_FAIL baseline_age lane%0d observed%0d",j,age);
    if(age!=ages[j] || (cnt[j]>0 && id!=prev[j]+1))$fatal(1,"SID6_MARKER_FAIL age lane%0d n%0d",j,n);
    prev[j]=id;cnt[j]++;
   end
   if(f1||f2)$fatal(1,"SID6_MARKER_FAIL landing_epoch n%0d f%0b%0b",n,f1,f2);
  end
  if(n==64)begin
   $display("SID6_MARKER_PASS logicalG=R0 native_phase_UNQUALIFIED samples=%0d,%0d,%0d CAP_ARR_age=%0d,%0d,%0d",cnt[0],cnt[1],cnt[2],ages[0],ages[1],ages[2]);$finish;
  end
 end
endmodule
