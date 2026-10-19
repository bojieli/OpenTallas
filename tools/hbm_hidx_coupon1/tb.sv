module tb;
 reg clk=0;reg[15:0]lane_v=0;reg[287:0]payload=0;
 wire[287:0]compacted;wire[575:0]pair_select;wire[1439:0]quad_select;
 `ifndef MUT
 `define MUT 0
 `endif
 hidx_coupon1 #(.ENABLE(1),.MUT(`MUT))dut(.*);
 integer m,k,s,j,c,z,b,checks=0;reg[287:0]expected;reg[15:0]old_mask;
 reg[31:0]rng=32'h87a1524d;
 task tick;begin #2;clk=1;#2;clk=0;#1;end endtask
 task check_compact;
 begin
  expected=0;s=0;
  // Independent stable append reference: no prefix count/onehot equations.
  for(k=0;k<8;k=k+1)if(lane_v[k])begin expected[s*36+:36]=payload[k*36+:36];s=s+1;end
  tick;
  if(compacted!==expected)$fatal(1,"COMPACT_ORDER_PREFIX_COPY_FAIL mutant=%0d mask=%h got=%h expected=%h",`MUT,lane_v,compacted,expected);
  checks=checks+1;
 end endtask
 initial begin
  // Exhaustive masks, zero + every payload basis. Exact basis proof of the
  // mask-controlled OR network, with no arithmetic assumptions about payload.
  for(m=0;m<256;m=m+1)begin
   lane_v=m;payload=0;check_compact;
   for(b=0;b<288;b=b+1)begin payload=0;payload[b]=1'b1;check_compact;end
  end
  // Exhaust all 16-bit pair-of-groups mask operands at the actual two edges.
  // Each cohort's 24 selectors and every slice are checked, not a sampled copy.
  for(m=0;m<65536;m=m+1)begin
   lane_v=m;
   for(k=0;k<9;k=k+1)begin rng=rng^(rng<<13);rng=rng^(rng>>17);rng=rng^(rng<<5);payload[k*32+:32]=rng;end
   check_compact;tick;
   s=0;j=0;for(k=0;k<16;k=k+1)begin if(lane_v[k])j=j+1;if(k<8&&lane_v[k])s=s+1;end
   for(c=0;c<6*24;c=c+1)if(pair_select[c*4+:4]!==4'(s))$fatal(1,"PAIR_COUNT_COPY_FAIL mask=%h owner=%d count=%d expected=%d",lane_v,c,pair_select[c*4+:4],s);
   for(c=0;c<12*24;c=c+1)if(quad_select[c*5+:5]!==5'(j))$fatal(1,"QUAD_COUNT_COPY_FAIL mask=%h owner=%d",lane_v,c);
   checks=checks+432;
  end
  $display("PASS full_masks=65536 compaction_masks=256 payload_basis=288 slices=9 pair_copies=144 quad_copies=288 checks=%0d",checks);$finish;
 end
endmodule
