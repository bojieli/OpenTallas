`timescale 1ns/1ps
// Minimum production-shaped regional endpoint vehicle: full NB80 windows,
// four credit lanes, deterministic skew, both copies, land/replay, payload/tag.
module tb_s81sl_lepab_rxlocal;
 parameter integer SEED=1;
 reg clk=0;always #0.4167 clk=~clk;
 // Fixed phase offsets, same epoch and frequency, within the D4/K2 contract.
 reg ca=0,cb=0;
 initial begin #0.08;forever #0.4167 ca=~ca;end
 initial begin #0.16;forever #0.4167 cb=~cb;end
 reg rn=0;
 // Exact HEAD parent topology: different same-age tree3 leaves feed core and
 // local lane replicas. Reference reads the ORIGINAL real u_core.rxv producer.
 wire [2:0] pc,pa,pb;
 ot_rst_relay_tree3 #(.REGIONS(3)) p_c(.clk(clk),.rst_n_in(rn),.rst_n(pc));
 ot_rst_relay_tree3 #(.REGIONS(3)) p_a(.clk(ca),.rst_n_in(rn),.rst_n(pa));
 ot_rst_relay_tree3 #(.REGIONS(3)) p_b(.clk(cb),.rst_n_in(rn),.rst_n(pb));

 reg [1103:0] ro=0,mrd=0;
 reg [33:0] mc=0;
 reg mrv=0;
 wire [1103:0] ri,mwd;
 wire [31:0] rt;
 wire mwv,fault;
 wire [3:0] lv,lr,iv,ir;
 wire [2211:0] ld,id;
 wire [3:0] rxv;
 ot_s81sl_lep_mu_ab_regional_r3r_rxlocal dut(.clk(clk),.clk_a(ca),.clk_b(cb),.rst_n(pc[0]),.rst_n_a(pa[2]),.rst_n_b(pb[2]),.ro(ro),.ri(ri),
  .mu_c(mc),.mu_rt(rt),.ml_wv(mwv),.ml_wd(mwd),.ml_rv(mrv),.ml_rd(mrd),.ml_f(1'b0),.sl_f(1'b0),
  .lo0_v(lv[0]),.lo0_r(lr[0]),.lo0_d(ld[0+:553]),.li0_v(iv[0]),.li0_r(ir[0]),.li0_d(id[0+:553]),
  .lo1_v(lv[1]),.lo1_r(lr[1]),.lo1_d(ld[553+:553]),.li1_v(iv[1]),.li1_r(ir[1]),.li1_d(id[553+:553]),
  .lo2_v(lv[2]),.lo2_r(lr[2]),.lo2_d(ld[1106+:553]),.li2_v(iv[2]),.li2_r(ir[2]),.li2_d(id[1106+:553]),
  .lo3_v(lv[3]),.lo3_r(lr[3]),.lo3_d(ld[1659+:553]),.li3_v(iv[3]),.li3_r(ir[3]),.li3_d(id[1659+:553]),
  .l0_f(3'd0),.l1_f(3'd0),.l2_f(3'd0),.l3_f(3'd0),.fault(fault));
 // Four local producers use their own lane's same-age parent leaf.
 ot_s81hd_lane_rx_enable_local le0(.ck(ca),.rst_n(pa[0]),.enable(rxv[0]));
 ot_s81hd_lane_rx_enable_local le1(.ck(ca),.rst_n(pa[1]),.enable(rxv[1]));
 ot_s81hd_lane_rx_enable_local le2(.ck(cb),.rst_n(pb[0]),.enable(rxv[2]));
 ot_s81hd_lane_rx_enable_local le3(.ck(cb),.rst_n(pb[1]),.enable(rxv[3]));
 integer cap_a=0,cap_b=0,rx_bad_a=0,rx_bad_b=0,rise_a=0,rise_b=0,fall_a=0,fall_b=0;
 reg [1:0] prev_a=0,prev_b=0;
 always @(negedge ca) begin
  #0.001;cap_a=cap_a+1;
  if(rxv[1:0] !== dut.g_pair[0].pair_rxv) rx_bad_a=rx_bad_a+1;
  if(prev_a==0 && dut.g_pair[0].pair_rxv==3) rise_a=rise_a+1;
  if(prev_a==3 && dut.g_pair[0].pair_rxv==0) fall_a=fall_a+1;
  prev_a=dut.g_pair[0].pair_rxv;
 end
 always @(negedge cb) begin
  #0.001;cap_b=cap_b+1;
  if(rxv[3:2] !== dut.g_pair[1].pair_rxv) rx_bad_b=rx_bad_b+1;
  if(prev_b==0 && dut.g_pair[1].pair_rxv==3) rise_b=rise_b+1;
  if(prev_b==3 && dut.g_pair[1].pair_rxv==0) fall_b=fall_b+1;
  prev_b=dut.g_pair[1].pair_rxv;
 end
 // Off-die PHY and elastic queue are reduced to a deterministic codec echo.
 // Credit returns after consumption; lane1/3 skew creates real RX occupancy.
 integer sent[4],returned[4],credit[4];
 for(genvar l=0;l<4;l=l+1) begin:g_echo
  wire ck=(l<2)?ca:cb;
  localparam integer D=(l%2==0)?3:7;
  reg [D-1:0] v=0;
  reg [552:0] d[0:D-1];
  reg cr=0;
  always @(posedge ck) begin
   if(!rn) begin v<=0;cr<=0;sent[l]<=0;returned[l]<=0;credit[l]<=0;end
   else begin
    v[0]<=lv[l];cr<=lv[l];
    for(integer j=1;j<D;j=j+1) v[j]<=v[j-1];
    if(lv[l]) sent[l]<=sent[l]+1;
    if(v[D-1]) returned[l]<=returned[l]+1;
    if(ir[l]) credit[l]<=credit[l]+1;
   end
   d[0]<=ld[553*l+:553];
   for(integer j=1;j<D;j=j+1) d[j]<=d[j-1];
  end
  assign lr[l]=cr;assign iv[l]=v[D-1];assign id[553*l+:553]=d[D-1];
 end
 reg [1103:0] qr[0:1023],qw[0:1023];
 reg [31:0] qt[0:1023];
 integer nr=0,nw=0,ar=0,aw=0,bad=0,cycle=0,first=-1,last=-1;
 always @(posedge clk) begin
  cycle<=cycle+1;
  if(ri[0]) begin
   if(first<0) first=cycle;last=cycle;
   if(ar>=nr || ri!==qr[ar] || rt!==qt[ar]) begin
    bad=bad+1;if(bad<8)$display("MISMATCH RI n%0d cyc%0d got%h rt%h exp%h rt%h",ar,cycle,ri[63:0],rt,qr[ar][63:0],qt[ar]);
   end
   ar=ar+1;
  end
  if(mwv) begin
   if(aw>=nw || mwd!==qw[aw]) begin bad=bad+1;if(bad<8)$display("MISMATCH LAND n%0d cyc%0d",aw,cycle);end
   aw=aw+1;
  end
 end
 function automatic [1103:0] payload(input integer u,b);
  reg [1103:0] q;
  begin
   for(integer k=0;k<34;k=k+1) q[32*k+:32]=32'(SEED*16777619+u*65537+b*1021+k*31);
   q[1103:1088]=16'(b*17+u);q[3:0]=4'b0101; q[1077:1045]=0;payload=q;
  end
 endfunction
 task automatic window(input integer u,input bit copy_b,land);
  reg [1103:0] q,stamped;
  begin
   @(negedge clk);mc={21'(100+u),10'(u),land,copy_b,1'b1};
   @(negedge clk);mc=0;
   for(integer b=0;b<80;b=b+1) begin
    q=payload(u,b);stamped=q;stamped[1045+:33]={21'(100+u),10'(u),land,1'b1};
    if(land) begin qw[nw]=stamped;nw=nw+1;end
    else begin qr[nr]=q;qt[nr]={1'b1,10'(u),21'(100+u)};nr=nr+1;end
    ro=q;
    @(negedge clk);ro=0;
    // 3/5 production stream, bounded exactly:80beats/133edges.
    if(b%3!=2) @(negedge clk);
   end
   ro=0;
   repeat(220) @(negedge clk);
  end
 endtask
 initial begin
  repeat(20) @(negedge clk);rn=1;
  repeat(100) @(negedge clk);
  window(0,0,0);window(1,1,1);window(2,0,0);window(3,1,0);window(4,0,1);window(5,1,0);
  repeat(200) @(negedge clk);
  // Central landing replay stays local; source-tag stripping and rt age checked.
  for(integer b=0;b<80;b=b+1) begin
   qr[nr]=payload(1,b);qt[nr]={1'b1,10'd1,21'd101};nr=nr+1;
   mrd=qw[b];mrv=1;
   @(negedge clk);
  end
  mrv=0;mrd=0;
  repeat(100) @(negedge clk);
  for(integer l=0;l<4;l=l+1) begin
   if(sent[l]!=returned[l] || sent[l]!=credit[l]) bad=bad+1;
   $display("LANE %0d tx%0d echo%0d rxcredit%0d",l,sent[l],returned[l],credit[l]);
  end
  if(ar!=nr || aw!=nw || fault || bad) begin
   $display("FAIL lepab_regional: received%0d/%0d landed%0d/%0d bad%0d fault%0b",ar,nr,aw,nw,bad,fault);$finish;
  end
  // Same-source protocol error: copy B user0 must latch a fault.
  mc={21'd7,10'd0,1'b0,1'b1,1'b1};@(negedge clk);mc=0;
  repeat(30) @(negedge clk);
  if(!fault) begin $display("FAIL lepab_rxlocal: missing illegal-copy fault");$finish;end
  // Reassert between clock edges and capture both regions through reset again.
  #0.071;rn=0;repeat(3) @(negedge clk);rn=1;
  repeat(30) @(negedge clk);
  if(rx_bad_a || rx_bad_b || rise_a!=2 || rise_b!=2 || fall_a!=1 || fall_b!=1)
   $display("FAIL lepab_rxlocal: mismatchA%0d mismatchB%0d rise%0d/%0d fall%0d/%0d",rx_bad_a,rx_bad_b,rise_a,rise_b,fall_a,fall_b);
  else $display("PASS lepab_rxlocal: received%0d landed%0d NB80 first%0d last%0d capturedA%0d capturedB%0d reset_reassert1 rises2/2 falls1/1 mismatch0",ar,aw,first,last,cap_a,cap_b);
  $finish;
 end
 initial begin #100000; $display("FAIL lepab_regional: timeout");$finish;end
endmodule
