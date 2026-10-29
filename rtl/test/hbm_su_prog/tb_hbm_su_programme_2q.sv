`timescale 1ns/1ps
module tb_hbm_su_programme_2q;
`include "root5_params.svh"
localparam P=R5_PARTS, SB=R5_SB, N=R5_EDGES, B=P*SB;
logic clk=0; always #0.4165 clk=~clk;
logic rst_n=0,cfg_we=0,start=0;
logic [15:0] cfg_bank=0; logic [6:0] cfg_row=0; logic [255:0] cfg_data=0;
wire r_start,fault; wire [15:0] r_len; wire [P-1:0] r_we,q_fault,q_busy,q_valid,q_done;
wire [16*P-1:0] r_bank,q_edge; wire [6:0] r_row; wire [255:0] r_data; wire [B-1:0] command;
reg [279:0] cfg[0:R5_WRITES-1]; reg [B-1:0] golden[0:N-1];
string dir; integer cycle=0,start_cycle=-1,first_age=-1,count=0,dones=0;
ot_hbm_su_programme_root_h5 #(.PARTS(P)) u_root(.clk,.rst_n,.cfg_we,.cfg_bank,.cfg_row,.cfg_data,.start,
 .length(16'(N)),.p_fault(q_fault),.r_start,.r_len,.r_we,.r_bank,.r_row,.r_data,.fault);
for(genvar k=0;k<P;k++) begin:g_q
 ot_hbm_su_programme_pslice_c5 #(.SB(SB),.NC(R5_NC),.DICT_CAP(R5_CAP)) u_slice(
 .clk,.rst_n,.cfg_we(r_we[k]),.cfg_bank(r_bank[16*k+:16]),.cfg_row(r_row),.cfg_data(r_data),
 .start(r_start),.length(r_len),.busy(q_busy[k]),.valid(q_valid[k]),.done(q_done[k]),
 .fault(q_fault[k]),.edge_index(q_edge[16*k+:16]),.command(command[SB*k+:SB]));
end
always @(posedge clk) begin
 cycle=cycle+1;
 if(start) start_cycle=cycle;
 // Post-NBA presentation age; a downstream always_ff consumes this word one edge later.
 #0.01;
 if(rst_n) begin
  if(fault || |q_fault) $fatal(1,"2Q_FAULT cycle=%0d",cycle);
  if(q_valid!=={P{q_valid[0]}} || q_done!=={P{q_done[0]}}) $fatal(1,"2Q_PART_PHASE");
  if(q_valid[0]) begin
   for(integer k=0;k<P;k++) if(q_edge[k*16+:16]!==16'(count)) $fatal(1,"2Q_INDEX part=%0d edge=%0d count=%0d",k,q_edge[k*16+:16],count);
   if(command!==golden[count]) $fatal(1,"2Q_COMMAND_MISMATCH edge=%0d",count);
   if(first_age<0) first_age=cycle-start_cycle;
   count=count+1;
  end
  if(q_done[0]) dones=dones+1;
 end
end
initial begin
 if(!$value$plusargs("DIR=%s",dir)) $fatal(1,"missing DIR");
 if($test$plusargs("MUT_CFG")) $readmemh({dir,"/config_mut.mem"},cfg); else $readmemh({dir,"/config.mem"},cfg);
 $readmemh({dir,"/expected.mem"},golden);
 repeat(5) @(negedge clk); rst_n=1; repeat(8) @(negedge clk);
 for(integer i=0;i<R5_WRITES;i++) begin
  cfg_we=1; cfg_bank=cfg[i][279:264];cfg_row=cfg[i][262:256];cfg_data=cfg[i][255:0]; @(negedge clk);
 end
 cfg_we=0; repeat(12) @(negedge clk); start=1; @(negedge clk);start=0;
 repeat(N+40) @(negedge clk);
 if(count!=N || dones!=1) $fatal(1,"2Q_COUNTS count=%0d dones=%0d",count,dones);
 $display("SU_PROGRAMME_2Q_PASS parts=%0d sb=%0d edges=%0d first_age=%0d checked_bits=%0d",P,SB,N,first_age,N*B);$finish;
end
endmodule
