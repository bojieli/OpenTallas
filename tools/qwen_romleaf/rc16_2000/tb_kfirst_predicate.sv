`timescale 1ns/1ps
module tb_kfirst_predicate;
 reg [17:0] k18=0; reg [15:0] k16=0; reg [31:0] k32=0;reg [7:0] k8=0;reg k1=0;
 reg [5:0] split=0;reg wsrc=0;
 wire q18,q16,q32,q8,q1;
 ot_qwen_kfirst_local #(.W(18)) d18(k18,split,wsrc,q18);
 ot_qwen_kfirst_local #(.W(16)) d16(k16,split,wsrc,q16);
 ot_qwen_kfirst_local #(.W(32)) d32(k32,split,wsrc,q32);
 ot_qwen_kfirst_local #(.W(8)) d8(k8,split,wsrc,q8);
 ot_qwen_kfirst_local #(.W(1)) d1(k1,split,wsrc,q1);
 reg [5:0] ma=0,mb=0;reg ms=0,mt=0;wire [5:0] my;
 ot_qwen_a0_mux_slice #(.W(6)) dm(ms,mt,ma,mb,my);
 longint unsigned checks=0;
 reg [31:0] threshold,expected_k;
 integer s,k,w,j,a,b,t;
 task automatic check_one(input reg got,input reg [31:0] v,input integer width);
  reg want;
  begin
   want=wsrc ? (v <= (32'd1 << split)) : (v == 32'd1);
   if(got !== want) $fatal(1,"KFIRST_PREDICATE_FAIL W%0d K%08h split%0d wsrc%0d got%0b want%0b",width,v,split,wsrc,got,want);
   checks=checks+1;
  end
 endtask
 initial begin
  for(a=0;a<64;a=a+1) for(b=0;b<64;b=b+1) for(w=0;w<2;w=w+1) for(t=0;t<2;t=t+1) begin
   mt=1'(t);ma=6'(a);mb=6'(b);ms=1'(w);#1;
   if(my !== ((ms && mt) ? ma : mb)) $fatal(1,"KTOT_MUX_SLICE_FAIL");
  end
  $display("KTOT_MUX_SLICE_PASS exhaustive_pairs4096_enable_pairs4");
  // All W16 and actual production W18 K values, all six-bit shifts (including 32..63), both modes.
  // The real source's split is four bits. This superset checks shift-out too.
  for(s=0;s<64;s=s+1) begin
   split=6'(s);
   for(k=0;k<262144;k=k+1) begin
    k18=18'(k);
    for(w=0;w<2;w=w+1) begin wsrc=1'(w);#1;check_one(q18,{14'd0,k18},18);end
   end
   for(k=0;k<65536;k=k+1) begin
    k16=16'(k);
    for(w=0;w<2;w=w+1) begin wsrc=1'(w);#1;check_one(q16,{16'd0,k16},16);end
   end
   for(k=0;k<256;k=k+1) begin
    k8=8'(k);
    for(w=0;w<2;w=w+1) begin wsrc=1'(w);#1;check_one(q8,{24'd0,k8},8);end
   end
   for(k=0;k<2;k=k+1) begin
    k1=1'(k);
    for(w=0;w<2;w=w+1) begin wsrc=1'(w);#1;check_one(q1,{31'd0,k1},1);end
   end
   threshold=32'd1<<split;
   // Exact threshold boundaries, zero, unsigned sign bit and full-width max.
   for(j=0;j<9;j=j+1) begin
    case(j)
     0:k32=32'd0;1:k32=32'd1;2:k32=32'd2;
     3:k32=32'hffffffff;4:k32=32'h80000000;5:k32=32'h7fffffff;
     6:k32=threshold-32'd1;7:k32=threshold;8:k32=threshold+32'd1;
    endcase
    for(w=0;w<2;w=w+1) begin wsrc=1'(w);#1;check_one(q32,k32,32);end
   end
  end
  if(checks!=41977216) $fatal(1,"unexpected predicate coverage %0d",checks);
  $display("KFIRST_PREDICATE_PASS checks%0d exhaustive_W18_K262144_W16_K65536_split64_modes2 W1_W8_exhaustive W32_unsigned_boundaries",checks);
  $finish;
 end
endmodule
