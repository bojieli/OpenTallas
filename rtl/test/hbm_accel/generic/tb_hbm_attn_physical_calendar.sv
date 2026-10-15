`timescale 1ns/1ps
module tb_hbm_attn_physical_calendar;
 localparam H=16,D=512,TD=32,NL=2,ROWW=4240,NT=32,DPT=16;
 reg clk=0;always #1 clk=~clk;reg rst_n=0;
 reg pwe=0,launch=0;reg[9:0]pa=0,last=0;reg[6:0]pe=0;
 wire[6:0]ev;wire[9:0]phase;wire valid,running,pfault;
 ot_hbm_attn_physical_event_program program_mem(.clk(clk),.rst_n(rst_n),.program_we(pwe),.program_addr(pa),.program_events({21'd0,pe}),.program_profile(2'd0),.launch(launch),.program_last(last),.events(ev),.phase(phase),.valid(valid),.running(running),.fault(pfault));
 integer rows=128,mode=0,mut=0,job=0,qn=0,kn=0,pn=0;wire cf;
 reg[8191:0]q_w;reg[NL*ROWW-1:0]kv_w;reg[NL-1:0]kv_m;reg[1023:0]p_w;
 wire sc_v,pv_v;wire[15:0]sc_row;wire[NL-1:0]sc_m;wire[NL*H*32-1:0]sc_y;wire[NL*H-1:0]sc_f;
 wire[7:0]pv_c;wire[NT*H*32-1:0]pv_y;wire[NT*H-1:0]pv_f;wire qi,pi;
 reg[159:0]jobs[0:1];reg[8191:0]qm[0:31];reg[ROWW-1:0]kvm[0:767];reg[511:0]pm[0:383];
 reg[H*33-1:0]scm[0:767];reg[H*33-1:0]pvm[0:1023];reg[6:0]cal[0:511];
 wire slotq=ev[5]||(mut==2&&valid&&phase==2);
 ot_hdc_v41x_attn_physical_calendar #(.H(H),.D(D),.TD(TD),.NL(NL),.TROWS(640),.SRAM_MACRO(1))dut(
 .clk(clk),.rst_n(rst_n),.job_v(ev[0]),.job_t(16'(rows|(mode?16384:8192))),.calendar_fault(cf),
 .slot_qk(slotq),.slot_fill(ev[4]),.slot_pv(ev[6]),.q_present(!(mut==1)),.kv_present(1'b1),.p_present(1'b1),
 .q_v(ev[1]),.q_w(q_w),.kv_v(ev[2]),.kv_m(kv_m),.kv_w(kv_w),.p_v(ev[3]),.p_w(p_w),
 .sc_v(sc_v),.sc_row(sc_row),.sc_m(sc_m),.sc_y(sc_y),.sc_f(sc_f),
 .pv_v(pv_v),.pv_c(pv_c),.pv_y(pv_y),.pv_f(pv_f),.qk_iss(qi),.pv_iss(pi));
 integer k,h,l,dim,cyc=0,t0=0,nsc=0,npv=0,scase=0,pvcase=0,lastout=0;string dir,fn;reg active=0;
 always @*begin
  q_w=qm[job*H+qn];if(mut==3)q_w[15]=~q_w[15];p_w={pm[(job==0?0:64)+pn+1],pm[(job==0?0:64)+pn]};kv_w=0;kv_m=0;
  for(integer ll=0;ll<NL;ll++)if(kn+ll<rows)begin kv_m[ll]=1;kv_w[ll*ROWW+:ROWW]=kvm[(job==0?0:128)+kn+ll];end
 end
 always @(posedge clk)begin
  cyc<=cyc+1;
  if(rst_n&&active)begin
   if(ev[0])begin qn<=0;kn<=0;pn<=0;end
   if(ev[1])qn<=qn+1;
   if(ev[2])kn<=kn+NL;
   if(ev[3])pn<=pn+2;
  end
 end
 always @(negedge clk)if(active)begin
  if(cf||pfault)$fatal(1,"ATT_CALENDAR fault mode%0d T%0d phase%0d q%0d kv%0d p%0d",mode,rows,phase,qn,kn,pn);
  if(valid&&ev!==cal[phase])$fatal(1,"actual programme ordinal/cycle mismatch");
  if(sc_v)begin
   if(mode!=0)$fatal(1,"PV-only produced score");
   for(integer ll=0;ll<NL;ll++)if(sc_m[ll])for(integer hh=0;hh<H;hh++)begin
    reg[32:0]exp;exp=scm[(job==0?0:128)+sc_row+ll][hh*33+:33];
    if(sc_f[ll*H+hh]!==exp[32]||(!exp[32]&&sc_y[(ll*H+hh)*32+:32]!==exp[31:0]))$fatal(1,"ATT_CALENDAR score mismatch row%0d head%0d",sc_row+ll,hh);
    nsc++;scase++;
   end
   lastout=cyc-t0;
  end
  if(pv_v)begin
   if(mode!=1)$fatal(1,"QK-only produced PV");
   for(integer tt=0;tt<NT;tt++)for(integer hh=0;hh<H;hh++)begin
    reg[32:0]exp;exp=pvm[job*D+tt*DPT+pv_c][hh*33+:33];
    if(pv_f[tt*H+hh]!==exp[32]||(!exp[32]&&pv_y[(tt*H+hh)*32+:32]!==exp[31:0]))$fatal(1,"ATT_CALENDAR PV mismatch dim%0d head%0d",tt*DPT+pv_c,hh);
    npv++;pvcase++;
   end
   lastout=cyc-t0;
  end
 end
 initial begin
  if(!$value$plusargs("DIR=%s",dir))$fatal(1,"DIR required");void'($value$plusargs("MUT=%d",mut));
  $readmemh({dir,"/jobs.hex"},jobs);$readmemh({dir,"/q.hex"},qm);$readmemh({dir,"/kv.hex"},kvm);$readmemh({dir,"/p.hex"},pm);$readmemh({dir,"/sc.hex"},scm);$readmemh({dir,"/pv.hex"},pvm);
  repeat(8)@(negedge clk);rst_n=1;
  for(job=0;job<2;job++)for(mode=0;mode<2;mode++)begin
   rows=job==0?128:640;fn=$sformatf("%s/%s%0d.hex",dir,mode?"pv":"qk",rows);$readmemh(fn,cal);
   // Last event comes directly from compiler output, not a runtime readiness trace.
   last=0;for(k=0;k<512;k++)if(cal[k]!=0)last=10'(k);
   active=0;
   for(k=0;k<512;k++)begin pwe=1;pa=10'(k);pe=cal[k];@(negedge clk);end
   pwe=0;qn=0;kn=0;pn=0;scase=0;pvcase=0;active=1;t0=cyc;
   launch=1;@(negedge clk);launch=0;
   repeat(600)@(negedge clk);
   if((mode==0&&scase!=rows*H)||(mode==1&&pvcase!=H*D))$fatal(1,"ATT_CALENDAR output accounting score%0d PV%0d",scase,pvcase);
   $display("ATT_STATIC_CASE T=%0d mode=%0d actual_H=16 actual_D=512 actual_TD=32 actual_NL=2 FPL=6 FML=8 PWORDS=2 physical_pairs=32 last_issue=%0d launch_to_last_result=%0d scores=%0d pv=%0d",rows,mode,last,lastout,scase,pvcase);
   active=0;repeat(30)@(negedge clk);
  end
  $display("PASS ATT_PHYSICAL_CALENDAR_FULL heads=16 dim=512 rows=128,640 scores=%0d pv=%0d staging_macros=34 programme_macros=1 real_RTL_FP=1",nsc,npv);$finish;
 end
endmodule
