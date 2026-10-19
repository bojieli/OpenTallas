`timescale 1ns/1ps
module tb;
 reg ck=0; always #5 ck=~ck;
 reg we=0; reg [5:0] wa=0,ra=0;
 reg [547:0] din=0; wire [547:0] q;
 ot_qkvd_llr_replay_four_sf137_private dut(.ck(ck),.we(we),.wa(wa),.ra(ra),.din(din),.dout(q));
 wire [547:0] qold;
 genvar b;
 for(b=0;b<4;b=b+1) begin : g_ref
  ot_qkvd_llr_replay_sram_leaf_sf ref_leaf(.ck(ck),.we(we),.wa(wa),.ra(ra),.din(din[137*b+:137]),.dout(qold[137*b+:137]));
 end
 wire [136:0] mr;
 ot_sram_1r1w_64x137_m1_r2c2_p192 macro_old(.clk(ck),.r_ce_in(1'b1),.r_addr_in(ra),.rd_out(mr),
 .w_ce_in(we),.w_addr_in(wa),.wd_in(din[136:0]),.w_mask_in({137{1'b1}}),
 .rr_en(2'd0),.rr_addr(12'd0),.cr_en(2'd0),.cr_sel(16'd0));
 reg [547:0] mem[0:63]; reg [63:0] known=0;
 reg [547:0] expected,prev_expected,old_expected;
 reg old_known; reg prev_valid=0, prev_we=0; reg [5:0] prev_wa=0;
 integer edges=0, checks=0, h0=0,h1=0,from_macro=0,unwritten=0,collisions=0,firstuses=0;
 integer i,j; reg [547:0] data;
 task step(input reg w,input reg[5:0] a,input reg[5:0] r,input reg[547:0] d);
 begin
  @(negedge ck); we=w;wa=a;ra=r;din=d;
  old_known=known[r]; old_expected=mem[r]; expected=(w && a==r)?d:mem[r];
  if(w && a==r) begin h0=h0+1;collisions=collisions+1; end
  else if(prev_we && prev_wa==r) h1=h1+1;
  else from_macro=from_macro+1;
  if(!known[r] && !(w && a==r)) unwritten=unwritten+1;
  if(w) begin if(!known[a]) firstuses=firstuses+1;mem[a]=d;known[a]=1;end
  @(posedge ck); #1;
  if(prev_valid) begin
`ifndef VERILATOR
   if(q !== prev_expected) $fatal(1,"LEAF_SCOREBOARD edge=%0d expected=%h actual=%h",edges,prev_expected,q);
   if(qold !== prev_expected) $fatal(1,"ORIGINAL_SCOREBOARD edge=%0d",edges);
   if(mr !== old_expected[136:0]) $fatal(1,"MACRO_OLD_COLLISION edge=%0d",edges);
`else
   // This two-state run corroborates edges; four-state first-use evidence comes from Icarus.
   if(q !== qold) $fatal(1,"LEAF_REFERENCE edge=%0d",edges);
   if(old_known && mr !== old_expected[136:0]) $fatal(1,"MACRO_OLD_COLLISION edge=%0d",edges);
`endif
   if(q !== qold) $fatal(1,"LEAF_REFERENCE edge=%0d",edges);
   checks=checks+1;
  end
  prev_expected=expected;prev_valid=1;prev_we=w;prev_wa=a;edges=edges+1;
 end endtask
 initial begin
  for(i=0;i<64;i=i+1) mem[i]='x;
  // No zero-initialized memory assumption: uninitialized observation remains X.
  step(0,0,63,0);step(0,0,63,0);step(0,0,63,0);
`ifndef VERILATOR
  if(!$isunknown(q)) $fatal(1,"NO_INIT_MUST_REMAIN_UNKNOWN");
`endif
  // First publication of every slot; every current-write collision is forwarded.
  for(i=0;i<64;i=i+1) begin
   for(j=0;j<17;j=j+1) data[32*j+:32]=$urandom;
   data[547:544]=$urandom;
   step(1,i,i,data);
  end
  // Previous-write age1, then macro age2; bank identity is deliberately distinct.
  for(i=0;i<64;i=i+1) begin
   data={137'h123456789abcdef,137'h6fedcba987654321,137'h55aa55aa55aa,137'haa55aa55aa55} ^ i;
   step(1,i,(i+7)%64,data);step(0,0,i,0);step(0,0,i,0);step(0,0,i,0);
  end
  // Back-to-back rewrites exercise h0 priority over h1, all 9 groups and bank3 high bit.
  for(i=0;i<1000;i=i+1) begin
   for(j=0;j<17;j=j+1) data[32*j+:32]=$urandom;
   data[547:544]=$urandom;
   if(i%4==0) step(1,i%64,i%64,data);
   else if(i%4==1) step(1,i%64,(i-1)%64,data);
   else step(i%3!=0,i%64,(i*13)%64,data);
  end
  step(0,0,1,0);step(0,0,2,0);
  if(h0<64 || h1<64 || firstuses!=64 || unwritten<3 || from_macro<64) $fatal(1,"COVERAGE_MISSING");
  $display("PASS edges=%0d checks=%0d h0=%0d h1=%0d macro=%0d firstuses=%0d unwritten=%0d collisions=%0d",edges,checks,h0,h1,from_macro,firstuses,unwritten,collisions);
  $finish;
 end
endmodule
