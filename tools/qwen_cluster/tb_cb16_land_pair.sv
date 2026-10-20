`timescale 1ns/1ps
module tb_pair #(parameter integer W=258,parameter integer MUT=0,parameter integer PHASE_PS=100);
reg ck_w=0,ck_r=0,rst_n=0; always #0.5 ck_w=~ck_w;
initial begin #(0.001*PHASE_PS); forever #0.5 ck_r=~ck_r;end
reg[W-1:0]i=0; wire[W-1:0]o,ref_o; wire[4*W-1:0]bank; wire[4*((W+23)/24)-1:0]vld;
qfd_c_land_safe_w #(.W(W))ref_w(ck_w,rst_n,i,bank,vld);
qfd_c_land_safe_r #(.W(W),.K(2))ref_r(ck_r,rst_n,bank,vld,ref_o);
qfd_c_land_pair_safe #(.W(W),.K(MUT==1?3:2))dut(ck_w,ck_r,rst_n,rst_n,i,o);
genvar gg,ss;
generate for(gg=0;gg<(W+14)/15;gg=gg+1)begin:g_cap_audit
 localparam integer N=(W-gg*15<15)?W-gg*15:15;
 for(ss=0;ss<4;ss=ss+1)begin:g_bank_audit
  reg[N-1:0]sampled;reg enabled;
  always @(posedge ck_w)begin
   sampled=i[gg*15+:N];
   enabled=dut.g_slice[gg].u_w.g_bank[ss].active && dut.g_slice[gg].u_w.sel[ss];
   #0.001;
   if(enabled && dut.g_slice[gg].u_w.g_bank[ss].b !== sampled)
    $fatal(1,"PAIR_FIRST_CAPTURE_FAIL group=%0d slot=%0d",gg,ss);
  end
 end
end endgenerate
integer c,j,n=0; reg[W+31:0]word;
initial begin
for(c=0;c<5000;c=c+1)begin
 @(negedge ck_w);rst_n=!(c<20 || (c>=2000 && c<2300));
 for(j=0;j<W;j=j+32)word[j+:32]=$random;
 i=word[W-1:0];
end
repeat(5)@(posedge ck_r);
if(n<4900)$fatal(1,"PAIR_COVERAGE_FAIL checks=%0d",n);
$display("PAIR_PASS W=%0d PHASE_PS=%0d checks=%0d",W,PHASE_PS,n);$finish;
end
always @(posedge ck_r)begin #0.1;
 if(c>40)begin n=n+1;if(o!==ref_o)$fatal(1,"PAIR_MISMATCH W=%0d phase=%0d edge=%0d",W,PHASE_PS,c);end
end
endmodule
