`timescale 1ps/1fs
module tb_exp_recut #(parameter integer N=3846);
 reg clk=0;always #416.666666667 clk=~clk;
 reg rst_n=0,v=0;reg[31:0] x=0;wire[31:0] y;wire vo,fault;
 ot_dsrom_su_softmax_exp_tile #(.LM(11),.LA(11),.NSPLIT(2),.ADDX(0)) dut(.*);
 reg[31:0] inputs[0:N-1],expected[0:N-1],queue[0:N+255];
 integer sent_at[0:N+255];integer cycle=0,wr=0,rd=0,index=0,total=0;
 string input_file,expected_file;
 always @(posedge clk)begin
  cycle=cycle+1;
  if(!rst_n)begin wr=0;rd=0;end
  else begin
   if(v)begin queue[wr]=expected[index];sent_at[wr]=cycle;wr=wr+1;end
   if(vo)begin
    if(rd>=wr)$fatal(1,"SPURIOUS_VALID_AFTER_RESET");
    if(y!==queue[rd])$fatal(1,"EXP_EXACT_MISMATCH index%0d got%08x expected%08x",rd,y,queue[rd]);
    if(cycle-sent_at[rd]!=173)$fatal(1,"EXP_LATENCY got%0d expected173",cycle-sent_at[rd]);
    if(fault)$fatal(1,"EXP_FAULT");
    rd=rd+1;total=total+1;
   end
  end
 end
 task automatic reset;
  @(negedge clk);rst_n=0;v=0;
  repeat(3)@(negedge clk);rst_n=1;
 endtask
 task automatic offer(input integer i);
  @(negedge clk);v=1;index=i;x=inputs[i];
 endtask
 task automatic drain;
  @(negedge clk);v=0;x=32'h7fc00001;
  repeat(175)@(negedge clk);
  if(wr!=rd)$fatal(1,"MISSING_RESULTS sent%0d received%0d",wr,rd);
 endtask
 initial begin
  if(!$value$plusargs("INPUT=%s",input_file)||!$value$plusargs("EXPECTED=%s",expected_file))$fatal(1,"FIXTURE_PATHS");
  $readmemh(input_file,inputs);$readmemh(expected_file,expected);
  reset();
  for(integer i=0;i<N;i=i+1)begin
   offer(i);
   if(i%113==0)begin @(negedge clk);v=0;x=32'h7fc00001;end
  end
  drain();$display("EXP_CONTIGUOUS_PASS vectors%0d latency173 II1",total);
  // Reset aborts in-flight values; no pre-reset result can return into a new row.
  for(integer i=0;i<20;i=i+1)offer(i);
  @(negedge clk);v=0;
  repeat(50)@(negedge clk);reset();
  repeat(175)@(negedge clk);if(rd!=0)$fatal(1,"RESET_LEAK");
  for(integer i=0;i<16;i=i+1)offer(i);
  drain();
  if(total!=N+16)$fatal(1,"COUNT");
  $display("PASS_EXP_RECUT vectors%0d source_bd30aca LM11 LA11 NSPLIT2 ADDX0 core172 tile173 II1 bubbles resetabort exactFP32",total);$finish;
 end
endmodule
