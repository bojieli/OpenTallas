`timescale 1ns/1ps
// HBM-IDX6 FAN32 lockstep equivalence bench: the FAN32 quadrant ot_hidx_s3_q / ctl ot_hidx_s3_ctl against the
// census-failing s3 originals (ot_hidx_s3_q_ref / ot_hidx_s3_ctl_ref, fb02fa82f), cycle by cycle on EVERY output port,
// under random control words (all ops 0..8, random pass/addr), random thresholds / ties / lines / returned streams, and
// random mid-run resets (op 0 around them).  DMUT/CMUT apply to the NEW design only (the bench must then FAIL).
// PASS line: "S3_EQUIV PASS ..."; any port difference prints "S3_EQUIV FAIL ..." and exits 1.
module tb_hidx_s3_equiv;
 parameter integer DMUT=0;        // quadrant mutant on the new design (1, 3, 5)
 parameter integer CMUT=0;        // ctl mutant on the new design (6)
 parameter integer CYC=200000;
 parameter integer FAST_COUNT=0;
 parameter integer PIPE_HAZARD=0;
 reg clk=0;reg runclk=1;always #1 if(runclk)clk=~clk;
 reg rst_n=0;
 reg [13:0] cw;reg [15:0] thr;reg [13:0] ties;reg [591:0] in_line;
 wire [24:0] ret_n,ret_r;wire qf_n,qf_r,sv_n,sv_r;wire [591:0] sl_n,sl_r;
 ot_hidx_s3_q #(.DMUT(DMUT),.FAST_COUNT(FAST_COUNT),.PIPE_HAZARD(PIPE_HAZARD)) u_n(.clk(clk),.rst_n(rst_n),.cw(cw),.thr(thr),.ties(ties),.in_line(in_line),
  .ret(ret_n),.qfault_o(qf_n),.selected_v_o(sv_n),.selected_line_o(sl_n));
 ot_hidx_s3_q #(.DMUT(0),.FAST_COUNT(0),.PIPE_HAZARD(0)) u_r(.clk(clk),.rst_n(rst_n),.cw(cw),.thr(thr),.ties(ties),.in_line(in_line),
  .ret(ret_r),.qfault_o(qf_r),.selected_v_o(sv_r),.selected_line_o(sl_r));
 reg [3:0] op;reg [1:0] pass;reg [7:0] addr;reg [9:0] k;
 reg [24:0] rq[0:3];reg [3:0] qf;
 wire [13:0] ccw_n,ccw_r;wire [15:0] cthr_n,cthr_r;wire [13:0] ct_n[0:3],ct_r[0:3];wire cf_n,cf_r;
 ot_hidx_s3_ctl #(.DMUT(CMUT)) c_n(.clk(clk),.rst_n(rst_n),.op(op),.pass(pass),.addr(addr),.k(k),.cw(ccw_n),.thr(cthr_n),
  .ties_0(ct_n[0]),.ties_1(ct_n[1]),.ties_2(ct_n[2]),.ties_3(ct_n[3]),.ret_0(rq[0]),.ret_1(rq[1]),.ret_2(rq[2]),.ret_3(rq[3]),
  .qf_0(qf[0]),.qf_1(qf[1]),.qf_2(qf[2]),.qf_3(qf[3]),.fault(cf_n));
 ot_hidx_s3_ctl_ref #(.DMUT(0)) c_r(.clk(clk),.rst_n(rst_n),.op(op),.pass(pass),.addr(addr),.k(k),.cw(ccw_r),.thr(cthr_r),
  .ties_0(ct_r[0]),.ties_1(ct_r[1]),.ties_2(ct_r[2]),.ties_3(ct_r[3]),.ret_0(rq[0]),.ret_1(rq[1]),.ret_2(rq[2]),.ret_3(rq[3]),
  .qf_0(qf[0]),.qf_1(qf[1]),.qf_2(qf[2]),.qf_3(qf[3]),.fault(cf_r));
 // A priced pipeline changes only fault/status and its private counter by1edge.
 reg qf_ref_d=0;reg [13:0] selected_ref_d=0;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin qf_ref_d<=0;selected_ref_d<=0;end
  else begin qf_ref_d<=qf_r;selected_ref_d<=u_r.selected;end
 end
 wire qf_expected=PIPE_HAZARD?(rst_n?qf_ref_d:qf_r):qf_r; // reset assertion clears both fault paths together
 always @(negedge clk)if(PIPE_HAZARD&&rst_n&&u_n.selected!==selected_ref_d)
  $fatal(1,"S3_COUNT_PIPE_MISMATCH new=%h ref_delayed=%h",u_n.selected,selected_ref_d);
 // Exact recurrence observation catches arithmetic mutations even before a sticky
 // schedule fault reaches the public port. Both state words retain the same reset.
 always @(negedge clk) if(FAST_COUNT&&!PIPE_HAZARD&&rst_n&&u_n.selected!==u_r.selected)
  $fatal(1,"S3_FAST_COUNT_MISMATCH new=%h ref=%h",u_n.selected,u_r.selected);
 function automatic [3:0] rop(input integer r);
  integer x;x=r%100;
  if(x<18)rop=0;else if(x<38)rop=2;else if(x<48)rop=4;else if(x<78)rop=6;else if(x<83)rop=1;else if(x<88)rop=3;
  else if(x<93)rop=5;else if(x<98)rop=7;else rop=8;
 endfunction
 integer cyc,errs,quiet,seed,nsel,nret,ncf,nqf,nrst;
 integer i;
 integer async_checks=0;
 reg stopped_reset_covered=0;
 initial begin
  wait(u_n.g_hazard_pipe.v_p!==0 && ^u_n.g_hazard_pipe.v_p!==1'bx);
  @(negedge clk);runclk=0;
  #0.2;
  if(u_n.g_hazard_pipe.v_p===0)$fatal(1,"DIRECTED_RESET_VACUOUS_ZERO");
  $display("DIRECTED_RESET_PRE_NONZERO controls=%h/%h/%h",u_n.g_hazard_pipe.v_p,u_n.g_hazard_pipe.other_p,u_n.g_hazard_pipe.id_p);
  rst_n=0;
  #0.1;
  if(u_n.g_hazard_pipe.v_p!==0||u_n.g_hazard_pipe.other_p!==0||u_n.g_hazard_pipe.id_p!==0)
   $fatal(1,"DIRECTED_ASYNC_RESET_FAIL_WITH_STOPPED_CLOCK");
  stopped_reset_covered=1;
  $display("DIRECTED_ASYNC_RESET_STOPPED_CLOCK_PASS");
  #0.4;runclk=1;
 end
 always @(negedge rst_n)begin
  #0.02;
  if(PIPE_HAZARD)begin
   async_checks=async_checks+1;
   if(u_n.g_hazard_pipe.v_p!==0||u_n.g_hazard_pipe.other_p!==0||u_n.g_hazard_pipe.id_p!==0)
    $fatal(1,"STRICT_ASYNC_PIPE_RESET_FAIL controls=%h/%h/%h",u_n.g_hazard_pipe.v_p,u_n.g_hazard_pipe.other_p,u_n.g_hazard_pipe.id_p);
  end
 end
 reg [515:0] common_array_word;reg [255:0] common_read;
 initial begin
  #0.2;
  for(integer ar=0;ar<130;ar=ar+1)begin
   for(integer ab=0;ab<516;ab=ab+1)common_array_word[ab]=$urandom_range(0,1);
   u_n.gm[0].mem.arr[ar]=common_array_word;u_r.gm[0].mem.arr[ar]=common_array_word;
   for(integer ab=0;ab<516;ab=ab+1)common_array_word[ab]=$urandom_range(0,1);
   u_n.gm[1].mem.arr[ar]=common_array_word;u_r.gm[1].mem.arr[ar]=common_array_word;
   for(integer ab=0;ab<516;ab=ab+1)common_array_word[ab]=$urandom_range(0,1);
   u_n.gm[2].mem.arr[ar]=common_array_word;u_r.gm[2].mem.arr[ar]=common_array_word;
  end
  for(integer ab=0;ab<256;ab=ab+1)common_read[ab]=$urandom_range(0,1);
  u_n.gm[0].mem.rd_out=common_read;u_r.gm[0].mem.rd_out=common_read;
  for(integer ab=0;ab<256;ab=ab+1)common_read[ab]=$urandom_range(0,1);
  u_n.gm[1].mem.rd_out=common_read;u_r.gm[1].mem.rd_out=common_read;
  for(integer ab=0;ab<256;ab=ab+1)common_read[ab]=$urandom_range(0,1);
  u_n.gm[2].mem.rd_out=common_read;u_r.gm[2].mem.rd_out=common_read;
  $display("STRICT_RETAINED_INIT physicalbits201240 readbits768 paired_actual_arrays PASS");
 end
 initial begin
  if(!$value$plusargs("seed=%d",seed))seed=1;
  i=$urandom(seed);                     // seed the thread's generator
  errs=0;quiet=0;nsel=0;nret=0;ncf=0;nqf=0;nrst=0;
  cw=0;thr=0;ties=0;in_line=0;op=0;pass=0;addr=0;k=1;qf=0;for(i=0;i<4;i=i+1)rq[i]=0;
  for(cyc=0;cyc<CYC;cyc=cyc+1)begin
   @(negedge clk);
   // reset: first 10 cycles, then random 6-cycle pulses with 8 quiet cycles either side
   if(cyc<10)rst_n=0;
   else if(cyc>20&&quiet==0&&($urandom(seed+cyc)%5000)==0)begin quiet=22;nrst=nrst+1;end
   if(quiet>0)begin quiet=quiet-1;rst_n=!(quiet<14&&quiet>=8);end else if(cyc>=10)rst_n=1;
   cw={8'($urandom),2'($urandom%3),(quiet>0||cyc<12)?4'd0:rop($urandom)};
   if(($urandom%8)!=0)thr=thr;else thr=16'($urandom);
   if(($urandom%8)==0)ties=14'($urandom%40);
   for(i=0;i<16;i=i+1)in_line[i*37+:37]={$urandom,5'($urandom)}|37'(($urandom%3)!=0);
   op=(quiet>0||cyc<12)?4'd0:rop($urandom);pass=2'($urandom%3);addr=8'($urandom);k=10'($urandom%600);
   for(i=0;i<4;i=i+1)rq[i]=($urandom%4==0)?{11'($urandom),14'($urandom)}:{rq[0][24:14],14'($urandom)};
   qf=(($urandom%200)==0)?4'($urandom):4'd0;
   @(posedge clk);#0.1;
   begin // STRICT: compare all public ports on every edge, including reset and quiet cycles
    if(sv_n!==sv_r||sl_n!==sl_r||ret_n!==ret_r||qf_n!==qf_expected)begin
     errs=errs+1;if(errs<=5)$display("S3_EQUIV MISMATCH quadrant cyc %0d sv %b/%b ret %h/%h qf %b/%b line_eq %b",cyc,sv_n,sv_r,ret_n,ret_r,qf_n,qf_r,sl_n===sl_r);
    end
    if(ccw_n!==ccw_r||cthr_n!==cthr_r||cf_n!==cf_r||ct_n[0]!==ct_r[0]||ct_n[1]!==ct_r[1]||ct_n[2]!==ct_r[2]||ct_n[3]!==ct_r[3])begin
     errs=errs+1;if(errs<=5)$display("S3_EQUIV MISMATCH ctl cyc %0d",cyc);
    end
    nsel=nsel+(sv_r&&sl_r!=0);nret=nret+(ret_r[13:0]!=0);ncf=ncf+cf_r;nqf=nqf+qf_r;
   end
  end
  if(!stopped_reset_covered)$fatal(1,"DIRECTED_RESET_NOT_COVERED");
  if(async_checks<25)$fatal(1,"STRICT_ASYNC_RESET_COVERAGE_FAIL checks=%d",async_checks);
  $display("STRICT_ASYNC_PIPE_RESET_PASS checks=%d",async_checks);
  if(errs==0)$display("S3_EQUIV PASS DMUT%0d CMUT%0d cycles %0d seed %0d resets %0d selected_lines %0d nonzero_hist_reads %0d qfault_cycles %0d",DMUT,CMUT,CYC,seed,nrst,nsel,nret,nqf);
  else $fatal(1,"S3_EQUIV FAIL DMUT%0d CMUT%0d errors %0d",DMUT,CMUT,errs);
  $finish;
 end
endmodule
