`timescale 1ns/1ps
module tb_s81_hcx_vm_scheduled;
 localparam integer RL=4,WL=4;
 reg clk=0;always #5 clk=~clk;
 reg rn=0,start=0;reg[337:0]q=0;wire[273:0]r;wire rv,wv;wire[13:0]ra,wa;wire[15:0]wm;wire[511:0]wd;wire f;
 reg[RL-1:0]read_v=0;reg[511:0]read_d[0:RL-1];
 reg[WL-1:0]commit_v=0;reg[13:0]write_a[0:WL-1];reg[15:0]write_m[0:WL-1];reg[511:0]write_d[0:WL-1];
 integer cycle=0,reads=0,writes=0,returns=0;
 reg[511:0]coef[0:1];
 reg[273:0]due[0:4000];
`ifdef MUT_LATE_COMMIT
 wire commit=commit_v[WL-1] && writes!=4;
`else
 wire commit=commit_v[WL-1];
`endif
`ifdef MUT_DROP_EPS
 localparam integer MUT=1;
`else
 localparam integer MUT=0;
`endif
 ot_s81_hcx_vm_scheduled #(.RL(RL),.WL(WL),.MUT_DROP_EPS(MUT))u(.clk(clk),.rst_n(rn),.job_start(start),.coef_base_row(14'd2560),.norm_eps(32'h3727c5ac),.vmq(q),.vmr(r),.rq_v(rv),.rq_row(ra),.rs_v(read_v[RL-1]),.rs_d(read_d[RL-1]),.wq_v(wv),.wq_row(wa),.wq_mask(wm),.wq_d(wd),.wq_commit(commit),.fault(f));
 function automatic[511:0] native_row(input[13:0]row);
  for(integer i=0;i<32;i=i+1)native_row[16*i+:16]=16'(32*row+i);
 endfunction
 function automatic[255:0] sector_data(input integer sec);
  for(integer i=0;i<8;i=i+1)sector_data[32*i+:32]={16'(8*sec+i),16'd0};
 endfunction
 always @(posedge clk)begin
  cycle<=cycle+1;
  read_v[0]<=rv;read_d[0]<=native_row(ra);
  for(integer i=1;i<RL;i=i+1)begin read_v[i]<=read_v[i-1];read_d[i]<=read_d[i-1];end
  commit_v[0]<=wv;write_a[0]<=wa;write_m[0]<=wm;write_d[0]<=wd;
  for(integer i=1;i<WL;i=i+1)begin commit_v[i]<=commit_v[i-1];write_a[i]<=write_a[i-1];write_m[i]<=write_m[i-1];write_d[i]<=write_d[i-1];end
  if(rv)reads<=reads+1;
  if(wv)writes<=writes+1;
  if(commit)for(integer i=0;i<16;i=i+1)if(write_m[WL-1][i])coef[write_a[WL-1]-2560][32*i+:32]<=write_d[WL-1][32*i+:32];
 end
 always @(negedge clk) if(rn)begin
  #1;
  if(r!==due[cycle] && (r[273] || due[cycle][273]))$fatal(1,"timeline mismatch cycle%0d got%h expected%h",cycle,r,due[cycle]);
  if(r[273])returns=returns+1;
 end
 initial begin
  for(integer i=0;i<=4000;i=i+1)due[i]=0;
  coef[0]='1;coef[1]='1;
  repeat(3)@(negedge clk);rn=1;start=1;
  @(negedge clk);start=0;
  // Full residual: 640 physical rows, 2560 canonical sector packets.
  for(integer sec=0;sec<2560;sec=sec+1)begin
   #2;q={1'b1,1'b0,27'(sec),5'd0,256'd0,32'd0,16'(sec)};
   due[cycle+RL+1]={1'b1,16'(sec),1'b0,sector_data(sec)};
   @(negedge clk);
  end
  #2;q=0;repeat(RL+3)@(negedge clk);
  for(integer sec=0;sec<3;sec=sec+1)begin
   #2;q={1'b1,1'b1,27'(5120+sec),5'd0,sector_data(700+sec),32'hffffffff,16'(3000+sec)};
   due[cycle+WL+1+(sec==2)]={1'b1,16'(3000+sec),1'b1,256'd0};
   @(negedge clk);
  end
  #2;q=0;repeat(WL+4)@(negedge clk);#2;
  if(reads!=640||writes!=4||returns!=2563)$fatal(1,"wrong physical schedule read%0d write%0d response%0d",reads,writes,returns);
`ifdef MUT_LATE_COMMIT
  if(!f)$fatal(1,"late commit not detected");
  $display("S81_HCX_SCHEDULE MUTANT DETECTED fixed completion timeline unchanged, native write missing");
`else
  if(f)$fatal(1,"unexpected fault");
  if(coef[0]!=={sector_data(702),sector_data(701)} || coef[1]!=={224'd0,32'h3727c5ac,sector_data(700)})$fatal(1,"coefficient comb/pre/post/EPS layout mismatch");
  $display("S81_HCX_SCHEDULE PASS 20480 BF16 values,640 native reads,4 native writes,2563 exact fixed returns, cycle%0d",cycle);
`endif
  $finish;
 end
 initial begin #40000;$fatal(1,"timeout");end
endmodule
