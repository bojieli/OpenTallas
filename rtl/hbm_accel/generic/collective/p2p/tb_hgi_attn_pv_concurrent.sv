`timescale 1ns/1ps
`default_nettype none
// Exact full-shape bench of the concurrent Qwen8192 PV tree (ot_hgi_attn_pv_concurrent): 32 SM stager rows x 128
// fixed input edges (2 KV groups x 64 rows = 32 block-slot pairs), 1,024 FP32 outputs. Expected answers only: the
// canonical association quadrant bit0 -> quadrant bit1 -> block slot -> SM bit0 -> SM bit1 -> SM bit2, every add an
// IEEE binary32 RNE (f32add.c). The bench drives rows on its OWN static calendar (start edge + 4 + k), never from DUT
// outputs; it checks every output word, the output edges (exact cycle), done, and that a legal programme never faults.
// SCEN: 0 production, 1 one SM row one edge late (fault expected, outputs keep their edges),
//       2 wrong epoch on one SM (fault expected), 3 back-to-back second start while active (fault expected).
// Mutants (DUT parameters, must FAIL production): MUT_PAIR, MUT_SLOT, MUT_DATA.
module tb_hgi_attn_pv_concurrent;
 parameter integer MUT_PAIR=0,MUT_SLOT=0,MUT_DATA=0,SCEN=0;
 import "DPI-C" function int unsigned f32add(input int unsigned a,input int unsigned b);
 reg clk=0;always #0.5 clk=~clk;
 reg rst_n=0,start=0;
 reg [31:0] row_v=0;reg [32*512-1:0] row_data=0;reg [32*6-1:0] row_sequence=0;reg [32*8-1:0] row_epoch=0;reg [31:0] row_bank=0;
 wire input_slot,expected_bank,out_v,out_group,done,fault;
 wire [5:0] expected_sequence,out_sequence;wire [7:0] expected_epoch,out_epoch;wire [511:0] out_data;
 localparam [7:0] E0=8'h35,E1=8'hc6;
 ot_hgi_attn_pv_concurrent #(.MUT_PAIR(MUT_PAIR),.MUT_SLOT(MUT_SLOT),.MUT_DATA(MUT_DATA)) dut(
  .clk(clk),.rst_n(rst_n),.start(start),.epoch0(E0),.epoch1(E1),.bank0(1'b0),.bank1(1'b1),
  .row_v(row_v),.row_data(row_data),.row_sequence(row_sequence),.row_epoch(row_epoch),.row_bank(row_bank),
  .input_slot(input_slot),.expected_sequence(expected_sequence),.expected_epoch(expected_epoch),.expected_bank(expected_bank),
  .out_v(out_v),.out_data(out_data),.out_sequence(out_sequence),.out_epoch(out_epoch),.out_group(out_group),.done(done),.fault(fault));
 function automatic [31:0] val(input integer s,input integer g,input integer seq,input integer w);
  reg [31:0] x;
  x=32'(s)*32'h9e3779b1 ^ 32'(g)*32'h85ebca77 ^ 32'(seq)*32'hc2b2ae3d ^ 32'(w)*32'h27d4eb2f;
  x=x ^ (x>>15); x=x*32'h2c1b3c6d; x=x ^ (x>>12); x=x*32'h297a2d39; x=x ^ (x>>15);
  return {x[31],8'(100+(x[30:23]%56)),x[22:0]};
 endfunction
 function automatic [31:0] gold(input integer q,input integer t,input integer half,input integer g,input integer p);
  integer w,sm,slot,seq;reg [31:0] a0,a1,b[0:1],s[0:7],t0[0:3],t1[0:1];
  w=8*t+2*(2*(q/2)+(q%2))+half;
  for(sm=0;sm<8;sm=sm+1)begin
   for(slot=0;slot<2;slot=slot+1)begin
    seq=2*p+slot;
    a0=f32add(val(q*8+sm,g,seq,w),val((q^1)*8+sm,g,seq,w));
    a1=f32add(val((q^2)*8+sm,g,seq,w),val(((q^2)^1)*8+sm,g,seq,w));
    b[slot]=f32add(a0,a1);
   end
   s[sm]=f32add(b[0],b[1]);
  end
  for(integer i=0;i<4;i=i+1)t0[i]=f32add(s[2*i],s[2*i+1]);
  for(integer i=0;i<2;i=i+1)t1[i]=f32add(t0[2*i],t0[2*i+1]);
  return f32add(t1[0],t1[1]);
 endfunction
 integer lat=-1,edge_n=0,start_edge=-1,outs=0,words=0,first_out=-1,last_out=-1,done_edge=-1;
 always @(posedge clk) edge_n<=edge_n+1;
 // Bench-side static calendar: row k is presented in the cycle after edge start+4+k (sampled at start+5+k).
 always @(negedge clk) begin
  integer k,kk,g,seq;
  row_v=0;row_data=0;row_sequence=0;row_epoch=0;row_bank=0;
  start=(edge_n==10 || (SCEN==3 && edge_n==60));
  if(start_edge>=0)begin
   k=edge_n-(start_edge+4)-1;
   for(integer s=0;s<32;s=s+1)begin
    kk=(SCEN==1 && s==13)?k-1:k;
    if(kk>=0 && kk<128)begin
     g=kk/64;seq=kk%64;
     row_v[s]=1;row_sequence[s*6+:6]=6'(seq);row_epoch[s*8+:8]=(g?E1:E0)^((SCEN==2 && s==7 && kk==77)?8'h01:8'h00);row_bank[s]=g[0];
     for(integer w=0;w<16;w=w+1)row_data[s*512+w*32+:32]=val(s,g,seq,w);
    end
   end
  end
 end
 always @(posedge clk) if(start && start_edge<0) start_edge<=edge_n;
 always @(posedge clk) if(rst_n && out_v) begin
  integer g,p;
  g=out_group;p=out_sequence/2;
  if(SCEN==0 && out_sequence[0]!==1'b1)$fatal(1,"output on a slot0 edge seq%0d",out_sequence);
  if(SCEN==0 && out_epoch!==(g?E1:E0))$fatal(1,"output epoch");
  // fixed latency from the slot1 row's sample edge: every output must sit at the same offset
  if(lat<0)lat=edge_n-(start_edge+64*g+2*p+1);
  else if(SCEN!=3 && edge_n-(start_edge+64*g+2*p+1)!=lat)$fatal(1,"output edge drifts off the fixed calendar g%0d p%0d",g,p);
  for(integer q=0;q<4;q=q+1)for(integer t=0;t<2;t=t+1)for(integer h=0;h<2;h=h+1)begin
   if(SCEN==0 && out_data[q*128+(2*t+h)*32+:32]!==gold(q,t,h,g,p))
    $fatal(1,"PV word mismatch q%0d t%0d half%0d group%0d pair%0d got %h exp %h",q,t,h,g,p,out_data[q*128+(2*t+h)*32+:32],gold(q,t,h,g,p));
   words=words+1;
  end
  if(first_out<0)first_out<=edge_n;last_out<=edge_n;outs=outs+1;
 end
 always @(posedge clk) if(done && done_edge<0) done_edge<=edge_n;
 initial begin
  repeat(4)@(negedge clk);rst_n=1;
  repeat(400)@(posedge clk);
  if(SCEN==0)begin
   if(fault)$fatal(1,"legal concurrent programme faulted");
   if(outs!=64||words!=1024)$fatal(1,"coverage outs%0d words%0d",outs,words);
   if(done_edge<0)$fatal(1,"no done");
   $display("ATTN_PV_CONCURRENT PASS sms=32 input_edges=128 outputs=%0d fp32_words=%0d start_edge=%0d first_out=+%0d last_out=+%0d done=+%0d runtime_stalls=0 fixed_latency_from_row=%0d",
    outs,words,start_edge,first_out-start_edge,last_out-start_edge,done_edge-start_edge,lat);
  end else begin
   if(!fault)$fatal(1,"scenario %0d not detected",SCEN);
   $display("ATTN_PV_CONCURRENT FAULT PASS scen=%0d outputs=%0d",SCEN,outs);
  end
  $finish;
 end
endmodule
`default_nettype wire
