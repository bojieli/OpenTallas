`timescale 1ns/1ps
module tb_s81_hcx_post_native;
 localparam integer RL=4,WL=4;
 reg clk=0;always #5 clk=~clk;
 reg rn=0,start=0,ffn=0;reg[15:0]budget;wire done,f,rv,wv;wire[13:0]ra,wa;wire[15:0]wm;wire[511:0]wd;
 reg[511:0]raw0[0:1],raw1[0:1],want0[0:1],want1[0:1],mem[0:1];reg[31:0]eps[0:0];
 reg[RL-1:0]readv=0;reg[511:0]readd[0:RL-1];
 reg[WL-1:0]writev=0;reg[13:0]writea[0:WL-1];reg[15:0]writem[0:WL-1];reg[511:0]writed[0:WL-1];
 integer cyc=0,t0,cost=0,fd;string dir;bit calibrate;
 reg fq=0;reg[4:0]prevstate=31;
 always @(negedge clk)begin
  if(u.core.st!=prevstate)begin $display("HCX_POST_STATE cycle%0d st%0d adapterbusy%0d iss%0d jobdone%0d inflight%0d flt%0d",cyc,u.core.st,u.core.u_rec.busy,u.core.u_rec.iss,u.core.job_done,u.core.outst,u.core.flt);prevstate=u.core.st;end
  if(start)$display("HCX_POST_START cycle%0d ffn%0d ready%0d raw_v%0d busy%0d iss%0d",cyc,ffn,u.ready,u.core.u_rec.raw_v,u.core.u_rec.busy,u.core.u_rec.iss);
  if(u.core.job_v)$display("HCX_POST_JOB cycle%0d ready%0d state%0d",cyc,u.core.job_rdy,u.core.st);
  if(u.actual_done)$display("HCX_POST_ACTUAL_DONE cycle%0d relative%0d",cyc,cyc-t0);
  if(f&&!fq)$display("HCX_POST_FAULT cycle%0d core%0d transport%0d state%0d age%0d limit%0d actual_done%0d hq%0d ha%0d pbusy%0d",cyc,u.core_fault,u.transport_fault,u.core.st,u.age,u.limit,u.actual_done,u.hq,u.ha,u.pbusy);
  fq=f;
 end
`ifdef MUT_POST
 localparam integer MUT=1;
`else
 localparam integer MUT=0;
`endif
 ot_s81_hcx_post_native #(.RL(RL),.WL(WL),.MUT_POST(MUT))u(.clk(clk),.rst_n(rn),.start(start),.ffn(ffn),.layer_idx(6'd0),.raw_base_row(14'd2624),.coef_base_row(14'd2560),.norm_eps(eps[0]),.compiled_cycles(budget),.done(done),.rq_v(rv),.rq_row(ra),.rs_v(readv[RL-1]),.rs_d(readd[RL-1]),.wq_v(wv),.wq_row(wa),.wq_mask(wm),.wq_d(wd),.wq_commit(writev[WL-1]),.fault(f));
 always @(posedge clk)begin
  cyc<=cyc+1;readv[0]<=rv;readd[0]<=ffn?raw1[ra-2624]:raw0[ra-2624];
  for(integer i=1;i<RL;i=i+1)begin readv[i]<=readv[i-1];readd[i]<=readd[i-1];end
  writev[0]<=wv;writea[0]<=wa;writem[0]<=wm;writed[0]<=wd;
  for(integer i=1;i<WL;i=i+1)begin writev[i]<=writev[i-1];writea[i]<=writea[i-1];writem[i]<=writem[i-1];writed[i]<=writed[i-1];end
  if(writev[WL-1])for(integer i=0;i<16;i=i+1)if(writem[WL-1][i])mem[writea[WL-1]-2560][32*i+:32]<=writed[WL-1][32*i+:32];
 end
 initial begin:run
  if(!$value$plusargs("DIR=%s",dir))$fatal(1,"DIR required");
  calibrate=$test$plusargs("CALIBRATE");
  if(!$value$plusargs("COMPILED_CYC=%d",cost))cost=65535;budget=16'(cost);
  $readmemh({dir,"/raw0.mem"},raw0);$readmemh({dir,"/raw1.mem"},raw1);$readmemh({dir,"/coef0.mem"},want0);$readmemh({dir,"/coef1.mem"},want1);$readmemh({dir,"/eps.mem"},eps);
  repeat(3)@(negedge clk);rn=1;
  for(integer block=0;block<(calibrate?1:2);block=block+1)begin
   mem[0]='1;mem[1]='1;ffn=block^$test$plusargs("SWAP");start=1;t0=cyc;@(negedge clk);start=0;
   if(calibrate)begin
    while(!u.actual_done && cyc-t0<10000)@(negedge clk);
    if(!u.actual_done)$fatal(1,"no real core completion");
    $display("HCX_POST_CALIBRATE COMPILED_CYC=%0d",cyc-t0);$finish;
   end else begin
   while(!done && cyc-t0<10000)@(negedge clk);
   if(!done||f||cyc-t0!=cost+1)$fatal(1,"compiled tail timeline failed cost%0d actual%0d fault%0d real_done%0d core%0d transport%0d state%0d age%0d limit%0d",cost,cyc-t0,f,u.actual_done,u.core_fault,u.transport_fault,u.core.st,u.age,u.limit);
   if(mem[0] !== (block?want1[0]:want0[0]) || mem[1] !== (block?want1[1]:want0[1]))$fatal(1,"real coefficient tail/VM layout mismatch block%0d",block);
   fd=$fopen($sformatf("%s/pre%0d.actual.mem",dir,block),"w");
   for(integer i=0;i<4;i=i+1)$fdisplay(fd,"%08x",mem[1][32*i+:32]);
   $fclose(fd);
   $display("HCX_POST block%0d exact32words native_cycles%0d",block,cyc-t0);
   repeat(8)@(negedge clk);
   end
  end
  if(!calibrate)$display("HCX_POST_NATIVE PASS actual HBMHC op2 arithmetic +residentparameterROM+scheduledS81VM");$finish;
 end
 initial begin #220000;$fatal(1,"timeout");end
endmodule
