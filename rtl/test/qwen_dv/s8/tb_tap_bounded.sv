`timescale 1ns/1ps
module tb_tap_bounded;
reg ck=0;always #5 ck=~ck;
reg rst=0;reg[3:0]sid=0;reg[452:0]hr=0;reg xtv=0;reg[23:0]xta=0;reg[1023:0]xtd=0;reg xtbad=0;reg[7:0]lqbad=0;
integer cycle=0,mutant=0,checks=0;
initial begin if($value$plusargs("mutant=%d",mutant))begin end end
always @(negedge ck)begin
 cycle=cycle+1;rst=!(cycle<8 || (cycle>=9000&&cycle<9008));sid=$random;hr={$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random};
 xtv=$random;xta=$random;xtbad=($random%1024==0);lqbad=$random%1024==0;
 for(integer i=0;i<32;i=i+1)xtd[i*32+:32]=$random;
end
wire[1566:0]a,b;wire[23:0]ca,cb;wire fa,fb;
qfd_dv_s6_tap refdut(.ck(ck),.rst_n(rst),.sid(sid),.hr_q(hr),.xt_v(xtv),.xt_a(xta),.xt_d(xtd),.xt_bad(xtbad),.lq_bad(lqbad),.hw(a),.cid(ca),.tap_fault(fa));
qfd_dv_s8_tap_bounded newdut(.ck(ck),.rst_n(rst),.sid(sid),.hr_q(hr),.xt_vcopies({6{xtv ^ (mutant!=0)}}),.xt_a(xta),.xt_d(xtd),.xt_bad(xtbad),.lq_bad(lqbad),.hw(b),.cid(cb),.tap_fault(fb));
always @(posedge ck)begin #1;
 if(cycle>50)begin
  if({a,ca,fa}!=={b,cb,fb})$fatal(1,"TAP_BOUNDED_MISMATCH cycle%0d mutant%0d hw%0d cid%0d fault%0d",cycle,mutant,a!==b,ca!==cb,fa!==fb);
  checks=checks+1;
 end
 if(cycle==20000)begin $display("PASS TAP exact source bounded sameedge checks%0d two resets",checks);$finish;end
end
endmodule
