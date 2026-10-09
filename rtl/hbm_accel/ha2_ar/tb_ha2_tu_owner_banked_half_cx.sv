// REVIEW53 full failed shape, actual 833.333334ps fast period.
`timescale 1ps/1fs
// Exact gate for ot_ha2_tu_owner_banked against the unchanged TU adapter
// (ot_ha2_tu_owner_adapter_item9_cuts CUTS=0 -> ot_ha2_owner_reduce_runtime,
// SLOTREG=1) at the DS TP-96 shape (NC 8, PFMAX 384, LANES 16, INJ 2, NPT 8).
// Same per-port flit streams feed both: the reference pops a receive FIFO head
// whenever present (as the native caller does), the banked DUT only when its
// registered p_r allows. Own partials follow the native caller's (k, k+1)
// injection order and reach both on the same edges. Results must match in
// order and bits; dupe must stay low; both must be quiet at the end.
// Scenarios: S0 PF 64 column-mapped ports, S1 PF 384 column-mapped, S2 PF 384
// random port per flit (column contention + backpressure), S3 PF 384 random,
// with throttled pops. Negative controls (+NEG=n): 1 duplicate peer flit,
// 2 flit index >= OF, 3 foreign destination: each must raise dupe in the DUT.
// MUTANT builds (-GMUT=1 read-address mutant, -GMUT=2 dupe check removed with
// +NEG=1) must FAIL.
module tb_ha2_tu_owner_banked_half_cx;
 parameter integer PHASE_MUT=0;
 parameter integer LANDING=1;
 parameter integer MUT=0;
 parameter integer PQ=0;
 parameter integer HALF=1;
 localparam integer NC=8,PFMAX=384,LANES=16,FW=512,PWT=FW+33,NPT=8,INJ=2;
 localparam [7:0] RANK=8'd19;localparam integer J=19%8;
 reg clk=0;always #416.666667 clk=~clk;
 reg rst_n=0,active=0,arm=0;reg [15:0] pf=64;
 reg [INJ-1:0] hv=0;reg [INJ*(32+FW)-1:0] hd=0;
 reg [NPT-1:0] rpv=0,dpv=0;reg [NPT*PWT-1:0] rpd=0,dpd=0;
 wire [NPT-1:0] p_r;wire [INJ-1:0] h_r;
 wire dv,ddup,dis,dq;wire [15:0] dm;wire [FW-1:0] dd;
 wire rv,rdup,ris,rq;wire [15:0] rm;wire [FW-1:0] rd;
 if(HALF)begin:g_half
  ot_ha2_tu_owner_banked_half_cx #(.MUTANT(MUT),.PQREG(PQ),.LANDING(LANDING),.MUT_PHASE(PHASE_MUT)) dut(.clk(clk),.rst_n(rst_n),.active(active),.arm(arm),.rank(RANK),.pf(pf),
   .h_v(hv),.h_d(hd),.h_r(h_r),.p_v(dpv),.p_flit(dpd),.p_r(p_r),.r_v(dv),.r_m(dm),.r_d(dd),.dupe(ddup),.issue_o(dis),.quiet(dq));
 end else begin:g_full
  assign h_r={INJ{1'b1}};
  ot_ha2_tu_owner_banked #(.MUTANT(MUT),.PQREG(PQ)) dut(.clk(clk),.rst_n(rst_n),.active(active),.arm(arm),.rank(RANK),.pf(pf),
   .h_v(hv),.h_d(hd),.p_v(dpv),.p_flit(dpd),.p_r(p_r),.r_v(dv),.r_m(dm),.r_d(dd),.dupe(ddup),.issue_o(dis),.quiet(dq));
 end
 ot_ha2_tu_owner_adapter_item9_cuts #(.CUTS(0),.NC(NC),.PFMAX(PFMAX),.LANES(LANES),.INJ(INJ),.NPT(NPT),.SLOTREG(1)) ref_dut(
  .clk(clk),.rst_n(rst_n),.active(active),.arm(arm),.rank(RANK),.pf(pf),.h_v(hv),.h_d(hd),.p_v(rpv),.p_flit(rpd),
  .r_v(rv),.r_m(rm),.r_d(rd),.dupe(rdup),.issue_o(ris),.quiet(rq));
 // per-port streams
 localparam integer SMAX=400;
 reg [PWT-1:0] st[0:NPT-1][0:SMAX-1];integer sn[0:NPT-1],rh[0:NPT-1],dh[0:NPT-1];
 // results
 reg [15:0] Rm[0:255],Dm[0:255];reg [FW-1:0] Rd[0:255],Dd[0:255];integer rn=0,dn=0;
 integer cyc=0,first_issue_r=-1,first_issue_d=-1,last_r=-1,last_d=-1,stall=0;
 integer seed=1,thr=0;reg feeding=0;
 // Service coverage at the actual shell/core boundary, in fast edges. These
 // counters are bench observations, not hardware control or protection state.
 integer last_pop[0:NPT-1],pop_count=0,pair_count=0;
 initial for(integer p=0;p<NPT;p=p+1)last_pop[p]=-1;
 if(HALF)begin:g_cadence
  always @(negedge clk)if($test$plusargs("TRACE")&&cyc<160)
   $display("TRACE c=%0d ph=%b act=%b/%b arm=%b/%b core_act=%b core_arm=%b pf=%0d pv=%h hv=%h cnt=%h/%h pr=%h run=%b core_pf=%0d dupe=%b",
    cyc,g_half.dut.ph,active,g_half.dut.act_f,arm,g_half.dut.arm_s,
    g_half.dut.core_act,g_half.dut.core_arm,g_half.dut.core_pf,
    g_half.dut.p_head_v,g_half.dut.h_head_v,g_half.dut.p_cnt,g_half.dut.h_cnt,
    g_half.dut.core_pr,g_half.dut.u_core.run,g_half.dut.u_core.PF_q,ddup);
  always @(posedge clk)if(rst_n&&g_half.dut.ph)begin
   for(integer p=0;p<NPT;p=p+1)if(g_half.dut.p_head_v[p])begin
    if(last_pop[p]>=0)begin
     if(cyc-last_pop[p]<2)$fatal(1,"owner consumed twice within two fast edges");
     if(cyc-last_pop[p]==2)pair_count=pair_count+1;
    end
    last_pop[p]=cyc;pop_count=pop_count+1;
   end
  end
 end
 always @(posedge clk)begin
  cyc=cyc+1;
  if(rv)begin Rm[rn]=rm;Rd[rn]=rd;rn=rn+1;last_r=cyc;end
  if(dv)begin Dm[dn]=dm;Dd[dn]=dd;dn=dn+1;last_d=cyc;end
  if(ris&&first_issue_r<0)first_issue_r=cyc;
  if(dis&&first_issue_d<0)first_issue_d=cyc;
 end
 // port drivers (negedge): pop heads
 always @(negedge clk)begin
  rpv=0;dpv=0;
  if(feeding)for(integer p=0;p<NPT;p=p+1)begin
   if(rh[p]<sn[p]&&(thr==0||$urandom(seed+p+cyc)%3!=0))begin rpv[p]=1;rpd[p*PWT+:PWT]=st[p][rh[p]];rh[p]=rh[p]+1;end
   if(dh[p]<sn[p]&&p_r[p]&&(thr==0||$urandom(seed+7*p+cyc)%3!=1))begin dpv[p]=1;dpd[p*PWT+:PWT]=st[p][dh[p]];dh[p]=dh[p]+1;end
   else if(dh[p]<sn[p]&&!p_r[p])stall=stall+1;
  end
 end
 function automatic [31:0] rnd32(input integer a);
  reg [31:0] x;x=$urandom(a);
  // finite values with a spread of exponents, including cancellation pairs
  rnd32={x[31],1'b0,x[29:26]==0?4'b0111:{1'b1,x[28:26]},x[25:0]};
 endfunction
 function automatic [PWT-1:0] flit(input integer c,fl,input [7:0] dst,input integer sd);
  reg [FW-1:0] d;
  for(integer l=0;l<LANES;l=l+1)d[32*l+:32]=rnd32(sd*131+l*7+c*1009+fl*17);
  flit={1'b0,dst,8'(c),16'(fl),d};
 endfunction
 task automatic transaction(input integer pfv,input integer mode,input integer throttle,input integer neg);
  integer ofv,port,n;integer k;reg [FW-1:0] od;
  ofv=pfv/NC;thr=throttle;
  for(integer p=0;p<NPT;p=p+1)begin sn[p]=0;rh[p]=0;dh[p]=0;end
  for(integer fl=0;fl<ofv;fl=fl+1)for(integer c=0;c<NC;c=c+1)if(c!=J)begin
   port=(mode==0)?(c<J?c:c-1):$urandom(seed*3+fl*8+c)%NPT;
   st[port][sn[port]]=flit(c,fl,RANK,seed+fl);sn[port]=sn[port]+1;
  end
  if(neg==1)begin for(integer e=sn[2];e>1;e=e-1)st[2][e]=st[2][e-1];st[2][1]=st[2][0];sn[2]=sn[2]+1;end // duplicate before its slot issues
  if(neg==2)begin st[1][sn[1]]=flit(0,ofv,RANK,9);sn[1]=sn[1]+1;end
  if(neg==3)begin st[4][sn[4]]=flit(1,0,RANK+8'd1,9);sn[4]=sn[4]+1;end
  rn=0;dn=0;first_issue_r=-1;first_issue_d=-1;stall=0;
  repeat(4)@(negedge clk);
  if(!dq||!rq)$fatal(1,"not quiet before arm");
  pf=16'(pfv);arm=1;@(negedge clk);arm=0;active=1;
  // the banked DUT binds pf/rank one edge behind its pins: feed from the next edge
  @(negedge clk);feeding=1;
  for(k=0;k<pfv;k=k+2)begin
   hv=0;
   if(HALF)while(!(&h_r))@(negedge clk);
   for(integer i=0;i<2;i=i+1)if(k+i<pfv)begin
    hv[i]=1;
    for(integer l=0;l<LANES;l=l+1)od[32*l+:32]=rnd32(seed*977+(k+i)*13+l);
    hd[i*(32+FW)+:32+FW]={16'(k+i),16'(((J+1+(k+i)%NC)%NC)*ofv+(k+i)/NC),od};
   end
   @(negedge clk);
  end
  hv=0;
  n=0;while(n<(HALF?30000:4000)&&!(rn==ofv/2&&dn==ofv/2&&dq&&rq))begin @(negedge clk);n=n+1;end
  feeding=0;
 endtask
 integer neg=0,fails=0;
 initial begin
  if(!$value$plusargs("NEG=%d",neg))neg=0;
  repeat(4)@(negedge clk);rst_n=1;repeat(3)@(negedge clk);
  if(neg!=0)begin
   transaction(384,1,0,neg);
   repeat(40)@(negedge clk);
   if(!ddup)$fatal(1,"NEGATIVE %0d: banked DUT accepted the illegal flit (dupe low)",neg);
   $display("NEGATIVE %0d PASS: dupe raised (reference dupe=%0d)",neg,rdup);$finish;
  end
  for(integer s=0;s<4;s=s+1)begin
   seed=11+s*101;
   transaction(s==0?64:384,s<2?0:1,s==3,0);
   if(rn!=dn||rn!=(s==0?64:384)/16)begin $display("S%0d count ref %0d dut %0d",s,rn,dn);fails=fails+1;end
   for(integer i=0;i<rn&&i<dn;i=i+1)if(Rm[i]!==Dm[i]||Rd[i]!==Dd[i])begin
    if(fails<4)$display("S%0d result %0d mismatch m %0d/%0d",s,i,Rm[i],Dm[i]);fails=fails+1;end
   if(rdup||ddup)begin $display("S%0d unexpected dupe ref %0d dut %0d",s,rdup,ddup);fails=fails+1;end
   if(!dq||!rq)begin $display("S%0d not quiet",s);fails=fails+1;end
   $display("S%0d pf=%0d mode=%0d throttle=%0d results=%0d ref_first_issue->last=%0d dut_first_issue->last=%0d ref_last=%0d dut_last=%0d dut_ready_stalls=%0d",
    s,pf,s<2?0:1,s==3,dn,last_r-first_issue_r,last_d-first_issue_d,last_r,last_d,stall);
   if(fails)$fatal(1,"FAIL scenario %0d (%0d mismatches)",s,fails);
   active=0;repeat(3)@(negedge clk);
  end
  if(HALF&&pair_count==0)$fatal(1,"missing consecutive two-fast-edge service coverage");
  $display("CADENCE fast_period_ps=833.333334 core_service_fast_edges=2 pops=%0d adjacent_pairs=%0d",pop_count,pair_count);
  $display("PASS banked HA2 owner reducer: 4 scenarios bit-exact vs unchanged TU adapter (CUTS=0)");
  $finish;
 end
endmodule
