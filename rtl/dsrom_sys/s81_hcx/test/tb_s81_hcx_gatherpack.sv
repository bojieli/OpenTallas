`timescale 1ns/1ps
module tb_s81_hcx_gatherpack;
 reg clk=0;always #5 clk=~clk;
 reg rn=0,start=0,iv=0;reg[1:0]rank=0;reg[511:0]id=0;
 wire wv,done,f;wire[13:0]wa;wire[15:0]wm;wire[511:0]wd;
 reg[3:0]commits=0;integer cyc=0,t0,issue0=-1,issue1=-1,donecycle=-1,writes=0;reg[511:0]got[0:1];
 ot_s81_hcx_gatherpack u(.clk(clk),.rst_n(rn),.start(start),.raw_base_row(14'd2624),.i_v(iv),.i_rank(rank),.i_d(id),.wq_v(wv),.wq_row(wa),.wq_mask(wm),.wq_d(wd),.wq_commit(commits[3]),.done(done),.fault(f));
 always @(posedge clk)begin
  if(done)donecycle=cyc-t0;
  cyc<=cyc+1;commits<={commits[2:0],wv};
  if(wv)begin
   if(wm!=16'hffff)$fatal(1,"partialraw row");
   got[wa-2624]<=wd;
   if(writes==0)issue0=cyc-t0;else issue1=cyc-t0;
   writes=writes+1;
  end
 end
 initial begin
  repeat(3)@(negedge clk);rn=1;start=1;t0=cyc;@(negedge clk);start=0;
  for(integer step=0;step<24;step=step+1)begin
   iv=0;
   if(step==0||step==4||step==8||step==12)begin
    rank=2'(step/4);iv=1;id='1;
    for(integer j=0;j<6;j=j+1)id[32*j+:32]=32'h3f000000+32'(6*rank+j);
`ifdef MUT_RANK
    if(step==8)iv=0;
`endif
   end
   @(negedge clk);
  end
  if(writes!=2||issue0!=16||issue1!=17||donecycle!=23)$fatal(1,"writecalendar %0d %0d writes%0d",issue0,issue1,writes);
  for(integer j=0;j<24;j=j+1)if(got[j/16][32*(j%16)+:32]!==32'h3f000000+32'(j))$fatal(1,"compactionword%0d",j);
  if(got[1][511:256]!==256'd0)$fatal(1,"padding");
  if(f)$fatal(1,"HCX_GATHERPACK FAIL fixedwritesobserved%0d,%0d",issue0,issue1);
  $display("HCX_GATHERPACK PASS exact24words fullrows2 fixedwrites%0d,%0d fixedcompletion%0d",issue0,issue1,donecycle);$finish;
 end
endmodule
