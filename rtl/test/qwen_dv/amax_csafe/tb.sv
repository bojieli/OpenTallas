`timescale 1ns/1ps
module tb;
parameter integer NU=4,MUT=0;
reg ck=0;always #5 ck=~ck;
reg rst=0,r1=0,r2=0;
always @(posedge ck) begin r1<=rst;r2<=r1;end
reg c_stn=0,stn_amax_bit=0,stn_pend=0,r_v=0,c_am=0,am_clr=0,am_emit_cmd=0;
reg[1:0] stn_user=0,am_user=0;
reg[23:0] r_addr=0;reg[511:0] r_d=0;
wire[60:0] a,b;
qfd_dv_amax_mu #(.NU(NU),.MUT(MUT)) ref_dut(.ck(ck),.rst(r2),.c_stn(c_stn),.stn_amax_bit(stn_amax_bit),.stn_user(stn_user),.stn_pend(stn_pend),.r_v(r_v),.r_addr(r_addr),.r_d(r_d),.c_am(c_am),.am_clr(am_clr),.am_emit_cmd(am_emit_cmd),.am_user(am_user),.am_v(a[60]),.am_idx(a[59:36]),.am_val(a[35:4]),.am_u(a[3:2]),.emit_empty(a[1]),.mu_fault(a[0]));
qfd_dv_amax_mu_csafe #(.NU(NU),.MUT(MUT)) dut(.ck(ck),.rst(rst),.c_stn(c_stn),.stn_amax_bit(stn_amax_bit),.stn_user(stn_user),.stn_pend(stn_pend),.r_v(r_v),.r_addr(r_addr),.r_d(r_d),.c_am(c_am),.am_clr(am_clr),.am_emit_cmd(am_emit_cmd),.am_user(am_user),.am_v(b[60]),.am_idx(b[59:36]),.am_val(b[35:4]),.am_u(b[3:2]),.emit_empty(b[1]),.mu_fault(b[0]));
integer n,j,errors=0;
initial begin
for(n=0;n<12000;n=n+1) begin
 @(negedge ck);
 rst=(n%997>=8);
 c_stn=$urandom_range(0,7)==0;stn_amax_bit=$random;stn_user=$random;stn_pend=$random;
 r_v=$random;r_addr=$random;c_am=$urandom_range(0,5)==0;
 am_clr=$random;am_emit_cmd=$random;am_user=$random;
 for(j=0;j<16;j=j+1) r_d[32*j+:32]=(n%5==0)?32'h3f800000:$random;
 @(posedge ck);#1;
 if(n>5 && a!==b) begin errors=errors+1;if(errors<5)$display("MISMATCH n=%0d ref=%h got=%h",n,a,b);end
end
if(errors)$fatal(1,"AMAX_EQ_FAIL NU=%0d MUT=%0d errors=%0d",NU,MUT,errors);
$display("AMAX_EQ_PASS NU=%0d MUT=%0d edges=12000 reset_bursts=13",NU,MUT);$finish;
end
endmodule
