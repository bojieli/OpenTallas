`timescale 1ns/1ps
module tb_s81_hcx_post_gain_native;
 parameter integer MUT_GAIN=0,MUT_MODE=0;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,start=0,gain_mode=0,draft=0,ffn=0;
 wire done,fault,rv,wv;wire[13:0]ra,wa;wire[15:0]wm;wire[511:0]wd;
 reg[511:0]raw0[0:1],raw1[0:1],want0[0:1],want1[0:1],mem[0:16383];
 reg[31:0]eps[0:0],g0[0:5119],g1[0:5119];
 reg[15:0]writem[0:3];reg[3:0]readv=0,writev=0;reg[511:0]readd[0:3],writed[0:3];reg[13:0]writea[0:3];
 integer cyc=0,t0,n,errs=0,gain_rows=0;string dir,gdir;
 ot_s81_hcx_post_gain_native #(.MUT_GAIN(MUT_GAIN))u(
  .clk(clk),.rst_n(rst_n),.start(start),.gain_mode(gain_mode),.gain_draft(draft),.ffn(ffn),
  .raw_base_row(14'd2624),.coef_base_row(14'd2560),.gain_base_row(14'd4096),.layer_idx(6'd0),
  .norm_eps(eps[0]),.compiled_cycles(16'd540),.done(done),.fault(fault),
  .rq_v(rv),.rq_row(ra),.rs_v(readv[3]),.rs_d(readd[3]),
  .wq_v(wv),.wq_row(wa),.wq_mask(wm),.wq_d(wd),.wq_commit(writev[3]));
 always@(posedge clk)begin
  cyc<=cyc+1;readv[0]<=rv;readd[0]<=ffn?raw1[ra-2624]:raw0[ra-2624];
  writem[0]<=wm;writev[0]<=wv;writed[0]<=wd;writea[0]<=wa;
  for(integer i=1;i<4;i=i+1)begin readv[i]<=readv[i-1];readd[i]<=readd[i-1];writem[i]<=writem[i-1];writev[i]<=writev[i-1];writed[i]<=writed[i-1];writea[i]<=writea[i-1];end
  if(wv&&gain_mode&&wm!=16'hffff)$fatal(1,"bad shared VM mask");
  if(writev[3])for(integer lane=0;lane<16;lane=lane+1)if(writem[3][lane])mem[writea[3]][32*lane+:32]<=writed[3][32*lane+:32];
 end
 initial begin
  if(!$value$plusargs("DIR=%s",dir)||!$value$plusargs("GAIN=%s",gdir))$fatal(1,"fixture dirs");
  $readmemh({dir,"/raw0.mem"},raw0);$readmemh({dir,"/raw1.mem"},raw1);$readmemh({dir,"/coef0.mem"},want0);$readmemh({dir,"/coef1.mem"},want1);$readmemh({dir,"/eps.mem"},eps);
  $readmemh({gdir,"/gain0.mem"},g0);$readmemh({gdir,"/gain1.mem"},g1);
  repeat(4)@(negedge clk);rst_n=1;
  // Both coefficient jobs, both gain vectors, then both coefficient jobs again
  // WITHOUT reset or image replacement prove actual shared ROM preservation.
  for(integer job=0;job<6;job=job+1)begin
   gain_mode=(job==2||job==3);draft=job==3;ffn=job%2;
   start=1;t0=cyc;@(negedge clk);start=0;
   while(!done&&cyc-t0<2000)begin
    if(MUT_MODE&&job==2&&cyc-t0==20)gain_mode=0;
    @(negedge clk);
   end
   if(!done)$fatal(1,"fixed completion absent");
   if(job==2||job==3)begin
    if(cyc-t0!=327)$fatal(1,"gain calendar shifted %0d",cyc-t0);
    for(integer q=0;q<320;q=q+1)for(integer lane=0;lane<16;lane=lane+1)
     if(mem[4096+q][32*lane+:32] !== (draft?g1[16*q+lane]:g0[16*q+lane]))errs=errs+1;
    gain_rows=gain_rows+320;
   end else begin
    if(cyc-t0!=541)$fatal(1,"post calendar shifted %0d",cyc-t0);
    if(mem[2560] !== (ffn?want1[0]:want0[0]) || mem[2561] !== (ffn?want1[1]:want0[1]))errs=errs+1;
   end
   if(fault)$fatal(1,"shared owner fault job%0d",job);
   repeat(8)@(negedge clk);
  end
  $display("S81_POST_GAIN_SHARED jobs6 gainrows%0d errors%0d fault%0d",gain_rows,errs,fault);
  if(errs)$fatal(1,"shared gain arithmetic mismatch");$finish;
 end
 initial begin #100000;$fatal(1,"timeout");end
endmodule
