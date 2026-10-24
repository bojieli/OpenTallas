`timescale 1ns/1ps
// HBM-P5-RTLA (2026-10-23): trace form of tb_hgi_coll_tkm_static_p.  The in-tb pinned reference made the TP192
// top-level verilation exceed 290 GB (two 32-tile roots in one model), so the lock-step is done OFFLINE: this tb
// instantiates ONE engine -- PINNED 1: the pinned ot_hgi_coll_tkm_static; PINNED 0: the twin ot_hgi_coll_tkm_static_p
// #(PIPE,MUTP) -- checks the golden O/R words + timeline as before, and writes every write/done/fault event with its
// edge index after start to +TRACE.  tkm_trace_lockstep.py then requires twin event e == pinned event e at +2*PIPE.
module tb_hgi_coll_tkm_static_pt;
 parameter integer KMAX=2048,MUT=0,TP=96,TIE_W_MUT=0,PIPE=1,MUTP=0,PINNED=0;
 reg clk=0,rst_n=0,start=0;always #0.4167 clk=~clk;
 reg[31:0]cfg[0:15],a[0:TP*2048-1],b[0:TP*2048-1],eo[0:2047],er[0:2047],ns[0:TP-1];
 reg[3:0]slots=0,valids=0;reg[2179:0]flits=0;
 wire wv,busy,done,fault;wire[39:0]wa;wire[15:0]wm;wire[511:0]wd;wire[31:0]cycles;
 integer G,N,K,PF,NOUT,HASR,OB,RB,GB,errs=0,words=0,elapsed=0,expected,slotmut=0,rotate=0;
 bit seeno[0:2047],seenr[0:2047];string dir,tfile;
 wire[31:0]dtick,dingress_end;
 if(PINNED!=0)begin:g_pin
  ot_hgi_coll_tkm_static #(.KMAX(KMAX),.MUT(MUT),.TP(TP),.RANK_W(TIE_W_MUT?7:$clog2(TP)))dut(.clk(clk),.rst_n(rst_n),.start(start),.tile_clk({32{clk}}),.buffer_clk(clk),
  .cfg_n(12'(N)),.cfg_k(13'(K)),.cfg_nout(13'(NOUT)),.cfg_g(8'(G)),.cfg_gbase(8'(GB)),.cfg_pf(16'(PF)),
  .cfg_obase(40'(OB)),.cfg_rbase(40'(RB)),.cfg_has_r(1'(HASR)),.del_slot(slots),.del_valid(valids),.del_flit(flits),
  .w_v(wv),.w_addr(wa),.w_mask(wm),.w_data(wd),.busy(busy),.done(done),.fault(fault),.stat_cycles(cycles));
  assign dtick=dut.tick;assign dingress_end=dut.ingress_end;
 end else begin:g_twin
  ot_hgi_coll_tkm_static_p #(.KMAX(KMAX),.MUT(MUT),.TP(TP),.RANK_W(TIE_W_MUT?7:$clog2(TP)),.PIPE(PIPE),.MUTP(MUTP))dut(.clk(clk),.rst_n(rst_n),.start(start),.tile_clk({32{clk}}),.buffer_clk(clk),
  .cfg_n(12'(N)),.cfg_k(13'(K)),.cfg_nout(13'(NOUT)),.cfg_g(8'(G)),.cfg_gbase(8'(GB)),.cfg_pf(16'(PF)),
  .cfg_obase(40'(OB)),.cfg_rbase(40'(RB)),.cfg_has_r(1'(HASR)),.del_slot(slots),.del_valid(valids),.del_flit(flits),
  .w_v(wv),.w_addr(wa),.w_mask(wm),.w_data(wd),.busy(busy),.done(done),.fault(fault),.stat_cycles(cycles));
  assign dtick=dut.tick;assign dingress_end=dut.ingress_end;
 end
 localparam integer EP=(PINNED!=0)?0:PIPE;
 // event trace: edge index counted from the start edge; one line per write / done / fault change
 integer fd=0,tedge=-1;reg started=0,fault_d=0;
 always @(negedge clk)if(rst_n)begin
  if(start)begin started=1;tedge=0;end else if(started)tedge=tedge+1;
  if(fd!=0&&started&&(wv||done||fault!==fault_d))$fwrite(fd,"%0d %0d %h %h %h %0d %0d\n",tedge,wv,wv?wa:40'd0,wv?wm:16'd0,wv?wd:512'd0,done,fault);
  fault_d=fault;
 end
 function automatic[544:0]make_flit(input integer rank_,f);
  reg[544:0]v;v=0;v[544]=1;v[535:528]=8'(GB+rank_);v[527:512]=16'(rank_*PF+f);
  for(integer j=0;j<8;j=j+1)begin
   v[32*j+:32]=(8*f+j<int'(ns[rank_]))?a[rank_*2048+8*f+j]:32'hffffffff;
   v[256+32*j+:32]=(8*f+j<int'(ns[rank_]))?b[rank_*2048+8*f+j]:32'hffffffff;
  end return v;
 endfunction
 always @(negedge clk)begin
  slots=0;valids=0;flits=0;
  if(busy&&dtick>=8&&dtick<dingress_end&&((dtick-8)%8==0))begin
   for(integer l=0;l<4;l=l+1)begin:drive
    integer ix;ix=((int'(dtick)-8)/8)*4+l;
    if(ix<G*PF)begin slots[l]=1;valids[l]=1;flits[545*l+:545]=make_flit(((ix/PF)+rotate)%G,ix%PF);end
   end
   if(slotmut!=0&&dtick==8)valids[0]=0;
  end
 end
 // An expected-fault case checks the fault only (as tb_hgi_coll_qtkm): its golden O/R are not defined.
 always @(negedge clk)if(rst_n&&wv&&cfg[6]==0&&slotmut==0)begin
  for(integer j=0;j<16;j=j+1)if(wm[j])begin:check_word
   integer ix;ix=int'(wa)+j;
   if(ix>=OB&&ix<OB+NOUT)begin
    if(seeno[ix-OB]||wd[32*j+:32]!==eo[ix-OB])begin errs=errs+1;if(errs<8)$display("MISMATCH O %0d got%h expected%h",ix-OB,wd[32*j+:32],eo[ix-OB]);end
    seeno[ix-OB]=1;words=words+1;
   end else if(HASR&&ix>=RB&&ix<RB+NOUT)begin
    if(seenr[ix-RB]||wd[32*j+:32]!==er[ix-RB])begin errs=errs+1;if(errs<8)$display("MISMATCH R %0d got%h expected%h",ix-RB,wd[32*j+:32],er[ix-RB]);end
    seenr[ix-RB]=1;words=words+1;
   end else begin errs=errs+1;$display("OUTSIDE %0d",ix);end
  end
 end
 initial begin
  if(!$value$plusargs("DIR=%s",dir))$fatal(1,"missing DIR");
  if($value$plusargs("TRACE=%s",tfile))begin fd=$fopen(tfile,"w");if(fd==0)$fatal(1,"cannot open TRACE");end
  if($value$plusargs("SLOT_MUT=%d",slotmut))begin end
  if($value$plusargs("ROTATE=%d",rotate))begin end
  $readmemh({dir,"/cfg.hex"},cfg);$readmemh({dir,"/a.hex"},a);$readmemh({dir,"/b.hex"},b);
  $readmemh({dir,"/o.hex"},eo);$readmemh({dir,"/r.hex"},er);$readmemh({dir,"/n.hex"},ns);
  G=cfg[0];N=cfg[1];K=cfg[2];HASR=cfg[4];NOUT=cfg[5];OB=cfg[9];RB=cfg[10];GB=G>=96?0:(int'(cfg[3])/G)*G;PF=(N+7)/8;
  expected=8+((G*PF+3)/4)*8+2*(3*((KMAX+63)/64)+8)+3*((NOUT+3)/4)+24+1+2*EP;
  repeat(10)@(negedge clk);rst_n=1;repeat(10)@(negedge clk);start=1;@(negedge clk);start=0;
  while(!done&&elapsed<expected+20)begin @(negedge clk);elapsed=elapsed+1;end
  if(!done||cycles!=32'(expected))begin errs=errs+1;$display("TIMELINE got%0d expected%0d done%0d",cycles,expected,done);end
  if(fault!=(cfg[6]!=0||slotmut!=0))begin errs=errs+1;$display("FAULT got%0d",fault);end
  if(cfg[6]==0&&slotmut==0)for(integer i=0;i<NOUT;i=i+1)if(!seeno[i]||(HASR&&!seenr[i]))errs=errs+1;
  repeat(4)@(negedge clk);
  if(fd!=0)begin $fwrite(fd,"END %0d %0d\n",cycles,fault);$fclose(fd);end
  if(errs)$fatal(1,"TKM_STATIC_PT FAIL errors=%0d words=%0d cycles=%0d pinned=%0d pipe=%0d",errs,words,cycles,PINNED,EP);
  $display("TKM_STATIC_PT PASS words=%0d cycles=%0d pinned=%0d pipe=%0d",words,cycles,PINNED,EP);$finish;
 end
endmodule
