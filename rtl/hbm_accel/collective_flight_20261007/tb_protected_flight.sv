`timescale 1ns/1ps
module tb_protected_flight;
 localparam W=545,D=14;
 reg clk=0;always #0.416667 clk=~clk;
 reg rst_n=0,in_v=0,out_r=0;reg[W-1:0] in_d=0;
 wire in_r,out_v,quiet,fault;wire[W-1:0] out_d;
 ot_hbm_collective_protected_flight #(.ENABLE(1),.W(W),.D(D)) dut(.*);
 wire off_ir,off_ov,off_q,off_f;wire[W-1:0] off_d;
 ot_hbm_collective_protected_flight off(.clk(clk),.rst_n(rst_n),.in_v(in_v),.in_r(off_ir),.in_d(in_d),.out_v(off_ov),.out_r(out_r),.out_d(off_d),.quiet(off_q),.fault(off_f));
 integer cycle=0,sent=0,got=0,last_pop=-2,run=0,max_run=0,stall_checks=0,ce_checks=0;
 integer accepted[0:2047];reg[W-1:0] expected[0:2047];
 function automatic[W-1:0] datum(input integer n);
  reg[W-1:0] v;begin for(integer k=0;k<W;k=k+1)v[k]=((n*17+k*31)>>(k%19))&1;datum=v;end
 endfunction
 always @(posedge clk)begin
  cycle=cycle+1;
  if(rst_n)begin
   if(off_ir!==0||off_ov!==0||off_q!==0||off_f!==0||off_d!==0)$fatal(1,"default off");
   if(in_v&&in_r)begin expected[sent]=in_d;accepted[sent]=cycle;sent=sent+1;end
   if(out_v&&out_r)begin
    if(got>=sent||out_d!==expected[got])$fatal(1,"DATA mismatch got=%0d",got);
    if(cycle-accepted[got]<D)$fatal(1,"early delivery");
    if(cycle==last_pop+1)run=run+1;else run=1;
    if(run>max_run)max_run=run;last_pop=cycle;got=got+1;
   end
  end
 end
 task tick;begin @(posedge clk);#0.02;@(negedge clk);end endtask
 task cold;begin rst_n=0;in_v=0;out_r=0;repeat(3)tick;rst_n=1;tick;end endtask
 reg[W-1:0] held;
 initial begin
  cold;
  if(!quiet)$fatal(1,"reset not quiet");
  // Fixed full-width stream; finite calendar derived from 512 transfers and
  // sink schedule, rather than a process wall-time limit.
  for(integer c=0;c<1800;c=c+1)begin
   in_v=sent<512;in_d=datum(sent);out_r=(c%17>=5)||(c<150);
   tick;
  end
  in_v=0;out_r=1;repeat(30)tick;
  if(sent!=512||got!=512||!quiet||fault||max_run<50)$fatal(1,"stream count/II/quiet");
  // Fill all fourteen stages and stall final consumer.
  out_r=0;in_v=1;
  repeat(D)begin in_d=datum(sent);tick;end
  in_v=0;
  if(quiet||in_r||!out_v)$fatal(1,"full stall contract");
  held=out_d;
  repeat(9)begin tick;if(out_d!==held||!out_v||in_r||quiet)$fatal(1,"held output");stall_checks=stall_checks+1;end
  // Correctable data bit in held output must not leak changed data.
  dut.g_on.g_stage[13].u_bank.code[0]=dut.g_on.g_stage[13].u_bank.code[0]^72'h4;
  #0.01;
  if(out_v||in_r||quiet||fault||out_d!==held)$fatal(1,"CE permission/held payload");
  repeat(7)begin tick;if(out_d!==held||in_r||quiet||fault)$fatal(1,"CE held output");ce_checks=ce_checks+1;end
  if(!out_v)$fatal(1,"CE recovery");
  // CE in encoded valid bit word, and CE on an interior stage.
  dut.g_on.g_stage[13].u_bank.code[8]=dut.g_on.g_stage[13].u_bank.code[8]^72'h8000000000;
  repeat(7)tick;
  dut.g_on.g_stage[5].u_bank.code[2]=dut.g_on.g_stage[5].u_bank.code[2]^72'h8;
  repeat(7)tick;
  out_r=1;repeat(35)tick;
  if(got!=sent||!quiet||fault)$fatal(1,"CE drain");
  // A latent empty-stage UE must fail closed, not be overwritten by a push.
  dut.g_on.g_stage[2].u_bank.code[0]=dut.g_on.g_stage[2].u_bank.code[0]^72'h3;
  #0.01;if(!fault||in_r||out_v||quiet)$fatal(1,"UE fail closed");
  in_v=1;repeat(8)tick;if(!fault||in_r||out_v)$fatal(1,"UE sticky");
  cold;
  dut.g_on.g_stage[8].u_bank.code[9]=dut.g_on.g_stage[8].u_bank.code[9]^72'h1;
  #0.01;if(!fault||in_r||out_v||quiet)$fatal(1,"repair controller corruption");
  repeat(3)tick;
  $display("PASS flight W=%0d D=%0d sent=%0d got=%0d consecutive=%0d stalls=%0d CE_hold=%0d",W,D,sent,got,max_run,stall_checks,ce_checks);
  $finish;
 end
endmodule
