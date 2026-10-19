`timescale 1ps/1ps
`default_nettype none
// HBM-NEXT-UNITS-COLL 2026-10-19: L = 5 delivery landing (ot_hnx_su_cxdl5) on the unchanged SU slice ports.
// Serial 4 / stream 3 quanta on one lattice, phase-zero reset release (as tb_hbm_su_cxport_split).
//  run 0  lockstep, legal random traffic on lanes 0..3, lane 4 idle: every dw_v/dw_row/dw_d/fault bit of every slice
//         equals the four d4g leaves ot_hbm_su_static_cxport_dl at every serial edge (L = 5 hardware is d4g when idle)
//  run 1  lockstep with violations (phase-2 valids, bad apertures, invalid flits): faults identical too
//  run 2  calendar L = 4: a region of F = 4 M flits (slice = i mod 4, half = bit 6, row = i / 8) on the own lanes only
//  run 3  calendar L = 5: the own lanes take M - X flits a slice, lane 4 the last X (round robin over slices), placed by
//         the static calendar (tap arrival phase != 2; the own lane's flit of the same event is in the other half).
//         Every flit must land exactly once at (slice, half, row) with its data, no fault; serial edges are measured.
//  run 4  calendar error: one lane-4 flit in the SAME half as the own lane's flit of its event -> FAULT required.
// MUT (hnx side): 11 collision unchecked (run 4 fails), 12 tap ignores the slice filter, 13 lane-4 halves swapped.
module tb_hnx_su_cxdl5;
 parameter integer QID=1, MUT=0, EDGES=1500, M=160, X=32;
 localparam integer TS=1200, TP=900, T0=600, NT=2048;
 reg clk_q=0, clk_s=0;
 initial begin #(T0); forever begin clk_q=1; #(TS/2); clk_q=0; #(TS/2); end end
 initial begin #(T0); forever begin clk_s=1; #(TP/2); clk_s=0; #(TP/2); end end
 reg rst_n=0, active=0, viol=0; integer mode=0;   // 0 random lockstep, 1 calendar
 reg [4:0] del_valid; reg [5*545-1:0] del_flit; reg [5*40-1:0] del_obase;
 integer te=0;                                    // stream edges since release; te % 4 = DUT phase at edge te
 always @(posedge clk_s) te <= rst_n ? te+1 : 0;
 // ---------------- calendar schedule (built before a calendar run) ----------------
 reg sv[0:NT-1][0:4]; integer si[0:NT-1][0:4];
 function automatic integer ev(input integer t); return t - (t+1)/4; endfunction
 function automatic [39:0] faddr(input integer i);
  reg [39:0] a; begin a=0; a[5:4]=2'(i%4); a[6]=1'((i/4)%2); a[15:7]=9'(i/8); a[17:16]=2'(QID); faddr=a; end endfunction
 function automatic [511:0] fdata(input integer i);
  reg [511:0] d; for(integer l=0;l<16;l=l+1) d[32*l+:32]=32'h51ce0000^(32'(i)*32'h9e3779b1)^(32'(l)*32'h85ebca6b); return d; endfunction
 integer occ[0:3][0:NT-1][0:1];                   // flit index occupying (slice, event, half), -1 free
 integer seen[0:4095]; integer F=0, last_q=0, calN=0, run=0, errors=0, checks=0, lockn=0, dwn=0, f4_seen=0;
 task automatic build(input integer lanes, input integer collide);
  integer s, m, k, t, q, n4, head, found, own_n;
  begin
   F = 4*M;
   for(t=0;t<NT;t=t+1) for(q=0;q<5;q=q+1) begin sv[t][q]=0; si[t][q]=-1; end
   for(s=0;s<4;s=s+1) for(k=0;k<NT;k=k+1) begin occ[s][k][0]=-1; occ[s][k][1]=-1; end
   own_n = (lanes==5) ? M-X : M;
   // own lane s: flit m (i = 4m + s) at its m-th event edge from stream edge 8 (stimulus is live 2 serial edges after release)
   for(s=0;s<4;s=s+1) begin
    m=0;
    for(t=8;t<NT && m<own_n;t=t+1) if(t%4!=2) begin
     sv[t][s]=1; si[t][s]=4*m+s; occ[s][ev(t)][m%2]=4*m+s; m=m+1;      // flit 4m+s: half = m mod 2
    end
   end
   if(lanes==5) begin
    // lane 4: flits m = own_n .. M-1 of every slice, round robin; greedy first fit with a lookahead of 8
    integer qi[0:4095]; n4=0;
    for(m=own_n;m<M;m=m+1) for(s=0;s<4;s=s+1) begin qi[n4]=4*m+s; n4=n4+1; end
    head=0;
    for(t=8;t<NT-8 && head<n4;t=t+1) begin
     found=-1;
     for(q=head;q<n4 && q<head+8 && found<0;q=q+1) if(qi[q]>=0) begin
      integer i2, s2, h2, k2;
      i2=qi[q]; s2=i2%4; h2=(i2/4)%2;
      if((t+s2)%4!=2) begin
       k2=ev(t+s2);
       if(collide && head==n4/2 && q==head) begin if(occ[s2][k2][h2]>=0) found=q; end   // forced same-half collision
       else if(!(collide && head==n4/2) && occ[s2][k2][h2]<0) found=q;
      end
     end
     if(found>=0) begin
      integer i3, s3, h3;
      i3=qi[found]; s3=i3%4; h3=(i3/4)%2;
      sv[t][4]=1; si[t][4]=i3; if(occ[s3][ev(t+s3)][h3]<0) occ[s3][ev(t+s3)][h3]=i3; qi[found]=-1;
      while(head<n4 && qi[head]<0) head=head+1;
     end
    end
    if(head<n4) $fatal(1,"calendar did not place lane 4 (head %0d of %0d)", head, n4);
   end
  end
 endtask
 // ---------------- stimulus ----------------
 integer i;
 function automatic [39:0] daddr(input integer j, input integer bad);
  reg [39:0] a; begin a=0; a[5:4]=j; a[6]=$urandom; a[15:7]=$urandom; a[17:16]=QID; if(bad) a[3:0]=1; daddr=a; end endfunction
 always @(negedge clk_s) begin
  del_valid=0;
  if(active && mode==0 && (te%4!=2 || viol)) begin
   del_valid[3:0]=$urandom;
   for(i=0;i<4;i=i+1) begin del_obase[40*i+:40]=daddr(i, viol && ($urandom%50)==0);
    del_flit[545*i+:545]={1'b1,32'($urandom),{16{32'($urandom)}}}; if(viol && ($urandom%60)==0) del_flit[545*i+544]=0; end
  end else if(active && mode==1 && te<NT) begin
   for(i=0;i<5;i=i+1) if(sv[te][i]) begin
    del_valid[i]=1; del_obase[40*i+:40]=faddr(si[te][i]); del_flit[545*i+:545]={1'b1,32'(si[te][i]),fdata(si[te][i])};
   end
  end
 end
 initial begin del_valid=0; del_flit=0; del_obase=0; end
 // ---------------- d4g reference (4 leaves) and the L = 5 DUT ----------------
 wire [7:0] r_dwv, n_dwv; wire [71:0] r_dwr, n_dwr; wire [4095:0] r_dwd, n_dwd; wire [3:0] r_f, n_f;
 for(genvar g=0; g<4; g=g+1) begin : g_ref
  ot_hbm_su_static_cxport_dl #(.QID(QID),.G(g),.MUT(0)) u(.clk_s(clk_s),.clk_q(clk_q),.rst_s_n(rst_n),.rst_q_n(rst_n),
   .del_valid(del_valid[g]),.del_flit(del_flit[545*g+:545]),.del_obase(del_obase[40*g+:40]),
   .dw_v(r_dwv[2*g+:2]),.dw_row(r_dwr[18*g+:18]),.dw_d(r_dwd[1024*g+:1024]),.fault(r_f[g]));
 end
 ot_hnx_su_cxdl5 #(.QID(QID),.MUT(MUT)) dut(.clk_s(clk_s),.clk_q(clk_q),.rst_s_n(rst_n),.rst_q_n(rst_n),.del_valid(del_valid),
  .del_flit(del_flit),.del_obase(del_obase),.dw_v(n_dwv),.dw_row(n_dwr),.dw_d(n_dwd),.fault(n_f));
 // ---------------- checks ----------------
 integer tq=0; reg cmp=0;
 always @(posedge clk_q) tq <= rst_n ? tq+1 : 0;
 always @(posedge clk_q) if(cmp) begin
  #2;
  if(mode==0) begin
   checks=checks+1;
   if(r_dwv!==n_dwv || r_dwr!==n_dwr || r_dwd!==n_dwd || r_f!==n_f) begin errors=errors+1;
    if(errors<6) $display("LOCKSTEP MISMATCH run%0d t=%0t dwv %h/%h fault %b/%b row_eq %b d_eq %b", run, $time, r_dwv, n_dwv, r_f, n_f,
      r_dwr===n_dwr, r_dwd===n_dwd); end
   if(|r_dwv) lockn=lockn+1;
  end else begin
   for(integer s=0;s<4;s=s+1) for(integer h=0;h<2;h=h+1) if(n_dwv[2*s+h]) begin
    integer m, i4, found; found=-1; dwn=dwn+1;
    // the flit at (slice s, half h, row): i = 8 row + 4 h + s
    i4 = 8*int'(n_dwr[18*s+9*h+:9]) + 4*h + s;
    if(i4>=F || seen[i4]!=0 || n_dwd[1024*s+512*h+:512]!==fdata(i4)) begin if(run!=4) errors=errors+1;   // run 4 collides on purpose
     if(errors<8) $display("LAND MISMATCH run%0d slice%0d half%0d row%0d i%0d seen%0d", run, s, h, n_dwr[18*s+9*h+:9], i4, i4<F?seen[i4]:-1); end
    else seen[i4]=1;
    last_q = tq;
   end
  end
 end
 integer k, missing, faults_run;
 task automatic release_and_run(input integer md, input integer vio, input integer edges);
  begin
   rst_n=0; cmp=0; active=0; viol=vio; mode=md;
   repeat(4) @(posedge clk_q);
   while((($time-T0)%(3*TS)) != 2*TS) @(posedge clk_q);
   #(TS-150); rst_n=1;
   repeat(2) @(negedge clk_q); cmp=1; active=1;
   repeat(edges) @(negedge clk_q);
   active=0; repeat(30) @(negedge clk_q);
  end
 endtask
 integer t4=0, t5=0, fault4=0;
 initial begin
  // run 0/1: lockstep vs d4g with lane 4 idle
  run=0; release_and_run(0, 0, EDGES); if(|n_f) begin errors=errors+1; $display("RUN0 legal traffic faulted %b", n_f); end
  run=1; release_and_run(0, 1, EDGES);
  $display("CXDL5 LOCKSTEP runs0-1 checks%0d dw_edges%0d errors%0d fault_end ref%b hnx%b", checks, lockn, errors, r_f, n_f);
  // run 2: L = 4 calendar
  for(k=0;k<4096;k=k+1) seen[k]=0;
  run=2; build(4, 0); last_q=0; release_and_run(1, 0, 600); t4=last_q;
  missing=0; for(k=0;k<F;k=k+1) if(seen[k]==0) missing=missing+1;
  if(missing || |n_f) begin errors=errors+1; $display("RUN2 missing%0d fault%b", missing, n_f); end
  // run 3: L = 5 calendar
  for(k=0;k<4096;k=k+1) seen[k]=0;
  run=3; build(5, 0); last_q=0; release_and_run(1, 0, 600); t5=last_q;
  missing=0; for(k=0;k<F;k=k+1) if(seen[k]==0) missing=missing+1;
  if(missing || |n_f) begin errors=errors+1; $display("RUN3 missing%0d fault%b", missing, n_f); end
  $display("CXDL5_CALENDAR F%0d M%0d X%0d L4_last_serial_edge%0d L5_last_serial_edge%0d speedup%0.3f missing%0d", F, M, X, t4, t5,
    real'(t4)/real'(t5), missing);
  // run 4: one same-half collision -> fault required
  for(k=0;k<4096;k=k+1) seen[k]=0;
  run=4; build(5, 1); release_and_run(1, 0, 600); fault4 = |n_f;
  if(!fault4) begin errors=errors+1; $display("RUN4 collision NOT faulted"); end
  if(errors==0 && checks>2*EDGES-10 && lockn>100 && t5>0 && t5<t4)
   $display("CXDL5 PASS lockstep_checks%0d calendar L4 %0d -> L5 %0d serial edges (x%0.3f) collision_fault%0d", checks, t4, t5,
     real'(t4)/real'(t5), fault4);
  else $display("CXDL5 FAIL errors%0d checks%0d lockn%0d t4 %0d t5 %0d collision_fault%0d", errors, checks, lockn, t4, t5, fault4);
  $finish;
 end
endmodule
`default_nettype wire
