`timescale 1ns/1ps
// CTLM7: lockstep ot_qfd_xpf_static_schedule (reference) vs ot_qfd_xpf_static_schedule_p
// every output, every edge, constrained-random programs with repeated resets.
// +MUT=1 drives the _p copy with a 1-edge-late start (must FAIL).
module tb_xpf_p_lockstep;
 parameter integer N=4, T=20, ML=0;
 localparam integer IW=(N<2)?1:$clog2(N);
 reg clk=0,rst_n=0; always #1 clk=~clk;
 reg cfg_v,cfg_clear,cfg_seal,start,stop_x; reg [IW-1:0] cfg_index; reg [187:0] cfg_data; reg [IW:0] cfg_count;
 reg [5:0] stage; reg me_issue,su_issue,cp_issue; reg [11:0] me_pc,su_pc,cp_pc;
 wire ra,rb,fa,fb,aa,ab; wire [71:0] xa,xb; wire [31:0] ca,cb;
 integer MUT; reg start_d;
 wire stop_a=aa&&stop_x, stop_b=ab&&stop_x;
 ot_qfd_xpf_static_schedule #(.N(N),.ARM_TRANSPORT_EDGES(T),.MUT_LATE(ML)) ref_i(.clk(clk),.rst_n(rst_n),.cfg_v(cfg_v),.cfg_index(cfg_index),.cfg_data(cfg_data),
  .cfg_clear(cfg_clear),.cfg_seal(cfg_seal),.cfg_count(cfg_count),.start(start),.stop(stop_a),.stage(stage),
  .me_issue(me_issue),.me_pc(me_pc),.su_issue(su_issue),.su_pc(su_pc),.cp_issue(cp_issue),.cp_pc(cp_pc),
  .image_ready(ra),.xpf(xa),.fault(fa),.active(aa),.cycle(ca));
 ot_qfd_xpf_static_schedule_p #(.N(N),.ARM_TRANSPORT_EDGES(T),.MUT_LATE(ML)) dut(.clk(clk),.rst_n(rst_n),.cfg_v(cfg_v),.cfg_index(cfg_index),.cfg_data(cfg_data),
  .cfg_clear(cfg_clear),.cfg_seal(cfg_seal),.cfg_count(cfg_count),.start(MUT==1?start_d:start),.stop(stop_b),.stage(stage),
  .me_issue(me_issue),.me_pc(me_pc),.su_issue(su_issue),.su_pc(su_pc),.cp_issue(cp_issue),.cp_pc(cp_pc),
  .image_ready(rb),.xpf(xb),.fault(fb),.active(ab),.cycle(cb));
 // TB copy of the programmed records (for directed good issues)
 reg [187:0] rec[0:7]; reg [5:0] st0; integer k, cyc, ep, cmp, err, nfault, narm, nclean, phase, t_ph;
 integer seed, noisy;
 function [187:0] mkrec(input integer idx);
  reg [31:0] arm,iss,fw; reg [5:0] stg; reg [1:0] u; reg [11:0] pc; reg [71:0] x;
  begin
   stg=(noisy&&$urandom%8==0)?$urandom%4:0; u=(noisy&&$urandom%16==0)?0:1+$urandom%3; pc=$urandom%4+idx*0;
   arm=$urandom%12; iss=arm+$urandom%6; fw=arm+T+3+((noisy&&$urandom%6==0)?-($urandom%3)-1:$urandom%4);
   x={$urandom,$urandom,$urandom}; x[0]=!noisy||($urandom%8!=0);
   mkrec={fw,iss,arm,stg,u,pc,x};
   if(noisy&&$urandom%10==0)mkrec[0]=0;
  end
 endfunction
 initial begin
  if(!$value$plusargs("MUT=%d",MUT))MUT=0; if(!$value$plusargs("SEED=%d",seed))seed=1;
  void'($urandom(seed));
  cmp=0;err=0;nfault=0;narm=0;nclean=0;
  {cfg_v,cfg_clear,cfg_seal,start,stop_x,me_issue,su_issue,cp_issue}=0;cfg_index=0;cfg_data=0;cfg_count=0;stage=0;me_pc=0;su_pc=0;cp_pc=0;
  for(ep=0;ep<4000;ep=ep+1)begin
   noisy=($urandom%10<3); rst_n=0; @(negedge clk); @(negedge clk); rst_n=1;
   // phase 0: load (some episodes also clear and reload)
   for(k=0;k<N;k=k+1)begin rec[k]=mkrec(k); rec[k][83:72]=k; end
   for(k=0;k<N+2;k=k+1)begin
    @(negedge clk); {cfg_v,cfg_clear,cfg_seal,start,stop_x,me_issue,su_issue,cp_issue}=0;
    if(noisy&&$urandom%12==0)cfg_clear=1;
    else if(k<N||$urandom%3==0)begin cfg_v=1;cfg_index=(noisy&&$urandom%10==0)?$urandom:(k%N);cfg_data=rec[cfg_index%N];
      if(noisy&&$urandom%8==0)begin cfg_data[91:72]=rec[0][91:72]; end end
   end
   @(negedge clk); {cfg_v,cfg_clear,cfg_seal,start,stop_x,me_issue,su_issue,cp_issue}=0;
   cfg_seal=1; cfg_count=(noisy&&$urandom%6==0)?$urandom:(1+$urandom%N);
   @(negedge clk); cfg_seal=0;
   if(noisy&&$urandom%5==0)begin @(negedge clk); cfg_seal=($urandom%2); cfg_clear=($urandom%3==0); start=($urandom%2); end
   // phase 1: start then run
   @(negedge clk); cfg_seal=0; cfg_clear=noisy&&($urandom%6==0); start=1; stage=(noisy&&$urandom%8==0)?$urandom%4:rec[0][91:86];
   for(cyc=0;cyc<60;cyc=cyc+1)begin
    @(negedge clk); {cfg_v,cfg_clear,cfg_seal,start,stop_x,me_issue,su_issue,cp_issue}=0;
    if(noisy&&$urandom%40==0)start=1;
    if(noisy&&$urandom%60==0)cfg_v=1; if(noisy&&$urandom%90==0)cfg_seal=1; if(noisy&&$urandom%90==0)cfg_clear=1;
    if(!aa&&!noisy&&$urandom%3==0)begin start=1; stage=rec[0][91:86]; end
    cfg_index=$urandom; cfg_data={$urandom,$urandom,$urandom,$urandom,$urandom,$urandom};
    // directed: issue exactly on the record issue cycle (ref cycle), sometimes perturbed
    for(k=0;k<N;k=k+1)if(aa&&ca==rec[k][155:124]&&(!noisy||$urandom%8!=0))begin
     case(rec[k][85:84])
      1:begin me_issue=1;me_pc=rec[k][83:72]+((noisy&&$urandom%10==0)?1:0);end
      2:begin su_issue=1;su_pc=rec[k][83:72]+((noisy&&$urandom%10==0)?1:0);end
      3:begin cp_issue=1;cp_pc=rec[k][83:72]+((noisy&&$urandom%10==0)?1:0);end
      default:;
     endcase
    end
    if(noisy&&$urandom%25==0)begin me_issue=1;me_pc=$urandom%5;end
    if(noisy&&$urandom%25==0)begin su_issue=1;su_pc=$urandom%5;end
    if(noisy&&$urandom%25==0)begin cp_issue=1;cp_pc=$urandom%5;end
    stop_x=noisy?((cyc>=12&&$urandom%14==0)||cyc==59&&$urandom%2):(ca==rec[0][187:156]+2||cyc==59);
    if(xa[0])narm=narm+1;
   end
   if(!fa)nclean=nclean+1; else nfault=nfault+1;
  end
  $display("XPF_P_LOCKSTEP %s MUT=%0d N=%0d T=%0d ML=%0d compared=%0d errors=%0d episodes=%0d clean=%0d faulted=%0d arms=%0d",
   (err==0)?"PASS":"FAIL",MUT,N,T,ML,cmp,err,ep,nclean,nfault,narm);
  $finish;
 end
 always @(posedge clk) start_d<=start;
 always @(negedge clk) if(rst_n)begin
  cmp=cmp+1;
  if({ra,fa,aa,xa,ca}!=={rb,fb,ab,xb,cb})begin
   err=err+1; if(err<6)$display("MISMATCH t=%0t ref r%b f%b a%b c%0d x%h | dut r%b f%b a%b c%0d x%h",$time,ra,fa,aa,ca,xa,rb,fb,ab,cb,xb);
  end
 end
endmodule
