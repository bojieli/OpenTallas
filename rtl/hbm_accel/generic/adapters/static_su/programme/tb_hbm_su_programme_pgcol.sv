`timescale 1ns/1ps
// HBM-SU r5 2026-10-17: lockstep equivalence of the per-column cluster ot_hbm_su_programme_pslice_c5 (head + 10 pgcol
// leaves, packed per-column index) against the r4 per-quarter producer (ot_hbm_su_programme_pslice PIPE 2, STAGES 1)
// on one quarter of the 7111-edge su_top_compile image. SAME start edge (lead 0: the start advance stays DEPTH+4);
// every output (command, valid, done, edge_index, busy, fault) identical on EVERY edge through two executions, command
// = golden line; then directed fault cases, each in lockstep: (c) a configuration write during a third execution
// (write while busy), reset, (a) a configuration write on the start edge (start rejected in every column), reset,
// (b) a write to no column / out of range.
// Mutants (must FAIL): +MUT_CFG (config_mut.mem: column 3 index one edge off = PC offset, column 2 dictionary word
// flipped), -GMUT=1 (column MUT_COL start one edge late = phase), -GMUT=2 (head cfg_any not driven), -GMUT=3 (column
// MUT_COL final dictionary mux on the live hit = stale select).
// NATIVE-FIX3/pgs 2026-10-18: the cluster's configuration path is CL=2 edges longer than the r4 producer's (head export
// register + leaf pin register): every directed cluster write is driven CL edges before the reference write (the host
// issues configuration 2 edges earlier); the leaves' reset is released RREL=3 edges after the port (ot_rst_relay), checked
// on every reset; do_reset waits 8 edges. New mutants: -GMUT=4 (leaf reset relay bypassed: release check), -GMUT=5 (leaf
// cfg pin stage dropped), -GMUT=6 (head export registers dropped), -GMUT=7 (head l_fault pin registers dropped): the
// fault cases land 1 edge early -> lockstep mismatch; -GMUT=8 (head reset relay bypassed: release check).
module tb_hbm_su_programme_pgcol;
`include "ref/programme_params.svh"
`include "cols_params.svh"
localparam integer B=CL_SB, N=CL_EDGES, WM=REF_WRITES, WP=CL_WRITES;
parameter integer MUT=0;
localparam integer CL=2, RREL=3;
logic clk=0; always #5 clk=~clk;
logic rst_n=0;
logic m_we=0, p_we=0, start=0;
logic [15:0] m_bank=0, p_bank=0; logic [6:0] m_row=0, p_row=0; logic [255:0] m_data=0, p_data=0;
wire m_busy,m_valid,m_done,m_fault,p_busy,p_valid,p_done,p_fault;
wire [15:0] m_edge,p_edge; wire [B-1:0] m_cmd,p_cmd;
reg [279:0] m_cfg[0:WM-1]; reg [279:0] p_cfg[0:WP-1]; reg [B-1:0] golden[0:N-1];
string dir; integer mism, checked, active, faults_seen;
ot_hbm_su_programme_pslice #(.SB(B),.EDGES(N),.SCOLS(REF_COLS),.DICT_BANKS(REF_DICT_BANKS),.MACROS(REF_MACROS),
 .STAGES(1),.PIPE(2)) u_ref(
 .clk(clk),.clk_macro({REF_MACROS{clk}}),.rst_n(rst_n),.cfg_we(m_we),.cfg_bank(m_bank),.cfg_row(m_row),
 .cfg_data(m_data),.start(start),.length(16'(N)),.busy(m_busy),.valid(m_valid),.done(m_done),.fault(m_fault),
 .edge_index(m_edge),.command(m_cmd));
ot_hbm_su_programme_pslice_c5 #(.SB(B),.NC(CL_NC),.DICT_CAP(CL_CAP),.MUT(MUT),.MUT_COL(1)) u_cl(
 .clk(clk),.rst_n(rst_n),.cfg_we(p_we),.cfg_bank(p_bank),.cfg_row(p_row),
 .cfg_data(p_data),.start(start),.length(16'(N)),.busy(p_busy),.valid(p_valid),.done(p_done),.fault(p_fault),
 .edge_index(p_edge),.command(p_cmd));
task automatic tick; @(posedge clk); #1; endtask
always @(posedge clk) if(rst_n && checked>=0) begin
  #2;
  if(p_cmd!==m_cmd || p_valid!==m_valid || p_done!==m_done || p_edge!==m_edge || p_busy!==m_busy || p_fault!==m_fault) begin
    mism=mism+1;
    if(mism<=4) $display("SU_PROGRAMME_PGCOL_MISMATCH t=%0t valid=%b/%b edge=%0d/%0d done=%b/%b busy=%b/%b fault=%b/%b cmd_eq=%b",
      $time,p_valid,m_valid,p_edge,m_edge,p_done,m_done,p_busy,m_busy,p_fault,m_fault,p_cmd===m_cmd);
  end
  if(m_valid) begin
    active=active+1;
    if(m_cmd!==golden[m_edge]) begin mism=mism+1; if(mism<=4) $display("SU_PROGRAMME_PGCOL_GOLDEN_MISMATCH edge=%0d",m_edge); end
  end
  if(m_fault) faults_seen=faults_seen+1;
  checked=checked+1;
end
task automatic execute;
 @(negedge clk); start=1; tick(); @(negedge clk); start=0;
 for(integer e=0;e<N+10;e=e+1) tick();
endtask
// leaf reset release: edges from the port release until column 0 / MUT_COL column leave reset (region 0 and 1)
task automatic rel_check;
 integer r0, r1, rh;
 r0=-1; r1=-1; rh=-1;
 for(integer k=1;k<=8;k=k+1) begin
   tick();
   if(r0<0 && u_cl.g_c[0].u_c.rl===2'b11) r0=k;
   if(r1<0 && u_cl.g_c[1].u_c.rl===2'b11) r1=k;
   if(rh<0 && u_cl.u_h.hr===1'b1) rh=k;
 end
 if(r0!=RREL || r1!=RREL || rh!=RREL) begin mism=mism+1;
   $display("SU_PROGRAMME_PGCOL reset release col0=%0d col1=%0d head=%0d edges (expected %0d)",r0,r1,rh,RREL); end
endtask
task automatic do_reset;
 @(negedge clk); rst_n=0; tick(); tick(); @(negedge clk); rst_n=1; rel_check();
endtask
integer f_before;
initial begin
 checked=-1; mism=0; active=0; faults_seen=0;
 if(!$value$plusargs("DIR=%s",dir)) $fatal(1,"DIR required");
 $readmemh({dir,"/ref/config.mem"},m_cfg);
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
 p_we=0; for(integer i=0;i<4+CL;i=i+1) tick();
 checked=0;
 execute(); execute();
 if(m_fault || p_fault) begin mism=mism+1; $display("SU_PROGRAMME_PGCOL unexpected fault m=%b p=%b",m_fault,p_fault); end
 if(active!=2*N) begin mism=mism+1; $display("SU_PROGRAMME_PGCOL active=%0d of %0d",active,2*N); end
 // (c) write while busy (rejected, sticky fault on the same edge): ref bank 0 / cluster column 0 bank 0
 @(negedge clk); start=1; tick(); @(negedge clk); start=0;
 for(integer e=0;e<100-CL;e=e+1) tick();
 @(negedge clk); p_we=1; p_bank=0; p_row=5; p_data='1; tick();
 @(negedge clk); p_we=0; for(integer e=1;e<CL;e=e+1) tick();
 @(negedge clk); m_we=1; m_bank=0; m_row=5; m_data='1; tick();
 @(negedge clk); m_we=0; for(integer e=0;e<N;e=e+1) tick();
 f_before=faults_seen; if(f_before==0) begin mism=mism+1; $display("SU_PROGRAMME_PGCOL case c: no fault"); end
 // (a) write on the start edge: start rejected everywhere; ref bank 1 / cluster column 3 bank 0
 do_reset();
 @(negedge clk); p_we=1; p_bank=16'(32*3); p_row=0; p_data=p_cfg[0][255:0]; tick();
 @(negedge clk); p_we=0; for(integer e=1;e<CL;e=e+1) tick();
 @(negedge clk); start=1; m_we=1; m_bank=1; m_row=0; m_data=m_cfg[128][255:0]; tick();
 @(negedge clk); start=0; m_we=0; for(integer e=0;e<40;e=e+1) tick();
 if(faults_seen==f_before) begin mism=mism+1; $display("SU_PROGRAMME_PGCOL case a: no fault"); end
 if(m_busy || p_busy) begin mism=mism+1; $display("SU_PROGRAMME_PGCOL case a: busy"); end
 f_before=faults_seen;
 // (b) write to no column (out of range)
 do_reset();
 @(negedge clk); p_we=1; p_bank=16'hffff; tick();
 @(negedge clk); p_we=0; for(integer e=1;e<CL;e=e+1) tick();
 @(negedge clk); m_we=1; m_bank=16'hffff; tick();
 @(negedge clk); m_we=0; for(integer e=0;e<40;e=e+1) tick();
 if(faults_seen==f_before) begin mism=mism+1; $display("SU_PROGRAMME_PGCOL case b: no fault"); end
 if(mism!=0) $fatal(1,"SU_PROGRAMME_PGCOL FAIL mismatches=%0d active=%0d checked=%0d",mism,active,checked);
 $display("SU_PROGRAMME_PGCOL PASS edges=%0d active=%0d checked=%0d cols=%0d ref_macros=%0d fault_cases=3",
   N,active,checked,CL_NC,REF_MACROS);
 $finish;
end
endmodule
