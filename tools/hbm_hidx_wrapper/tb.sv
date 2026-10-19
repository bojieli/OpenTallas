module tb;
 reg clk=0;reg[15:0]lane_v;reg[287:0]payload;
 wire[287:0]compacted;wire[575:0]pair_select;wire[1439:0]quad_select;
 `ifndef MUT
 `define MUT 0
 `endif
 hidx_registered_coupon #(.ENABLE(1),.MUT(`MUT))dut(.*);
 reg[287:0]expected,prior;reg[3:0]pc,prevpc;reg[4:0]qc,prevqc;
 reg[31:0]rng=32'h87a1524d;integer m,k,s,c,checks=0;
 initial begin
  // Deliberately do NOT initialize unreset DUT registers or mask cold outputs.
  for(m=0;m<65538;m=m+1)begin
   lane_v=(m==0)?16'hffff:(m==1)?16'h0000:16'(m-2);
   for(k=0;k<9;k=k+1)begin rng=rng^(rng<<13);rng=rng^(rng>>17);rng=rng^(rng<<5);payload[k*32+:32]=rng;end
   expected=0;s=0;pc=0;qc=0;
   for(k=0;k<16;k=k+1)begin
    if(lane_v[k])qc=qc+1;
    if(k<8&&lane_v[k])begin pc=pc+1;expected[s*36+:36]=payload[k*36+:36];s=s+1;end
   end
   #2;clk=1;#2;
   // First input E1 has no output requirement; E2 and every edge thereafter
   // must publish the previous sample, with a new sample admitted each edge.
   if(m>=1)begin
    if(compacted!==prior)$fatal(1,"S1_CAPTURE_AGE_FAIL sample=%0d mutant=%0d got=%h expected=%h",m-1,`MUT,compacted,prior);
    for(c=0;c<144;c=c+1)if(pair_select[c*4+:4]!==prevpc)$fatal(1,"PAIR_AGE_FAIL sample=%0d copy=%0d",m-1,c);
    for(c=0;c<288;c=c+1)if(quad_select[c*5+:5]!==prevqc)$fatal(1,"QUAD_AGE_FAIL sample=%0d copy=%0d",m-1,c);
    checks=checks+2304;
   end
   clk=0;#1;prior=expected;prevpc=pc;prevqc=qc;
  end
  $display("PASS cold_priming_edges=2 sustained_ii=1 admitted=65538 checked_samples=65537 output_bits_per_sample=2304 bit_checks=%0d",checks);$finish;
 end
endmodule
