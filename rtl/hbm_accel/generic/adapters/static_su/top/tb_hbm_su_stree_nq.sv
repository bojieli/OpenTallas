`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// HBM-BIND B2 (2026-10-24): SU scalar tree NLEG bench (ot_hbm_su_stree_net #(NLEG), root masters ot_hbm_su_stree_root /
// ot_hbm_su_stree_root2, leaf NLEG). Random heads {v, tag8, x32} on every reducer every edge (valid p = 1/2, plus
// all-legs-at-once edges). REF = the unchanged origin net (ot_hbm_su_stree.sv of the base, every module renamed *_ref,
// run_stree_nq.sh extracts it).
//   NLEG 4: (1) model: replica d lane w == head[w] injected exactly L_TREE edges earlier (valid always, data when valid);
//           (2) lock : DUT == REF bit for bit, all 16 x 41-b replica words, every edge (incl. invalid data).
//   NLEG 2: (1) model as above for 2 replicas x 2 lanes;
//           (2) lock : DUT replica d lane w == REF (4-leg) replica 2+d lane 2+w, REF driven with heads {h1, h0, 0, 0}
//               (legs 2 NW / 3 NE = B2 legs 0 / 1; SW / SE heads idle), valid always, data when valid.
//   Both: coherence (every replica sees source w on the same edge).
// Mutants (-P...MUT=1..4, net level, see ot_hbm_su_stree.sv) must FAIL.
// ---------------------------------------------------------------------------------------------------------------------
module tb_hbm_su_stree_nq;
 parameter integer UP=14, DN=14, MUT=0, NCYC=20000, SEED=7, NLEG=4;
 localparam integer L=UP+DN+4, H=64, N=NLEG;
 reg clk=0; always #5 clk=~clk;
 reg rst_n=0;
 reg [N*41-1:0] heads=0;
 wire [N*N-1:0] q_wv; wire [N*N*8-1:0] q_wa; wire [N*N*32-1:0] q_wd;
 ot_hbm_su_stree_net #(.UP(UP),.DN(DN),.MUT(MUT),.NLEG(NLEG)) dut(.clk_q({N{clk}}),.clk_root(clk),.rst_n(rst_n),.head(heads),
  .q_wv(q_wv),.q_wa(q_wa),.q_wd(q_wd));
 wire [4*41-1:0] rheads=(N==4)?heads:{heads,82'd0};
 wire [15:0] r_wv; wire [127:0] r_wa; wire [511:0] r_wd;
 ot_hbm_su_stree_net_ref #(.UP(UP),.DN(DN),.MUT(0)) ref4(.clk_q({4{clk}}),.clk_root(clk),.rst_n(rst_n),.head(rheads),
  .q_wv(r_wv),.q_wa(r_wa),.q_wd(r_wd));
 reg [N*41-1:0] hist [0:H-1];
 integer t, d, w, err, nchk, nwords, nall, seed, rd, rw;
 reg [40:0] exp_t, got, rg, g0;
 initial begin
  seed=SEED; err=0; nchk=0; nwords=0; nall=0;
  for(t=0;t<H;t=t+1) hist[t]=0;
  repeat(4) @(posedge clk); #1 rst_n=1;
  for(t=0;t<NCYC;t=t+1) begin
   @(negedge clk);
   if(t>L+12) for(d=0;d<N;d=d+1) for(w=0;w<N;w=w+1) begin
    exp_t=hist[(t-L+H)%H][w*41+:41];
    got={q_wv[d*N+w],q_wa[(d*N+w)*8+:8],q_wd[(d*N+w)*32+:32]};
    rd=(N==4)?d:d+2; rw=(N==4)?w:w+2;
    rg={r_wv[rd*4+rw],r_wa[(rd*4+rw)*8+:8],r_wd[(rd*4+rw)*32+:32]};
    g0={q_wv[w],q_wa[w*8+:8],q_wd[w*32+:32]};
    nchk=nchk+3;
    if(got[40]!==exp_t[40] || (exp_t[40] && got!==exp_t)) begin
     err=err+1; if(err<8) $display("ERR model t=%0d d=%0d w=%0d got=%h exp=%h",t,d,w,got,exp_t); end
    if(exp_t[40]) nwords=nwords+1;
    if(N==4 ? (got!==rg) : (got[40]!==rg[40] || (got[40] && got!==rg))) begin
     err=err+1; if(err<8) $display("ERR lock t=%0d d=%0d w=%0d dut=%h ref=%h",t,d,w,got,rg); end
    if(got[40] && got!==g0) begin
     err=err+1; if(err<8) $display("ERR coh t=%0d d=%0d w=%0d",t,d,w); end
   end
   for(w=0;w<N;w=w+1) heads[w*41+:41]={($random(seed)&1)==1, 8'($random(seed)), 32'($random(seed))};
   if(t%97==5) for(w=0;w<N;w=w+1) heads[w*41+40]=1'b1;
   begin : all_v integer a; a=1; for(w=0;w<N;w=w+1) a=a&heads[w*41+40]; nall=nall+a; end
   if(t<12) for(w=0;w<N;w=w+1) heads[w*41+40]=1'b0;
   hist[t%H]=heads;
  end
  $display("STREE_NQ%0d %s checks=%0d errors=%0d words=%0d all_legs_edges=%0d L_TREE=%0d UP=%0d DN=%0d MUT=%0d",
   N,err==0?"PASS":"FAIL",nchk,err,nwords,nall,L,UP,DN,MUT);
  $finish;
 end
endmodule
