`timescale 1ns/1ps
// NEW parent query packing/retention gate on immutable archived quant vectors.
// This checks no released SU producer, full scorer, global selection or clock.
module tb_hbm_index_query;
 reg clk=0;always #5 clk=~clk;
 reg por_n=0,start=0,block_v=0,ql_r=0;
 wire start_ready,block_r,ql_v,done,fault;
 reg[4:0] head;reg[1:0] block_number;
 reg[1023:0] data;reg[15:0] weight;
 wire[7:0] qhead;wire[511:0] codes;wire[31:0] scales;wire[15:0] qw;
 ot_hbm_accel_index_query #(.ENABLE(1)) dut(
 .clk(clk),.por_n(por_n),.start(start),.start_ready(start_ready),
 .block_v(block_v),.block_r(block_r),.block_head(head),.block_number(block_number),
 .block_data(data),.head_weight(weight),.ql_v(ql_v),.ql_r(ql_r),.ql_head(qhead),
 .ql_codes(codes),.ql_sc(scales),.ql_w(qw),.done(done),.fault(fault));
 reg[1027:0] input_words[0:127];reg[783:0] expected_words[0:127];
 string ip,ep;
 integer i,b,l,n,frames=0,checked=0,cycles=0;
 reg[511:0] expected_codes,hold_codes;
 reg[31:0] expected_scales,hold_scales;
 reg[7:0] hold_head;
 reg held=0;
 always @(posedge clk)begin
  cycles<=cycles+1;
  if(ql_v)begin
   if(held && ({qhead,scales,codes}!=={hold_head,hold_scales,hold_codes}))
    $fatal(1,"query changed while downstream held");
   held<=!ql_r;hold_head<=qhead;hold_scales<=scales;hold_codes<=codes;
  end else held<=0;
 end
 task automatic check_head;
  integer x,y,idx;reg signed[11:0] e;
  begin
   expected_codes=0;expected_scales=0;
   for(x=0;x<4;x=x+1)begin
    idx=4*n+x;e=expected_words[idx][768+:12];
    if(expected_words[idx][780+:4]!=0)$fatal(1,"archived vector fault");
    expected_scales[8*x+:8]=8'(e+127);
    for(y=0;y<32;y=y+1)expected_codes[128*x+4*y+:4]=expected_words[idx][512+8*y+:4];
   end
   if(qhead!==8'(n)||codes!==expected_codes||scales!==expected_scales||qw!==16'(16'h3f80+n))
    $fatal(1,"native query packing mismatch head=%0d actual=%0d",n,qhead);
   checked=checked+1;
  end
 endtask
 initial begin
  if(!$value$plusargs("INPUT=%s",ip)||!$value$plusargs("EXPECTED=%s",ep))$fatal(1,"cached input paths required");
  $readmemh(ip,input_words);$readmemh(ep,expected_words);
  repeat(3)@(negedge clk);por_n=1;
  for(frames=0;frames<2;frames=frames+1)begin
   @(negedge clk);if(!start_ready)$fatal(1,"no start credit");start=1;
   @(negedge clk);start=0;
   for(i=0;i<128;i=i+1)begin
    while(!block_r)@(negedge clk);
    head=5'(i/4);block_number=2'(i%4);data=input_words[i][1023:0];weight=16'(16'h3f80+i/4);block_v=1;
    @(negedge clk);block_v=0;
    if(i%11==0)@(negedge clk);
    if(fault)$fatal(1,"query fault during accepted blocks");
   end
   // Complete prepaid query remains held while consumer refuses every head.
   repeat(17)@(negedge clk);
   for(n=0;n<32;n=n+1)begin
    while(!ql_v)begin @(negedge clk);if(fault)$fatal(1,"query fault before head");end
    check_head();ql_r=1;@(negedge clk);ql_r=0;
    if(n%3==0)repeat(2)@(negedge clk);
   end
   if(!done||fault)$fatal(1,"missing clean query terminal");
  end
  // Wrong accepted ordinal must fail closed, not publish the next query.
  @(negedge clk);start=1;@(negedge clk);start=0;
  head=1;block_number=0;data=input_words[0][1023:0];weight=16'h3f80;block_v=1;
  @(negedge clk);block_v=0;
  if(!fault||ql_v||block_r||start_ready)$fatal(1,"malformed ordinal not refused");
  $display("PASS_HBM_QUERY_NATIVE_PACKING heads=%0d frames=2 cycles=%0d malformed_refused=1 source_SU_qualified=0",checked,cycles);
  $finish;
 end
endmodule
