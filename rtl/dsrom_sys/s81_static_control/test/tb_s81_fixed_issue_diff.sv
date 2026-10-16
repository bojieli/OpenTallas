`timescale 1ns/1ps
// Differential bench (S-ELEM-PQ 2026-10-15, c9 n4): the frozen issuer (ot_s81_fixed_issue_ref = git HEAD before n4)
// and the n4 issuer (registered one-edge-ahead row hits + parallel event reductions) run the same randomized
// program / job / completion / availability stimulus; every output is compared on every edge.  Stimulus never drives
// a calendar write on the edge a job is accepted (n4 faults it explicitly; the frozen issuer started the job on a
// half-written calendar), see the +concurrent mode for that one documented difference.
module tb_s81_fixed_issue_diff;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,pw_v=0,job_v=0;reg[6:0]pw_a=0;reg[27:0]pw_d=0;
 reg[7:0]plen=0;reg[9:0]user=0;reg[20:0]pos=0,tok=0;
 reg[12:0]av=13'h1fff,dv=0;reg[103:0]dt=0;
 wire jr0,busy0,done0,kd0,sl0,f0,jr1,busy1,done1,kd1,sl1,f1;wire[20:0]kt0,kt1;wire[3:0]c0,c1;wire[1:0]ph0,ph1;
 wire[12:0]cv0,cv1;wire[1091:0]cd0,cd1;wire[31:0]nj0,nc0,nj1,nc1;
 ot_s81_fixed_issue_ref #(.STAGE(5))ref0(.clk(clk),.rst_n(rst_n),.pw_v(pw_v),.pw_a(pw_a),.pw_d(pw_d),.prog_len(plen),
  .job_v(job_v),.job_user(user),.job_pos(pos),.job_tok(tok),.job_rdy(jr0),.busy(busy0),.job_done(done0),.job_kdone(kd0),.done_slot(sl0),.kit_tok(kt0),
  .cmd_v(cv0),.cmd_d(cd0),.engine_available(av),.dn_v(dv),.dn_tag(dt),.fault(f0),.fault_code(c0),.st_jobs(nj0),.st_cmds(nc0),.phase(ph0));
 ot_s81_fixed_issue #(.STAGE(5))dut(.clk(clk),.rst_n(rst_n),.pw_v(pw_v),.pw_a(pw_a),.pw_d(pw_d),.prog_len(plen),
  .job_v(job_v),.job_user(user),.job_pos(pos),.job_tok(tok),.job_rdy(jr1),.busy(busy1),.job_done(done1),.job_kdone(kd1),.done_slot(sl1),.kit_tok(kt1),
  .cmd_v(cv1),.cmd_d(cd1),.engine_available(av),.dn_v(dv),.dn_tag(dt),.fault(f1),.fault_code(c1),.st_jobs(nj1),.st_cmds(nc1),.phase(ph1));
 // program image: n words {addr7,data28}, from the generator
 reg[34:0]pwmem[0:399];initial for(i=0;i<400;i=i+1)pwmem[i]=0;reg[31:0]meta[0:7];
 reg[12:0]due[0:65535];reg[103:0]tags[0:65535];reg[12:0]lat[0:127];
 integer tick=-1,i,e,op,seed,nw,errs=0,cmds=0,jobs=0,faults=0,dones=0,cycles,pwi=-1,pert,concurrent=0,mism_first=-1,sph;
 reg[83:0]cmd;
 initial begin
  if(!$value$plusargs("seed=%d",seed))seed=1;
  if($test$plusargs("concurrent"))concurrent=1;
  $readmemh("prog.hex",pwmem);$readmemh("meta.hex",meta);
  nw=meta[0];plen=meta[1];cycles=meta[2];pert=meta[3];sph=meta[4];
  for(i=0;i<65536;i=i+1)begin due[i]=0;tags[i]=0;end
  repeat(3)@(negedge clk);rst_n=1;
 end
 // stimulus on negedge
 always @(negedge clk)if(rst_n)begin
  dv=due[(tick+1)&65535];dt=tags[(tick+1)&65535];
  pw_v=0;job_v=0;
  if(pwi<nw-1 && !busy0 && ($urandom%4)!=0)begin
   pwi=pwi+1;pw_v=1;pw_a=pwmem[pwi][34:28];pw_d=pwmem[pwi][27:0];
  end else if(pert && ($urandom%997)==0)begin   // illegal write (while busy or random), exercises cfg faults
   pw_v=1;pw_a=$urandom%128;pw_d=$urandom;
  end
  // legal starts: next phase == programmed start phase and the next context free; pert adds random illegal starts
  if((ref0.sealed&&jr0&&((ph0+2'd1)==sph[1:0])&&($urandom%3==0))||(pert&&($urandom%300==0)))begin
   job_v=1;user=$urandom;pos=$urandom;tok=$urandom;
   if(!concurrent&&pw_v&&!busy0)job_v=0;
  end
  av=(pert&&($urandom%50==0))?13'h1fff^(13'd1<<($urandom%13)):13'h1fff;
  if(pert&&($urandom%200==0))begin dv[$urandom%13]=1'b1;dt[8*($urandom%13)+:8]=$urandom;end
 end
 always @(posedge clk)begin
  if(!rst_n)tick=-1;
  else begin
   tick=tick+1;#1;
   for(e=0;e<13;e=e+1)if(cv0[e])begin
    cmd=cd0[84*e+:84];op=cmd[6:0];cmds=cmds+1;
    if(!(pert&&($urandom%61==0)))begin
     due[(tick+lat[op]+((pert&&($urandom%53==0))?1:0))&65535][e]=1;
     tags[(tick+lat[op])&65535][8*e+:8]={cmd[83],7'(op)};
    end
   end
   if(done0)dones=dones+1;
   if({jr0,busy0,done0,kd0,sl0,kt0,cv0,cd0,f0,c0,nj0,nc0,ph0}!=={jr1,busy1,done1,kd1,sl1,kt1,cv1,cd1,f1,c1,nj1,nc1,ph1})begin
    if(errs<5)$display("MISMATCH tick=%0d ref{rdy%b busy%b done%b kd%b sl%b f%b c%0d nj%0d nc%0d cv%h} n4{rdy%b busy%b done%b kd%b sl%b f%b c%0d nj%0d nc%0d cv%h}",
     tick,jr0,busy0,done0,kd0,sl0,f0,c0,nj0,nc0,cv0,jr1,busy1,done1,kd1,sl1,f1,c1,nj1,nc1,cv1);
    if(mism_first<0)mism_first=tick;
    errs=errs+1;
   end
   if(tick==cycles)begin
    $display("DIFF seed=%0d pert=%0d concurrent=%0d len=%0d cycles=%0d jobs=%0d cmds=%0d dones=%0d fault=%0d code=%0d mismatches=%0d first=%0d",
      seed,pert,concurrent,plen,cycles,nj0,cmds,dones,f0,c0,errs,mism_first);
    if(errs)$display("DIFF FAIL");else $display("DIFF PASS");
    $finish;
   end
  end
 end
 initial $readmemh("lat.hex",lat);
endmodule
