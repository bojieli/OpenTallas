`timescale 1ns/1ps
module tb;
reg clk=0;always #5 clk=~clk;
reg rst_n=0;reg[35:0] irq;reg[33:0] tq,aq;reg[513:0] rr;
wire[33:0] oldirq={irq[35:34],irq[32:18],irq[17:16],irq[14:0]};
wire[33:0] gq;wire[35:0] nq;wire[513:0] gi,gt,ga,ni,nt,na;wire gf,nf;
ot_hbm_idx_vm_share_leaf_r #(.VM_RT(75),.F32(1)) gold(.clk(clk),.rst_n(rst_n),.index_rq(oldirq),.topk_rq(tq),.argmax_rq(aq),.vm_rq(gq),.vm_rr(rr),.index_rr(gi),.topk_rr(gt),.argmax_rr(ga),.fault(gf));
ot_hbm_idx_vm_share_leaf_index18_r2048 #(.VM_RT(75),.F32(1)) dut(.clk(clk),.rst_n(rst_n),.index_rq(irq),.topk_rq(tq),.argmax_rq(aq),.vm_rq(nq),.vm_rr(rr),.index_rr(ni),.topk_rr(nt),.argmax_rr(na),.fault(nf));
integer checks=0,high=0,mirror=0;reg[35:0] expected;reg[2:0] v;
initial begin
irq=0;tq=0;aq=0;rr=0;
for(integer n=0;n<700;n=n+1)begin
 @(negedge clk);rst_n=(n>3 && !(n>=350&&n<354));
 irq={$random,$random};tq={$random,$random};aq={$random,$random};
 for(integer k=0;k<17;k=k+1)rr[30*k+:30]=$random;
 rr[513:510]=$random;
 @(posedge clk);#1;
 expected=0;
 for(integer b=0;b<2;b=b+1)begin
 v={aq[17*b+16],tq[17*b+16],irq[18*b+17]};
 if(v==1)begin expected[18*b+:18]=irq[18*b+:18];if(irq[18*b+15])high=high+1;end
 else if(v==2)begin expected[18*b+:18]={tq[17*b+16],tq[17*b+15],1'b0,tq[17*b+:15]};if(tq[17*b+15])mirror=mirror+1;end
 else if(v==4)begin expected[18*b+:18]={aq[17*b+16],aq[17*b+15],1'b0,aq[17*b+:15]};if(aq[17*b+15])mirror=mirror+1;end
 end
 if(nq!==expected)$fatal(1,"request field mismatch n=%0d",n);
 if(rst_n && n>90 && (ni!==gi||nt!==gt||na!==ga||nf!==gf))$fatal(1,"legacy response/fault mismatch n=%0d",n);
 checks=checks+1;
end
if(high<20||mirror<20)$fatal(1,"coverage");
$display("PASS checks=%0d high=%0d mirror=%0d",checks,high,mirror);$finish;
end
endmodule
