`timescale 1ns/1ps
// H-SU 2026-10-16: lockstep equivalence of ot_hbm_su_programme_part (PARTS per-quarter producers) against the
// monolithic ot_hbm_su_programme on the same compiled image. The partitioned producer gets start DEPTH edges before
// the monolithic one (the compiler's start advance); from then on every output (command, valid, done, edge_index, busy,
// fault) must be identical on EVERY edge, through two complete executions (restart without reload), and the command
// must equal the golden image line. Mutants: +MUT_TEMPLATE (one dictionary word of producer 2), +MUT_PCOFF (producer
// 3 index table one edge off = PC offset), build -GMUT=1 (producer MUT_SLICE start one edge late = phase).
module tb_hbm_su_programme_part;
`include "mono/programme_params.svh"
`include "part_params.svh"
localparam integer B=PROGRAMME_BITS, N=PART_EDGES, WM=PROGRAMME_WRITES, WP=PART_WRITES;
parameter integer MUT=0;
logic clk=0; always #5 clk=~clk;
logic rst_n=0;
logic m_we=0, p_we=0, m_start=0, p_start=0;
logic [15:0] m_bank=0, p_bank=0; logic [6:0] m_row=0, p_row=0; logic [255:0] m_data=0, p_data=0;
wire m_busy,m_valid,m_done,m_fault,p_busy,p_valid,p_done,p_fault;
wire [15:0] m_edge,p_edge; wire [B-1:0] m_cmd,p_cmd;
reg [279:0] m_cfg[0:WM-1]; reg [279:0] p_cfg[0:WP-1]; reg [B-1:0] golden[0:N-1];
string dir; integer mut_template, mut_pcoff, mism, checked, active;
ot_hbm_su_programme #(.LINE_BITS(B),.COLS(PROGRAMME_COLS),.EDGES(N),.DICT_BANKS(PROGRAMME_DICT_BANKS),
 .MACROS(PROGRAMME_MACROS)) u_mono(
 .clk(clk),.clk_macro({PROGRAMME_MACROS{clk}}),.rst_n(rst_n),.cfg_we(m_we),.cfg_bank(m_bank),.cfg_row(m_row),
 .cfg_data(m_data),.start(m_start),.length(16'(N)),.busy(m_busy),.valid(m_valid),.done(m_done),.fault(m_fault),
 .edge_index(m_edge),.command(m_cmd));
ot_hbm_su_programme_part #(.LINE_BITS(B),.EDGES(N),.PARTS(PART_N),.DEPTH(PART_DEPTH),.SCOLS(PART_COLS),
 .SMACROS(PART_SMACROS),.DICT_BANKS(PART_DICT_BANKS),.MACROS(PART_MACROS),.MUT(MUT),.MUT_SLICE(1)) u_part(
 .clk(clk),.clk_macro({PART_MACROS{clk}}),.rst_n(rst_n),.cfg_we(p_we),.cfg_bank(p_bank),.cfg_row(p_row),
 .cfg_data(p_data),.start(p_start),.length(16'(N)),.busy(p_busy),.valid(p_valid),.done(p_done),.fault(p_fault),
 .edge_index(p_edge),.command(p_cmd));
task automatic tick; @(posedge clk); #1; endtask
// compare after every edge
always @(posedge clk) if(rst_n && checked>=0) begin
  #2;
  if(p_cmd!==m_cmd || p_valid!==m_valid || p_done!==m_done || p_edge!==m_edge || p_busy!==m_busy || p_fault!==m_fault) begin
    mism=mism+1;
    if(mism<=4) $display("SU_PROGRAMME_PART_MISMATCH t=%0t valid=%b/%b edge=%0d/%0d done=%b/%b busy=%b/%b fault=%b/%b cmd_eq=%b",
      $time,p_valid,m_valid,p_edge,m_edge,p_done,m_done,p_busy,m_busy,p_fault,m_fault,p_cmd===m_cmd);
  end
  if(m_valid) begin
    active=active+1;
    if(m_cmd!==golden[m_edge]) begin mism=mism+1; if(mism<=4) $display("SU_PROGRAMME_PART_GOLDEN_MISMATCH edge=%0d",m_edge); end
  end
  checked=checked+1;
end
task automatic execute;
 @(negedge clk); p_start=1; tick(); @(negedge clk); p_start=0;
 for(integer d=1;d<PART_DEPTH;d=d+1) begin tick(); @(negedge clk); end
 m_start=1; tick(); @(negedge clk); m_start=0;
 for(integer e=0;e<N+8;e=e+1) tick();
endtask
initial begin
 checked=-1; mism=0; active=0;
 if(!$value$plusargs("DIR=%s",dir)) $fatal(1,"DIR required");
 mut_template=$test$plusargs("MUT_TEMPLATE"); mut_pcoff=$test$plusargs("MUT_PCOFF");
 $readmemh({dir,"/mono/config.mem"},m_cfg);
 if(mut_pcoff) $readmemh({dir,"/config_mut_pc.mem"},p_cfg); else $readmemh({dir,"/config.mem"},p_cfg);
 $readmemh({dir,"/expected.mem"},golden);
 tick(); @(negedge clk); rst_n=1;
 for(integer i=0;i<WM;i=i+1) begin
   m_we=1; m_bank=m_cfg[i][279:264]; m_row=m_cfg[i][262:256]; m_data=m_cfg[i][255:0]; tick(); @(negedge clk);
 end
 m_we=0;
 for(integer i=0;i<WP;i=i+1) begin
   p_we=1; p_bank=p_cfg[i][279:264]; p_row=p_cfg[i][262:256]; p_data=p_cfg[i][255:0];
   // producer 2's first dictionary bank, row 0 (global bank = base_2 + its index banks)
   if(mut_template && p_bank==16'(2*PART_SMACROS[31:0]+PART_FIRST_DICT) && p_row==0) p_data=p_data^256'h1;
   tick(); @(negedge clk);
 end
 p_we=0; for(integer i=0;i<4;i=i+1) tick();
 checked=0;
 execute(); execute();
 if(m_fault || p_fault) begin mism=mism+1; $display("SU_PROGRAMME_PART fault m=%b p=%b",m_fault,p_fault); end
 if(mism!=0 || active!=2*N) $fatal(1,"SU_PROGRAMME_PART FAIL mismatches=%0d active=%0d of %0d checked=%0d",mism,active,2*N,checked);
 $display("SU_PROGRAMME_PART PASS edges=%0d active=%0d checked=%0d parts=%0d depth=%0d macros=%0d mono_macros=%0d",
   N,active,checked,PART_N,PART_DEPTH,PART_MACROS,PROGRAMME_MACROS);
 $finish;
end
endmodule
