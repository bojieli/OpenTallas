`timescale 1ns/1ps
module tb_hgi_qdq_fr_pin_capture;
 parameter integer MUT_ORDER=0,MUT_END=0;
 reg clk=0;always #1 clk=~clk;
 reg rst_n=0;reg [682:0] rec=0;
 wire av,v,fault,rv,ra,rf,gv,ga,gf;wire [189:0] s,rs,gs;
 ot_hgi_qdq_fr_pin_capture #(.PIN_CAPTURE(1),.MUT_ORDER(MUT_ORDER),.MUT_END(MUT_END)) dut(.clk(clk),.rst_n(rst_n),.rec(rec),.s1_v(av),.s3_v(v),.s3(s),.nfault(fault));
 // Mathematical reference retains the original full-width span calculation.
 ot_hgi_qdq_fr #(.SPANPIPE(0)) reference(.clk(clk),.rst_n(rst_n),.rec(rec),.s1_v(ra),.s3_v(rv),.s3(rs),.nfault(rf));
 ot_hgi_qdq_fr #(.SPANPIPE(1)) closed(.clk(clk),.rst_n(rst_n),.rec(rec),.s1_v(ga),.s3_v(gv),.s3(gs),.nfault(gf));
 reg [189:0] expected[0:8191];
 integer wp=0,rp=0,gp=0,checked=0,gchecked=0,cycles=0,maxcount=0,errors=0;
 reg fast_phase=0;
 always @(negedge clk) begin
  #0.1;
  cycles=cycles+1;
  if(!rst_n) begin wp=0;rp=0;gp=0;end
  else if(cycles>12) begin
   if(rv) begin expected[wp]=rs;wp=wp+1;end
   if(v) begin
    if(rp>=wp || s!==expected[rp]) begin $display("MIX mismatch cycle=%0d idx=%0d got=%h want=%h",cycles,rp,s,expected[rp]);errors=errors+1;end
    rp=rp+1;checked=checked+1;
   end
   if(gv) begin
    if(gp>=wp || gs!==expected[gp]) begin $display("GENERAL reference mismatch %0d",gp);errors=errors+1;end
    gp=gp+1;gchecked=gchecked+1;
   end
   if(fast_phase && (v!==rv || (v && s!==rs))) begin $display("FAST_EDGE mismatch cycle=%0d",cycles);errors=errors+1;end
   if(av!==ra || av!==ga || fault!==rf || fault!==gf) begin $display("ACCEPT/FAULT mismatch cycle=%0d",cycles);errors=errors+1;end
   if(dut.g_mix.u_retire.count>maxcount)maxcount=dut.g_mix.u_retire.count;
   if(dut.g_mix.u_retire.count>16)begin $display("OVERFLOW");errors=errors+1;end
  end
 end
 task automatic drive(input integer i,input integer fastonly);
 reg [255:0] a,o;reg [127:0] h;reg [19:0] n,m;reg [39:0] base;
 begin
  @(negedge clk);
  a=0;o=0;h=0;n=32*(1+i%8);m=fastonly?1:(i%3==0?1:1+i%7);
  base=40'(i*512%16384);
  a[1:0]=1;o[1:0]=1;a[47:8]=base;o[47:8]=base+40'd65536;
  a[67:48]=n;o[67:48]=n;a[87:68]=m;o[87:68]=m;
  a[119:88]=256;o[119:88]=256;
  h[127:124]=4;h[123:118]=4+i%3;h[99:93]=7'b0010001;h[71:64]=16;
  if(!fastonly)case(i%17)
   0:begin a[87:68]=20'hfffff;o[87:68]=20'hfffff;a[119:88]=32'hffffffff;o[119:88]=32'hffffffff;end
   1:begin a[87:68]=0;o[87:68]=0;end
   2:begin o[87:68]=m+1;end
   3:begin a[47:8]=262136;o[47:8]=262136;end
   4:begin o[47:8]=base+8;end
   5:begin a[5]=1;end
   6:begin a[135:120]=3;end
   7:begin a[119:88]=7;o[119:88]=13;end
   8:begin h[127:124]=0;end
   9:begin o[47:8]=base;o[119:88]=a[119:88];end
   default:begin end
  endcase
  rec={21'(n),21'(n),o,a,h,1'b1};
 end endtask
 task automatic drain;
 begin @(negedge clk);rec=0;repeat(24)@(negedge clk);#0.2;
  if(rp!=wp || gp!=wp)begin $display("DRAIN mismatch wp=%0d rp=%0d gp=%0d",wp,rp,gp);errors=errors+1;end
 end endtask
 initial begin
  repeat(10)@(negedge clk);rst_n=1;repeat(10)@(negedge clk);
  fast_phase=1;for(integer i=0;i<96;i=i+1)drive(i,1);drain();fast_phase=0;
  for(integer i=0;i<1024;i=i+1)drive(i,0);drain();
  // Warm reset with accepted fast and general records still in flight.
  for(integer i=0;i<12;i=i+1)drive(i,0);
  @(negedge clk);rst_n=0;rec=0;repeat(12)@(negedge clk);
  rst_n=1;repeat(12)@(negedge clk);#0.2;
  if(v || gv || rv || av || fault)begin $display("RESET_STALE");errors=errors+1;end
  for(integer i=0;i<1024;i=i+1)drive(i+100,0);drain();
  drive(2,1);@(negedge clk);rec[661:641]=21'd999;
  repeat(20)@(negedge clk);#0.2;
  if(!fault)begin $display("FAULT_NOT_LATCHED");errors=errors+1;end
  rec=0;repeat(20)@(negedge clk);
  if(errors)$fatal(1,"FAIL QDQ_FR_PIN_CAPTURE checked=%0d errors=%0d",checked,errors);
  $display("PASS QDQ_FR_PIN_CAPTURE checked=%0d general=%0d max_inflight=%0d fast_matches_original_edge=1 warm_reset=1",checked,gchecked,maxcount);$finish;
 end
endmodule
