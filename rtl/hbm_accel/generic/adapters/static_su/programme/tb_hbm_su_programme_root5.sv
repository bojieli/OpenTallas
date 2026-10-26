`timescale 1ns/1ps
// HBM-RTL5 2026-10-18: WHOLE SU programme path, r5 vs r4, on the full 7111-edge su_top_compile image (all 4 quarters).
//   REF (previous behaviour, the d4f/d4g GEN0 composition): ot_hbm_su_programme_part PARTS 4 DEPTH 2 PIPE 2 = root
//       ot_hbm_su_programme_root FREG 1 (= root_h, 4 x 98 banks) + 4 x pslice STAGES 1 PIPE 2 (= pslice_q4).
//   DUT (d4g GEN1): ot_hbm_su_programme_root5 (root_h5: SMACROS 4 x 320, SDLY 2, RRLY 1) -> 4 x ot_hbm_su_programme_
//       pslice_c5 (pghead + 10 pgcol S/L leaves with the NATIVE-FIX3 pin/reset stages), wired as the die wires su_pgr ->
//       pgp_<q> (r_start/r_len shared, r_we[k]/r_bank[k], r_row/r_data shared, p_fault[k] <- pgp_<k>.fault,
//       busy/valid/done/edge_index from pgp_0).
// ONE host stimulus drives both on the SAME edges (configuration image, start, directed fault writes); each side gets
// its own compiled image (ref: --partition 4; DUT: --root5, bank = 320 part + 32 column + local), written in separate
// idle windows. Check on EVERY edge (outside reset windows): every DUT output (9,688-b command, valid, done,
// edge_index, busy, fault) == the REF output SD=2 edges earlier (the documented root_h5 latency shift), REF command ==
// golden line. Two executions, then directed cases on identical host edges: (c) write while busy (part 0), (d) write
// while busy (part 3), reset, (a) write on the start edge (start rejected everywhere), reset, (b) write to no part.
// Reset: the DUT root and the cluster head/leaves of every part leave reset RREL=3 edges after the port (checked).
// Mutants (must FAIL): -GMUT=1 root SDLY 0 (old root timing with the r5 clusters), 2 root decode 4 x 98, 3 root reset
// relay bypassed, 4 root out-of-range fault not delayed; -GCMUT=5 cluster leaf cfg pin stage dropped (old leaves);
// +MUT_CFG (quarter 2 column 3 index one edge off + column 2 dictionary word flipped).
module tb_hbm_su_programme_root5;
`include "ref4/part_params.svh"
`include "root5_params.svh"
localparam integer B=PART_SB*PART_N, N=PART_EDGES, WM=PART_WRITES, WP=R5_WRITES, P=R5_PARTS, SB=R5_SB;
parameter integer MUT=0, CMUT=0;
localparam integer SD=2, RREL=3;
logic clk=0; always #5 clk=~clk;
logic rst_n=0;
logic m_we=0, p_we=0, start=0;
logic [15:0] m_bank=0, p_bank=0; logic [6:0] m_row=0, p_row=0; logic [255:0] m_data=0, p_data=0;
wire m_busy,m_valid,m_done,m_fault,p_busy,p_valid,p_done,p_fault;
wire [15:0] m_edge,p_edge; wire [B-1:0] m_cmd,p_cmd;
reg [279:0] m_cfg[0:WM-1]; reg [279:0] p_cfg[0:WP-1]; reg [B-1:0] golden[0:N-1];
string dir; integer mism, checked, active, faults_seen, chk;
// REF
ot_hbm_su_programme_part #(.LINE_BITS(B),.EDGES(N),.PARTS(PART_N),.DEPTH(PART_DEPTH),.SCOLS(PART_COLS),
 .SMACROS(PART_SMACROS),.DICT_BANKS(PART_DICT_BANKS),.MACROS(PART_MACROS),.PIPE(2)) u_ref(
 .clk(clk),.clk_macro({PART_MACROS{clk}}),.rst_n(rst_n),.cfg_we(m_we),.cfg_bank(m_bank),.cfg_row(m_row),
 .cfg_data(m_data),.start(start),.length(16'(N)),.busy(m_busy),.valid(m_valid),.done(m_done),.fault(m_fault),
 .edge_index(m_edge),.command(m_cmd));
// DUT
wire r_start; wire [15:0] r_len; wire [P-1:0] r_we, q_fault, q_busy, q_valid, q_done; wire [16*P-1:0] r_bank, q_edge;
wire [6:0] r_row; wire [255:0] r_data;
ot_hbm_su_programme_root5 #(.PARTS(P),.SMACROS({P{32'(R5_PART_BANKS)}}),.SDLY(2),.RRLY(1),.MUT(MUT)) u_root(
 .clk(clk),.rst_n(rst_n),.cfg_we(p_we),.cfg_bank(p_bank),.cfg_row(p_row),.cfg_data(p_data),.start(start),
 .length(16'(N)),.p_fault(q_fault),.r_start(r_start),.r_len(r_len),.r_we(r_we),.r_bank(r_bank),.r_row(r_row),
 .r_data(r_data),.fault(p_fault));
genvar k;
for(k=0;k<P;k=k+1) begin:g_q
  ot_hbm_su_programme_pslice_c5 #(.SB(SB),.NC(R5_NC),.DICT_CAP(R5_CAP),.MUT(CMUT),.MUT_COL(1)) u_c5(
   .clk(clk),.rst_n(rst_n),.cfg_we(r_we[k]),.cfg_bank(r_bank[16*k+:16]),.cfg_row(r_row),.cfg_data(r_data),
   .start(r_start),.length(r_len),.busy(q_busy[k]),.valid(q_valid[k]),.done(q_done[k]),.fault(q_fault[k]),
   .edge_index(q_edge[16*k+:16]),.command(p_cmd[SB*k+:SB]));
end
assign p_busy=q_busy[0]; assign p_valid=q_valid[0]; assign p_done=q_done[0]; assign p_edge=q_edge[15:0];
task automatic tick; @(posedge clk); #1; endtask
// REF history: h_*[0] = REF output sampled this edge, h_*[SD] = SD edges ago
reg [B-1:0] h_cmd[0:SD]; reg h_v[0:SD], h_d[0:SD], h_b[0:SD], h_f[0:SD]; reg [15:0] h_e[0:SD];
integer hv;   // valid history depth since the last (re-)enable
always @(posedge clk) begin
  #2;
  for(integer j=SD;j>0;j=j-1) begin h_cmd[j]=h_cmd[j-1]; h_v[j]=h_v[j-1]; h_d[j]=h_d[j-1]; h_b[j]=h_b[j-1];
    h_f[j]=h_f[j-1]; h_e[j]=h_e[j-1]; end
  h_cmd[0]=m_cmd; h_v[0]=m_valid; h_d[0]=m_done; h_b[0]=m_busy; h_f[0]=m_fault; h_e[0]=m_edge;
  if(chk) begin
    hv=hv+1;
    if(hv>SD) begin
      if(p_cmd!==h_cmd[SD] || p_valid!==h_v[SD] || p_done!==h_d[SD] || p_edge!==h_e[SD] || p_busy!==h_b[SD] ||
         p_fault!==h_f[SD]) begin
        mism=mism+1;
        if(mism<=4) $display("SU_PROGRAMME_ROOT5_MISMATCH t=%0t valid=%b/%b edge=%0d/%0d done=%b/%b busy=%b/%b fault=%b/%b cmd_eq=%b",
          $time,p_valid,h_v[SD],p_edge,h_e[SD],p_done,h_d[SD],p_busy,h_b[SD],p_fault,h_f[SD],p_cmd===h_cmd[SD]);
      end
      checked=checked+1;
    end
    if(m_valid) begin
      active=active+1;
      if(m_cmd!==golden[m_edge]) begin mism=mism+1; if(mism<=4) $display("SU_PROGRAMME_ROOT5_GOLDEN_MISMATCH edge=%0d",m_edge); end
    end
    if(m_fault) faults_seen=faults_seen+1;
  end else hv=0;
end
task automatic execute;
 @(negedge clk); start=1; tick(); @(negedge clk); start=0;
 for(integer e=0;e<N+10;e=e+1) tick();
endtask
// reset release: DUT root + every part's head and column 0/1 leaves, edges after the port release
task automatic rel_check;
 integer rr, bad;
 rr=-1; bad=0;
 for(integer e=1;e<=8;e=e+1) begin
   tick();
   if(rr<0 && u_root.rr===1'b1) rr=e;
   if(e==RREL-1 && (g_q[0].u_c5.u_h.hr!==1'b0 || g_q[3].u_c5.g_c[1].u_c.rl!==2'b00)) bad=1;
   if(e==RREL && (g_q[0].u_c5.u_h.hr!==1'b1 || g_q[1].u_c5.u_h.hr!==1'b1 || g_q[2].u_c5.g_c[0].u_c.rl!==2'b11 ||
                  g_q[3].u_c5.g_c[1].u_c.rl!==2'b11)) bad=1;
 end
 if(rr!=RREL || bad) begin mism=mism+1;
   $display("SU_PROGRAMME_ROOT5 reset release root=%0d edges (expected %0d) cluster_bad=%0d",rr,RREL,bad); end
endtask
task automatic do_reset;
 @(negedge clk); chk=0; rst_n=0; tick(); tick(); @(negedge clk); rst_n=1; rel_check(); chk=1;
endtask
// one host write on both sides on the same edge
task automatic wr2(input [15:0] mb, input [15:0] pb, input [6:0] row, input [255:0] d, input logic st);
 @(negedge clk); m_we=1; p_we=1; m_bank=mb; p_bank=pb; m_row=row; p_row=row; m_data=d; p_data=d; start=st; tick();
 @(negedge clk); m_we=0; p_we=0; start=0;
endtask
integer f_before;
initial begin
 checked=0; mism=0; active=0; faults_seen=0; chk=0; hv=0;
 if(!$value$plusargs("DIR=%s",dir)) $fatal(1,"DIR required");
 $readmemh({dir,"/ref4/config.mem"},m_cfg);
 if($test$plusargs("MUT_CFG")) $readmemh({dir,"/config_mut.mem"},p_cfg); else $readmemh({dir,"/config.mem"},p_cfg);
 $readmemh({dir,"/expected.mem"},golden);
 tick(); @(negedge clk); rst_n=1; rel_check(); @(negedge clk);
 for(integer i=0;i<WM;i=i+1) begin
   m_we=1; m_bank=m_cfg[i][279:264]; m_row=m_cfg[i][262:256]; m_data=m_cfg[i][255:0]; tick(); @(negedge clk);
 end
 m_we=0;
 for(integer i=0;i<WP;i=i+1) begin
   p_we=1; p_bank=p_cfg[i][279:264]; p_row=p_cfg[i][262:256]; p_data=p_cfg[i][255:0]; tick(); @(negedge clk);
 end
 p_we=0; for(integer i=0;i<12;i=i+1) tick();
 chk=1;
 execute(); execute();
 if(m_fault || p_fault) begin mism=mism+1; $display("SU_PROGRAMME_ROOT5 unexpected fault m=%b p=%b",m_fault,p_fault); end
 if(active!=2*N) begin mism=mism+1; $display("SU_PROGRAMME_ROOT5 active=%0d of %0d",active,2*N); end
 // (c) write while busy, part 0: ref bank 0 / DUT part 0 column 0 bank 0 (same host edge)
 @(negedge clk); start=1; tick(); @(negedge clk); start=0;
 for(integer e=0;e<100;e=e+1) tick();
 wr2(16'd0, 16'd0, 7'd5, '1, 1'b0);
 for(integer e=0;e<N;e=e+1) tick();
 f_before=faults_seen; if(f_before==0) begin mism=mism+1; $display("SU_PROGRAMME_ROOT5 case c: no fault"); end
 // (d) write while busy, part 3 (decode of the last part): ref bank 3 x 98 / DUT 3 x 320 + column 5 bank 0
 do_reset();
 @(negedge clk); start=1; tick(); @(negedge clk); start=0;
 for(integer e=0;e<50;e=e+1) tick();
 wr2(16'(3*PART_SMACROS[31:0]), 16'(3*R5_PART_BANKS+32*5), 7'd2, '0, 1'b0);
 for(integer e=0;e<N;e=e+1) tick();
 if(faults_seen==f_before) begin mism=mism+1; $display("SU_PROGRAMME_ROOT5 case d: no fault"); end
 f_before=faults_seen;
 // (a) write on the start edge (same host edge): start rejected in every part; ref bank 1 / DUT column 3 bank 0
 do_reset();
 wr2(16'd1, 16'(32*3), 7'd0, m_cfg[128][255:0], 1'b1);
 for(integer e=0;e<40;e=e+1) tick();
 if(faults_seen==f_before) begin mism=mism+1; $display("SU_PROGRAMME_ROOT5 case a: no fault"); end
 if(m_busy || p_busy) begin mism=mism+1; $display("SU_PROGRAMME_ROOT5 case a: busy"); end
 f_before=faults_seen;
 // (b) write to no part (out of range)
 do_reset();
 wr2(16'hffff, 16'hffff, 7'd0, '0, 1'b0);
 for(integer e=0;e<40;e=e+1) tick();
 if(faults_seen==f_before) begin mism=mism+1; $display("SU_PROGRAMME_ROOT5 case b: no fault"); end
 if(mism!=0) $fatal(1,"SU_PROGRAMME_ROOT5 FAIL mismatches=%0d active=%0d checked=%0d",mism,active,checked);
 $display("SU_PROGRAMME_ROOT5 PASS edges=%0d active=%0d checked=%0d parts=%0d cols=%0d ref_writes=%0d dut_writes=%0d shift=%0d fault_cases=4",
   N,active,checked,P,R5_NC,WM,WP,SD);
 $finish;
end
endmodule
