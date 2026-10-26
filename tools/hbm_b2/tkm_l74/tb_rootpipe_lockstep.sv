`timescale 1ns/1ps
// Same root boundary stimuli, qualified data comparisons; tile chain intentionally external.
module tb;
parameter MUT=0,BDR=0;
reg clk=0,rst_n=0,start=0;always #1 clk=~clk;
reg[11:0] n=8;reg[12:0]k=64,nout=64;reg[7:0]g=192,gb=0;reg[15:0]pf=1;reg hr=1;
reg[3:0]slots=0;reg[2179:0]flit=0;reg[343:0]up=0;
wire[1:0]wv,busy,done,fault,dv,clr,conv;wire[39:0]wa[2];wire[15:0]wm[2];wire[511:0]wd[2];wire[31:0]cycles[2];wire[343:0]down[2];
integer checks=0,edges=0,round=0;reg active=0;
`define P .KMAX(2048),.TP(192),.PIPE(1),.HOP(2),.FRT(4),.CB(21),.CLRB(0)
`define C(i) .clk(clk),.tile_clk({32{clk}}),.buffer_clk(clk),.rst_n(rst_n),.start(start),.cfg_n(n),.cfg_k(k),.cfg_nout(nout),.cfg_g(g),.cfg_gbase(gb),.cfg_pf(pf),.cfg_obase(40'd0),.cfg_rbase(40'd4096),.cfg_has_r(hr),.del_slot(slots),.del_valid(slots),.del_flit(flit),.w_v(wv[i]),.w_addr(wa[i]),.w_mask(wm[i]),.w_data(wd[i]),.busy(busy[i]),.done(done[i]),.fault(fault[i]),.stat_cycles(cycles[i]),.probe_up(up),.probe_down(down[i]),.probe_dv(dv[i]),.probe_clr(clr[i]),.probe_conv(conv[i])
ot_hgi_coll_tkm_static_p #(`P) refp(`C(0));
ot_hgi_coll_tkm_static_pd #(`P,.MUTP(MUT),.DELIVERED_RESET(BDR)) cand(`C(1));
always @(negedge clk)begin
 if(rst_n&&active)begin
  checks=checks+1;
  if({wv[0],busy[0],done[0],fault[0],cycles[0]} !== {wv[1],busy[1],done[1],fault[1],cycles[1]}) $fatal(1,"ROOTPIPE_LOCKSTEP FAIL control edge%0d round%0d",edges,round);
  if(busy[0] && {dv[0],clr[0],conv[0]} !== {dv[1],clr[1],conv[1]})$fatal(1,"ROOTPIPE_LOCKSTEP FAIL tile control edge%0d",edges);
  if(dv[0] && down[0] !== down[1])$fatal(1,"ROOTPIPE_LOCKSTEP FAIL entries edge%0d",edges);
  if(wv[0] && {wa[0],wm[0],wd[0]} !== {wa[1],wm[1],wd[1]})$fatal(1,"ROOTPIPE_LOCKSTEP FAIL writes edge%0d",edges);
 end
 edges=edges+1;
 slots=refp.expected;
 for(integer l=0;l<4;l=l+1)begin
  flit[545*l+:545]=0;flit[545*l+544]=1;flit[545*l+528+:8]=8'((refp.group_index*4+l)/pf)+gb;flit[545*l+512+:16]=16'(refp.group_index*4+l);
  for(integer j=0;j<8;j=j+1)begin flit[545*l+32*j+:32]=$random;flit[545*l+256+32*j+:32]=$random;end
 end
 for(integer j=0;j<10;j=j+1)up[32*j+:32]=$random;up[343:320]=24'($random);
end
initial begin
 repeat(12)@(negedge clk);rst_n=1;repeat(8)@(negedge clk);
 for(round=0;round<5;round=round+1)begin
  n=12'(8+round*8);pf=16'((n+7)/8);g=8'(192-round*17);nout=13'(64-round*7);k=nout;gb=8'(3*round);hr=round%2;
  start=1;active=0;@(negedge clk);start=0;active=1;
  wait(done[0]);repeat(5)@(negedge clk);
 end
 $display("ROOTPIPE_LOCKSTEP PASS checks=%0d rounds=%0d MUT=%0d BDR=%0d",checks,round,MUT,BDR);$finish;
end
endmodule
