`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// HBM-B-RTL1 lockstep bench: SU scalar tree (ot_hbm_su_stree_net, d4g) against the d4f RF write relay network of
// ot_hbm_su_static_top (ref_d4f_rf_relay below = the g_src/g_dst code of that file, verbatim apart from the module wrap).
// Stimulus: random heads {v, tag8, x32} on all 4 reducers every edge (valid with probability 1/2, incl. all-4-at-once).
// Checks, every edge, every replica d and source w:
//   (1) tree  : rf_wv/wa/wd[d][w] == head[w] injected exactly L_TREE edges earlier (valid always; tag/x when valid);
//   (2) d4f36 : the RF_RELAY=36 reference == head[w] injected exactly 36 edges earlier (same check; the documented delta
//               is L_TREE - 36 edges);
//   (3) lock  : a second reference with RF_RELAY=L_TREE equals the tree output bit for bit on every valid word;
//   (4) coherence: for each w, all 4 replicas see the same word on the same edge (implied by (1), checked explicitly).
// PASS prints "STREE PASS"; any mismatch prints "STREE FAIL" and the first errors. Mutants: -P...MUT=1..4 must FAIL.
// ---------------------------------------------------------------------------------------------------------------------
module ref_d4f_rf_relay #(parameter integer RF_RELAY=36)(
 input wire [3:0] clk_relay, input wire rst_n, input wire [4*41-1:0] heads, output wire [40:0] rly [0:15]
);
 for(genvar w=0;w<4;w=w+1)begin:g_src
  wire [40:0] head=heads[w*41+:41];
  for(genvar d=0;d<4;d=d+1)begin:g_dst
    reg st_v [0:RF_RELAY-1]; reg [39:0] st_d [0:RF_RELAY-1];
    integer k;
    always @(posedge clk_relay[w] or negedge rst_n)
     if(!rst_n)for(k=0;k<RF_RELAY;k=k+1)st_v[k]<=1'b0;
     else begin st_v[0]<=head[40];for(k=1;k<RF_RELAY;k=k+1)st_v[k]<=st_v[k-1]; end
    always @(posedge clk_relay[w])begin st_d[0]<=head[39:0];for(k=1;k<RF_RELAY;k=k+1)st_d[k]<=st_d[k-1]; end
    assign rly[w*4+d]={st_v[RF_RELAY-1],st_d[RF_RELAY-1]};
  end
 end
endmodule

module tb_hbm_su_stree;
 parameter integer UP=14, DN=14, MUT=0, NCYC=20000, SEED=1;
 localparam integer L=UP+DN+4, D4F=36, H=64;
 reg clk=0; always #5 clk=~clk;
 reg rst_n=0;
 reg [4*41-1:0] heads=0;
 wire [15:0] q_wv; wire [127:0] q_wa; wire [511:0] q_wd;
 ot_hbm_su_stree_net #(.UP(UP),.DN(DN),.MUT(MUT)) dut(.clk_q({4{clk}}),.clk_root(clk),.rst_n(rst_n),.head(heads),
  .q_wv(q_wv),.q_wa(q_wa),.q_wd(q_wd));
 wire [40:0] r36 [0:15]; wire [40:0] rL [0:15];
 ref_d4f_rf_relay #(.RF_RELAY(D4F)) u_r36(.clk_relay({4{clk}}),.rst_n(rst_n),.heads(heads),.rly(r36));
 ref_d4f_rf_relay #(.RF_RELAY(L)) u_rL(.clk_relay({4{clk}}),.rst_n(rst_n),.heads(heads),.rly(rL));
 reg [4*41-1:0] hist [0:H-1];   // heads applied at edge t (index t mod H)
 integer t, d, w, err, nwords, nall4, seed;
 reg [40:0] exp_t, exp_r, got;
 initial begin
  seed=SEED; err=0; nwords=0; nall4=0;
  for(t=0;t<H;t=t+1) hist[t]=0;
  repeat(4) @(posedge clk); #1 rst_n=1;
  for(t=0;t<NCYC;t=t+1) begin
   @(negedge clk);
   // check outputs produced by the edge just passed (edge index t-1 => sampled heads of edge t-1-L)
   if(t>L+12) for(d=0;d<4;d=d+1) for(w=0;w<4;w=w+1) begin
    exp_t=hist[(t-L+H)%H][w*41+:41];
    got={q_wv[d*4+w],q_wa[d*32+w*8+:8],q_wd[d*128+w*32+:32]};
    if(got[40]!==exp_t[40] || (exp_t[40] && got!==exp_t)) begin
     err=err+1; if(err<8) $display("ERR tree t=%0d d=%0d w=%0d got=%h exp=%h",t,d,w,got,exp_t); end
    if(exp_t[40]) nwords=nwords+1;
    if(rL[w*4+d][40]!==got[40] || (got[40] && rL[w*4+d]!==got)) begin
     err=err+1; if(err<8) $display("ERR lock t=%0d d=%0d w=%0d tree=%h refL=%h",t,d,w,got,rL[w*4+d]); end
    // coherence: replica d vs replica 0 for the same source on the same edge
    if({q_wv[d*4+w],q_wa[d*32+w*8+:8],q_wd[d*128+w*32+:32]}!=={q_wv[w],q_wa[w*8+:8],q_wd[w*32+:32]} && got[40]) begin
     err=err+1; if(err<8) $display("ERR coh t=%0d d=%0d w=%0d",t,d,w); end
    if(t>D4F+12) begin
     exp_r=hist[(t-D4F+H)%H][w*41+:41];
     if(r36[w*4+d][40]!==exp_r[40] || (exp_r[40] && r36[w*4+d]!==exp_r)) begin
      err=err+1; if(err<8) $display("ERR d4f36 t=%0d d=%0d w=%0d got=%h exp=%h",t,d,w,r36[w*4+d],exp_r); end
    end
   end
   // drive the heads for the next edge (edge index t)
   for(w=0;w<4;w=w+1) heads[w*41+:41]={($random(seed)&1)==1, 8'($random(seed)), 32'($random(seed))};
   if(t%97==5) for(w=0;w<4;w=w+1) heads[w*41+40]=1'b1;   // all four reducers on one edge
   if(&{heads[163],heads[122],heads[81],heads[40]}) nall4=nall4+1;
   if(t<12) for(w=0;w<4;w=w+1) heads[w*41+40]=1'b0;        // reset settle (pin rst sync 2 edges)
   hist[t%H]=heads;
  end
  $display("STREE %s UP=%0d DN=%0d L_TREE=%0d d4f=%0d delta=%0d edges words=%0d all4_edges=%0d errors=%0d MUT=%0d",
   err==0?"PASS":"FAIL",UP,DN,L,D4F,L-D4F,nwords,nall4,err,MUT);
  $finish;
 end
endmodule
