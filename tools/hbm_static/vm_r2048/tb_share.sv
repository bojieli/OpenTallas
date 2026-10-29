`timescale 1ns/1ps
module tb_share;
parameter MUT=0;
reg clk=0;always #5 clk=~clk;reg rst=0;
reg[135:0]a=0,b=0;reg[143:0]an=0,bn=0;wire[135:0]q;wire[143:0]qn;reg[2055:0]rr=0;
wire[2055:0]ar,br,arn,brn;wire f,fn;
ot_hbm_idx_vm_share2_static_r #(.BANK_RT(54)) gold(.clk_pair({4{clk}}),.rst_n(rst),.a_rq(a),.b_rq(b),.vm_rq(q),.vm_rr(rr),.a_rr(ar),.b_rr(br),.fault(f));
ot_hbm_idx_vm_share2_static_r_r2048 #(.BANK_RT(54),.MUT(MUT)) dut(.clk_pair({4{clk}}),.rst_n(rst),.a_rq(an),.b_rq(bn),.vm_rq(qn),.vm_rr(rr),.a_rr(arn),.b_rr(brn),.fault(fn));
reg[143:0]lift,expected;integer i,k;
task tick;begin @(posedge clk);#1;end endtask
initial begin
 repeat(5)tick();@(negedge clk);rst=1;repeat(5)tick();
 for(i=0;i<250;i=i+1)begin
  @(negedge clk);a=0;b=0;an=0;bn=0;expected=0;
  for(k=0;k<8;k=k+1)begin
   a[k*17+:17]=$random;b[k*17+:17]=$random;
   an[k*18+:18]={a[k*17+16],a[k*17+15],1'b0,a[k*17+:15]};
   bn[k*18+:18]={b[k*17+16],b[k*17+15],1'b0,b[k*17+:15]};
   rr[k*257+:257]={1'b1,256'(i*8+k)};
  end
  tick();for(k=0;k<8;k=k+1)begin
   if(qn[k*18+17]!==q[k*17+16])$fatal(1,"valid date");
   if(q[k*17+16] && qn[k*18+:17]!=={q[k*17+15],1'b0,q[k*17+:15]})$fatal(1,"legacy packet");
  end
  if(f!==fn || ar!==arn || br!==brn)$fatal(1,"owner response/date");
 end
 @(negedge clk);an=0;bn=0;an[17:0]={1'b1,17'h08005};tick();if(qn[17:0]!==an[17:0])$fatal(1,"high regular lost");
 @(negedge clk);an[17:0]={1'b1,17'h10005};tick();if(qn[17:0]!==an[17:0])$fatal(1,"mirror lost");
 $display("NATIVE_SHARE PASS bankrt54 250legacyedges highregular mirror responseowner samecycles");$finish;
end
endmodule
