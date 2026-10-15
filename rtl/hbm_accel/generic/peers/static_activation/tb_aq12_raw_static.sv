`timescale 1ps/1fs
module tb_aq12_raw_static;
 parameter integer MUT=0,N=1638;
 reg clk=0;always #416.6665 clk=~clk;
 wire[5:0]clock_root={6{clk}};
 reg rst_n=0;reg[1:0]v=0;reg[1023:0]x[0:1];
 wire[1:0]vo,fault;wire[255:0]q[0:1];wire signed[9:0]e[0:1];wire[511:0]y[0:1];
 for(genvar r=0;r<2;r=r+1)begin:ROOT
  ot_hbm_sm_aq_static actual(.clk_core(clock_root[3*r]),.clk_delay(clock_root[3*r+1]),.clk_encode(clock_root[3*r+2]),.rst_n(rst_n),.v(v[r]),.x(x[r]),.vo(vo[r]),.q(q[r]),.e(e[r]),.y(y[r]),.fault(fault[r]));
 end
 reg[1023:0]inputs[0:N-1];reg[255:0]gold_q[0:N-1];reg[9:0]gold_e[0:N-1];reg[511:0]gold_y[0:N-1];reg gold_fault[0:N-1];
 reg expected_v[0:1][0:17];integer expected_id[0:1][0:17],issued_at[0:N-1];integer driven_id[0:1];
 integer cycle=0,issued=0,post_outputs=0,consumer_outputs=0,native_outputs=0,nf_outputs=0,bubbles=0,reset_flush_inputs=0;
 task check(input integer root,id,input bit valid_expected,input bit after_nba);
 reg[255:0]observed_q;reg[9:0]observed_e;reg observed_fault;
 begin
  observed_q=MUT==1?q[root]^256'd1:q[root];observed_e=MUT==2?10'(e[root]+10'd1):e[root];observed_fault=MUT==3?1'b0:fault[root];
  if(vo[root]!==valid_expected)$fatal(1,"AQ12 valid observer mismatch root%0d cycle%0d postNBA%0d got%0b expected%0b",root,cycle,after_nba,vo[root],valid_expected);
  if(!valid_expected)begin if(fault[root]!==0)$fatal(1,"AQ12 invalid input poison raised fault");end
  else begin
   if(cycle-issued_at[id]!=(after_nba?17:18))$fatal(1,"AQ12 observed latency convention mismatch");
   if(observed_fault!==gold_fault[id])$fatal(1,"AQ12 nonfinite fault mismatch id%0d root%0d",id,root);
   if(!gold_fault[id])begin
    if(observed_q!==gold_q[id])$fatal(1,"AQ12 raw code mismatch id%0d root%0d got%h expected%h",id,root,observed_q,gold_q[id]);
    if(observed_e!==gold_e[id])$fatal(1,"AQ12 exponent mismatch id%0d root%0d got%0d expected%0d",id,root,$signed(observed_e),$signed(gold_e[id]));
    if(y[root]!==gold_y[id])$fatal(1,"AQ12 dequant BF16 mismatch id%0d root%0d got%h expected%h",id,root,y[root],gold_y[id]);
   end
   if(after_nba)begin post_outputs=post_outputs+1;if(id<1280)native_outputs=native_outputs+1;if(gold_fault[id])nf_outputs=nf_outputs+1;end
   else consumer_outputs=consumer_outputs+1;
  end
 end endtask
 task tick;
 begin
  @(posedge clk);
  if(!rst_n)begin for(integer r=0;r<2;r=r+1)for(integer s=0;s<18;s=s+1)begin expected_v[r][s]=0;expected_id[r][s]=0;end end
  else begin
   for(integer r=0;r<2;r=r+1)check(r,expected_id[r][17],expected_v[r][17],0);
   for(integer r=0;r<2;r=r+1)begin
    for(integer s=17;s>0;s=s-1)begin expected_v[r][s]=expected_v[r][s-1];expected_id[r][s]=expected_id[r][s-1];end
    expected_v[r][0]=v[r];expected_id[r][0]=driven_id[r];
    if(v[r])issued_at[driven_id[r]]=cycle;
   end
  end
  #1;
  if(rst_n)for(integer r=0;r<2;r=r+1)check(r,expected_id[r][17],expected_v[r][17],1);
  else if(vo!==0||fault!==0)$fatal(1,"AQ12 reset did not flush valid/fault");
  cycle=cycle+1;@(negedge clk);
 end endtask
 task idle;
 begin v=0;for(integer r=0;r<2;r=r+1)begin x[r]={32{32'h7fc12345}};driven_id[r]=0;end tick();bubbles=bubbles+1;end endtask
 task pair(input integer base);
 begin v=2'b11;for(integer r=0;r<2;r=r+1)begin x[r]=inputs[base+r];driven_id[r]=base+r;end tick();end endtask
 initial begin
  $readmemh("vectors/x.hex",inputs);$readmemh("vectors/q.hex",gold_q);$readmemh("vectors/e.hex",gold_e);$readmemh("vectors/y.hex",gold_y);$readmemh("vectors/fault.hex",gold_fault);
  x[0]=0;x[1]=0;driven_id[0]=0;driven_id[1]=0;
  repeat(3)tick();rst_n=1;
  // A real reset aborts eight in-flight blocks before the first output.
  for(integer j=0;j<4;j=j+1)pair(j*2);
  rst_n=0;v=0;repeat(2)tick();rst_n=1;repeat(20)idle();reset_flush_inputs=8;
  for(integer j=0;j<1280;j=j+2)begin pair(j);issued=issued+2;end
  for(integer j=1280;j<N;j=j+2)begin if(j%22==0)idle();pair(j);issued=issued+2;end
  repeat(22)idle();
  if(issued!=N||post_outputs!=N||consumer_outputs!=N||native_outputs!=1280||nf_outputs!=24)$fatal(1,"AQ12 missing response inventory issued%0d post%0d consumer%0d native%0d nf%0d",issued,post_outputs,consumer_outputs,native_outputs,nf_outputs);
  $display("AQ12_RAW_STATIC PASS AQs2_clockroots6 nativeP8K5120words40960 blocks1280 fixed_issue_edges640 totalblocks%0d nonfinite24 rawq_e_y_exact finiteblocks%0d postNBA_gap17 downstream_sample_gap18 inclusive_stages18 II1_per_root reset_flushed%0d invalidNaNbubbles%0d",N,N-24,reset_flush_inputs,bubbles);$finish;
 end
 initial begin #100000000;$fatal(1,"AQ12 gate timeout");end
endmodule
