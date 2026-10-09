`timescale 1ns/1ps
module tb_qwen_dspark_argmax_gather;
 parameter integer MUT=0;
 reg clk=0,rst=0,bv=0,orr=0;always #0.555555 clk=~clk;
 reg [63:0] bid=0;reg [7:0] bs=0;reg [3:0] iv=0,ifault=0;
 reg [255:0] ids=0;reg [31:0] seqs=0;reg [71:0] tokens=0;reg [127:0] vals=0;
 wire br,ov,fault;wire [3:0] ready;wire [17:0] token;wire [31:0] val;wire [63:0] oid;wire [7:0] os;
 ot_qwen_dspark_argmax_gather #(.ENABLE(1),.MUT_TIE(MUT)) dut(.clk(clk),.rst_n(rst),.begin_v(bv),.begin_r(br),.begin_id(bid),.begin_seq(bs),
  .i_v(iv),.i_r(ready),.i_id(ids),.i_seq(seqs),.i_token(tokens),.i_value(vals),.i_fault(ifault),.o_v(ov),.o_r(orr),.o_token(token),.o_value(val),.o_id(oid),.o_seq(os),.fault(fault));
 task automatic reset;
  begin @(negedge clk);rst=0;iv=0;bv=0;orr=0;repeat(3)@(negedge clk);rst=1;repeat(3)@(negedge clk);end
 endtask
 task automatic begin_row;
  begin @(negedge clk);if(!br)$fatal(1,"new cohort credit unavailable");bv=1;@(negedge clk);bv=0;end
 endtask
 integer c,step,r,t,cases=0;reg [17:0] expected;reg [31:0] ev;
 initial begin
  reset();
  for(c=0;c<40;c=c+1)begin
   bid=64'habc987fe00000000+64'(c);bs=8'(200+c);begin_row();
   expected=18'((c%5==4)?17:((c%5)*37984+17));ev=(c%5==4)?32'h80000000:32'h40000000;
   for(step=0;step<4;step=step+1)begin
    r=(c%2==0)?3-step:step;
    @(negedge clk);repeat(step%3)@(negedge clk);
    if(!ready[r])$fatal(1,"rank credit unavailable");
    ids[r*64+:64]=bid;seqs[r*8+:8]=bs;tokens[r*18+:18]=18'(r*37984+17);
    vals[r*32+:32]=(c%5==4)?((r%2==0)?32'h80000000:32'b0):((r==c%5)?32'h40000000:32'h3f800000);
    iv=4'b1<<r;@(negedge clk);iv=0;
    if(ready[r])$fatal(1,"rank credit prematurely recycled");
   end
   t=0;while(!ov&&t<10)begin @(negedge clk);t=t+1;end
   if(!ov||fault||token!==expected||val!==ev||oid!==bid||os!==bs)$fatal(1,"crossdie gather mutant/tie/fullidentity failure case=%0d tok=%0d expected=%0d",c,token,expected);
   repeat(6)begin @(negedge clk);if(!ov||ready||br||token!==expected||oid!==bid||os!==bs)$fatal(1,"gather lease unstable during stall");end
   orr=1;@(negedge clk);orr=0;cases=cases+1;
  end
  reset();bid=55;bs=200;begin_row();ids[63:0]=bid;seqs[7:0]=bs-1;tokens[17:0]=17;vals[31:0]=32'h3f800000;iv=1;@(negedge clk);iv=0;@(negedge clk);
  if(!fault||ready||ov)$fatal(1,"stale sequence not quarantined");
  reset();bid=55;bs=200;begin_row();ids[63:0]=bid+1;seqs[7:0]=bs;iv=1;@(negedge clk);iv=0;@(negedge clk);
  if(!fault||ready||ov)$fatal(1,"wrong cohort not quarantined");
  reset();bid=55;bs=200;begin_row();ids[63:0]=bid;seqs[7:0]=bs;tokens[17:0]=131072;iv=1;@(negedge clk);iv=0;@(negedge clk);
  if(!fault||ready||ov)$fatal(1,"cross-rank index alias not quarantined");
  $display("QWEN_ARGMAX_GATHER_PASS cases=%0d all4ranks=1 arrivalorders=2 full64bitID_sequence8=1 lowestID_zero_ties=1 stalledcredit=1 stale_cohort_rank_negative=1",cases);
  $finish;
 end
endmodule
