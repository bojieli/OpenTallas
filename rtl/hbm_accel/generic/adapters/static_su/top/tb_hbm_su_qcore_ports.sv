`timescale 1ns/1ps
// Port-move equivalence bench of ot_hbm_su_static_qcore (H-NETLIST 2026-10-15): the drain decode (rf_drain_cmd =
// vmw_cmd[38:37] of slice 0 port 0) and the RF-relay head valid (red_rf_v = red_sv && red_tag[8]) moved from the
// quarter/top compositions into the core. Reference = the core as it was (qcore_base: rf_drain_now input, renamed
// copy of the pre-change source), driven with the composition's own AND. Every output of both cores is compared on
// every edge; red_rf_v is compared against the composition expression. Directed phases (reset between) prove each
// decode case of the drain check; a random phase drives reducer commands (all six ops, random tags incl. tag[8]).
// RTL mutants (-P...MUT=): 16 = drain decode ignores the src bit, 32 = relay valid ignores tag[8]; both must FAIL.
module tb_hbm_su_qcore_ports;
 parameter integer MUT=0;
 reg clk=0; always #5 clk=~clk;
 reg rst_n=0;
 reg [53:0] rf_rd_cmd=0; reg [73:0] red_cmd=0; reg [1:0] dcmd=0; reg [127:0] slice_x=0;
 reg [3:0] rf_wv=0; reg [31:0] rf_wa=0; reg [127:0] rf_wd=0;
 wire [127:0] a_bw,b_bw; wire [35:0] a_bc,b_bc; wire [255:0] a_ds,b_ds; wire a_sv,b_sv,a_f,b_f,b_rv;
 wire [31:0] a_tag,b_tag,a_x,b_x;
 qcore_base u_ref(.clk_rf({64{clk}}),.clk_ctl(clk),.clk_red(clk),.rst_n(rst_n),.rf_rd_cmd(rf_rd_cmd),.red_cmd(red_cmd),
  .rf_drain_now(dcmd[1]&&dcmd[0]),.slice_x(slice_x),.rf_wv(rf_wv),.rf_wa(rf_wa),.rf_wd(rf_wd),.rf_bword(a_bw),
  .rf_bcmd(a_bc),.rf_dsec(a_ds),.red_sv(a_sv),.red_tag(a_tag),.red_x(a_x),.fault(a_f));
 ot_hbm_su_static_qcore #(.MUT(MUT)) u_dut(.clk_rf({64{clk}}),.clk_ctl(clk),.clk_red(clk),.rst_n(rst_n),
  .rf_rd_cmd(rf_rd_cmd),.red_cmd(red_cmd),.rf_drain_cmd(dcmd),.slice_x(slice_x),.rf_wv(rf_wv),.rf_wa(rf_wa),.rf_wd(rf_wd),
  .rf_bword(b_bw),.rf_bcmd(b_bc),.rf_dsec(b_ds),.red_sv(b_sv),.red_tag(b_tag),.red_x(b_x),.red_rf_v(b_rv),.fault(b_f));
 integer errors=0,edges=0,rv1=0,rv0=0,faults_seen=0;
 always @(negedge clk) if(rst_n) begin
  edges=edges+1;
  if({a_bw,a_bc,a_ds,a_sv,a_tag,a_x,a_f}!=={b_bw,b_bc,b_ds,b_sv,b_tag,b_x,b_f})begin
   errors=errors+1; if(errors<6)$display("output mismatch t=%0t fault %b/%b",$time,a_f,b_f); end
  if(b_rv!==(a_sv&&a_tag[8]))begin errors=errors+1; if(errors<6)$display("red_rf_v mismatch t=%0t",$time); end
  if(a_sv&&a_tag[8])rv1=rv1+1; if(a_sv&&!a_tag[8])rv0=rv0+1;
 end
 task automatic do_reset; begin rst_n=0; rf_rd_cmd=0; red_cmd=0; dcmd=0; repeat(3)@(posedge clk); #1 rst_n=1; end endtask
 // drain case: optional class-5 read (addr sector aligned) one edge before dcmd
 task automatic drain_case(input c5, input [1:0] d, input expect_fault);
  begin
   do_reset; repeat(2)@(posedge clk); #1;
   rf_rd_cmd[5*9+:9]=c5?{1'b1,2'd1,3'd2,3'd0}:9'd0; @(posedge clk); #1;
   rf_rd_cmd[5*9+:9]=0; dcmd=d; @(posedge clk); #1; dcmd=0; repeat(3)@(posedge clk); #1;
   if(a_f!==expect_fault)begin errors=errors+1; $display("drain case c5=%0d d=%b: ref fault %b expected %b",c5,d,a_f,expect_fault); end
   if(a_f)faults_seen=faults_seen+1;
  end
 endtask
 integer i;
 initial begin
  drain_case(1,2'b11,0);   // legal RF drain
  drain_case(0,2'b11,1);   // RF drain without the class-5 read -> FAULT
  drain_case(0,2'b10,0);   // valid vmw command, src 0 (not RF): no class-5 needed
  drain_case(0,2'b01,0);   // src bit without valid
  drain_case(1,2'b00,0);
  // random phase: RF writes, broadcast reads, reducer commands with random ops/tags
  do_reset;
  for(i=0;i<4000;i=i+1)begin
   @(posedge clk); #1;
   rf_wv=$random; rf_wa={$random}; rf_wd={$random,$random,$random,$random};
   rf_wv=rf_wv&4'b0001;           // one writer an edge (no compile-time conflict)
   rf_rd_cmd[0+:45]={$random,$random}; rf_rd_cmd[5*9+:9]=0; dcmd=0;
   slice_x={$random,$random,$random,$random};
   red_cmd=0;
   if(($random&3)==0)begin
    red_cmd[73]=1; red_cmd[72:70]=$urandom%6; red_cmd[69:60]=$urandom%16; red_cmd[59:50]=$urandom%16;
    red_cmd[49:40]=$urandom%16; red_cmd[39:8]={$random}; red_cmd[7]=$random; red_cmd[6:0]=$random;
   end
  end
  red_cmd=0; repeat(30)@(posedge clk); #1;
  $display("QCORE_PORTS edges=%0d errors=%0d scalars_rf=%0d scalars_norf=%0d drain_faults=%0d",edges,errors,rv1,rv0,faults_seen);
  if(rv1==0||rv0==0)begin errors=errors+1; $display("random phase did not exercise both tag[8] values"); end
  if(errors)$fatal(1,"QCORE_PORTS FAIL errors=%0d",errors);
  $display("QCORE_PORTS PASS"); $finish;
 end
endmodule
