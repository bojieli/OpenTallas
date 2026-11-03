module cut_vehicle #(parameter W=828, LO=517, ST=12)(input clk,input rst_n,input ea,input integer iter,output reg done=0);
 reg[W-1:0] d;wire[W-1:0] oq[0:ST];wire[W-4:0] nq[0:ST],mq[0:ST];wire oe[0:ST],ne[0:ST],me[0:ST];integer i,j,checks=0,mutants=0;
 function automatic[W-4:0] cut(input[W-1:0] x);integer k;begin for(k=0;k<W-3;k=k+1)cut[k]=x[k<LO?k:k+3];end endfunction
 assign oq[0]=d;assign nq[0]=cut(d);assign mq[0]=cut(d)^1;assign oe[0]=ea;assign ne[0]=ea;assign me[0]=!ea;
 genvar g;generate for(g=0;g<ST;g=g+1)begin
 ot_dp_st #(.W(W)) gold(clk,rst_n,oq[g],oe[g],oq[g+1],oe[g+1]);
 ot_dp_st #(.W(W-3)) prop(clk,rst_n,nq[g],ne[g],nq[g+1],ne[g+1]);
 ot_dp_st #(.W(W-3)) wrong(clk,rst_n,mq[g],me[g],mq[g+1],me[g+1]);
 end endgenerate
 always @(negedge clk)begin for(i=0;i<W;i=i+1)d[i]=$random;d[LO+:3]=0;end
 always @(posedge clk)begin #1;if(iter>ST+2)begin for(j=1;j<=ST;j=j+1)begin
  if(nq[j]!==cut(oq[j])||ne[j]!==oe[j])$fatal(1,"CUT_EQ_FAIL W%0d ST%0d",W,j);
  checks=checks+1;if(mq[j]!==cut(oq[j]))mutants=mutants+1;
 end end if(iter==220)begin if(mutants!=checks||checks==0)$fatal(1,"MUTANT_NOT_DETECTED");$display("PASS W%0d DROP%0d checks%0d wrong_retainedbit%0d ST%0d reset_epoch_exact",W,LO,checks,mutants,ST);done=1;end end
endmodule
module tb;reg clk=0,rst_n=0,ea=0;integer iter=0;wire[3:0]done;always #416.5 clk=~clk;always @(negedge clk)begin iter=iter+1;ea=$random;end
initial begin #19 rst_n=1;repeat(12)begin #10017 rst_n=0;#777 rst_n=1;end end
cut_vehicle #(.W(4986),.LO(517))a(clk,rst_n,ea,iter,done[0]);cut_vehicle #(.W(828),.LO(517))b(clk,rst_n,ea,iter,done[1]);cut_vehicle #(.W(4127),.LO(35))c(clk,rst_n,ea,iter,done[2]);cut_vehicle #(.W(8),.LO(5))d(clk,rst_n,ea,iter,done[3]);always @(posedge clk)if(&done)begin $display("ALL4CUTS_PASS_SELECTED_PRIMITIVE_NO_ADDED_EDGES");$finish;end
endmodule
