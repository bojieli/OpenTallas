`timescale 1ns/1ps
module tb;
 reg clk=0,q_word=0;
 reg [511:0] f_hdr=0,q_d=0;
 reg [11:0] f_idx=0;
 reg [9:0] rc=0;
 wire [511:0] reference,legacy;
 wire [511:0] candidate [0:5];
 reference_vehicle r(clk,q_word,f_hdr,q_d,f_idx,rc,reference);
 legacy_vehicle l(clk,q_word,f_hdr,q_d,f_idx,rc,legacy);
 candidate_0 c0(clk,q_word,{f_hdr[448],f_idx[6:4]},q_d,4'(rc-10'd1),candidate[0]);
 candidate_1 c1(clk,q_word,{f_hdr[448],f_idx[6:4]},q_d,4'(rc-10'd1),candidate[1]);
 candidate_2 c2(clk,q_word,{f_hdr[448],f_idx[6:4]},q_d,4'(rc-10'd1),candidate[2]);
 candidate_3 c3(clk,q_word,{f_hdr[448],f_idx[6:4]},q_d,4'(rc-10'd1),candidate[3]);
 candidate_4 c4(clk,q_word,{f_hdr[448],f_idx[6:4]},q_d,4'(rc-10'd1),candidate[4]);
 candidate_5 c5(clk,q_word,{f_hdr[448],f_idx[6:4]},q_d,4'(rc-10'd1),candidate[5]);
 reg [511:0] gold [0:15];
 reg [15:0] known=0,lifetime=0,heads_seen=0;
 integer mode=0,checks=0,qualified=0,collisions=0,wraps=0,edges=0,j,h,b,k;
 function automatic [511:0] word(input integer job,input integer head,input integer salt);
   integer n;
   for(n=0;n<16;n=n+1) word[32*n +:32]=32'hb1350001 ^ (32'(job)<<20) ^ (32'(head)<<12) ^ (32'(n)<<4) ^ 32'(salt);
 endfunction
 task automatic edge_check(input bit wr,input integer wh,input integer rh,input bit use_word,input integer job,input integer salt);
   reg [511:0] expected; bit check;
   begin
    clk=0; q_word=wr; f_hdr='0; f_hdr[448]=1'(wh>>3); f_idx=12'((wh & 7)<<4);
    q_d=word(job,wh,salt); rc=10'(rh+1); #2;
    expected=gold[rh]; check=known[rh];
    if(use_word && !lifetime[rh]) $fatal(1,"LIFETIME_FAIL edge=%0d head=%0d",edges,rh);
    if(wr && wh==rh && check) collisions++;
    clk=1; #2;
    if(check) begin
      if(reference !== expected || legacy !== expected) $fatal(1,"LEGACY_FAIL edge=%0d head=%0d",edges,rh);
      if(candidate[mode] !== expected) $fatal(1,"QMEM_DATA_FAIL mode=%0d edge=%0d head=%0d collision=%0d got=%h expected=%h",mode,edges,rh,wr && wh==rh,candidate[mode][63:0],expected[63:0]);
      checks++;
    end
    if(use_word) begin qualified++; heads_seen[rh]=1'b1; end
    if(wr) begin gold[wh]=q_d; known[wh]=1; lifetime[wh]=1; end
    edges++; clk=0; #1;
   end
 endtask
 initial begin
   if(!$value$plusargs("mode=%d",mode)) mode=0;
   // OT_MEM_NO_INIT plus runtime random reset2 seeds all physical payload;
   // no comparison relies on initial payload or a zero-initialized memory.
   for(k=0;k<11;k++) edge_check(0,0,k%16,0,0,0);
   for(j=1;j<=3;j++) begin
     lifetime=0; // actual parent reset/job-start invalidates valid/q_have, not payload
     for(h=0;h<16;h++) begin
       edge_check(1,h,15,0,j,17*j);
       if(h%3==0) edge_check(0,0,15,0,j,0);
     end
     if(lifetime!==16'hffff) $fatal(1,"LOAD_FAIL");
     // Exact rc1..16 q read schedule, repeated across address15->0 wrap.
     for(k=0;k<4;k++) begin
       for(h=0;h<16;h++) edge_check(0,0,h,1,j,0);
       wraps++;
     end
     // Rewrites exercise read-old on the SAME edge, then new on the next.
     for(h=0;h<16;h++) begin
       edge_check(1,h,h,1,j,16'h77a0+h);
       edge_check(0,0,h,1,j,0);
     end
     if(j==1) begin
       lifetime=0; // occupied reset: output payload retained, consume disabled
       for(h=0;h<16;h++) edge_check(0,0,h,0,j,0);
     end
   end
   if(heads_seen!==16'hffff || collisions<48 || wraps<12 || qualified<288) $fatal(1,"COVERAGE_FAIL");
   $display("QMEM8_PASS mode=%0d edges=%0d data_checks=%0d qualified=%0d nonzero_heads=16 OLD_collisions=%0d wraps=%0d jobs=3 occupied_reset=1",mode,edges,checks,qualified,collisions,wraps);
   $finish;
 end
endmodule
