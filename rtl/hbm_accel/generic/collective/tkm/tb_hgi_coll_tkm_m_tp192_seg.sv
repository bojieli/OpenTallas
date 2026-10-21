`timescale 1ns/1ps
// PL-TP192 10-18: the tb_hgi_coll_tkm_static golden bench on the TKM TP192 sub-cluster parents: the flat reference
// ot_hgi_coll_tkm_m_tp192_seg (default) or, with +define+TKM_LP, the generated landed parent ot_hgi_coll_tkm_m_tp192_lp
// (every region clock = clk; its regional reset releases 6 edges after rst_n, before start).  Timeline = tkm_static
// + 2*(XS+PIPE) (XS = 2*HOP*(NSEG-1) = 42: 7 seams, pre-scheduled crossing of 3 edges each way; PIPE 4 = the ctl
// ingress / re-read pipeline, HBM-TP192 10-20).
module tb_hgi_coll_tkm_m_tp192_seg;
 parameter integer KMAX=2048,MUT=0,TP=192,XS=42,PIPE=4,IREG=1;   // HBM-TP192 10-20: ctl PIPE 4 + face flops (IREG 1 in, 1 out)
 reg clk=0,rst_n=0,start=0;always #0.4167 clk=~clk;
 reg[31:0]cfg[0:15],a[0:TP*2048-1],b[0:TP*2048-1],eo[0:2047],er[0:2047],ns[0:TP-1];
 reg[3:0]slots=0,valids=0;reg[2179:0]flits=0;
 wire wv,busy,done,fault;wire[39:0]wa;wire[15:0]wm;wire[511:0]wd;wire[31:0]cycles;
 integer G,N,K,PF,NOUT,HASR,OB,RB,GB,errs=0,words=0,elapsed=0,expected,slotmut=0,rotate=0;
 bit seeno[0:2047],seenr[0:2047];string dir;
`ifdef TKM_LP
 ot_hgi_coll_tkm_m_tp192_lp #(.CTL_MUT(MUT))dut(.ck_SW(clk),.ck_NW(clk),.ck_NE(clk),.ck_SE(clk),.rst_n(rst_n),.start(start),.arg_mode(1'b0),
`else
 ot_hgi_coll_tkm_m_tp192_seg #(.CTL_MUT(MUT))dut(.clk(clk),.rst_n(rst_n),.start(start),.arg_mode(1'b0),.tile_clk({32{clk}}),.buffer_clk(clk),
`endif
 .cfg_n(12'(N)),.cfg_k(13'(K)),.cfg_nout(13'(NOUT)),.cfg_g(8'(G)),.cfg_gbase(8'(GB)),.cfg_pf(16'(PF)),
 .cfg_obase(40'(OB)),.cfg_rbase(40'(RB)),.cfg_has_r(1'(HASR)),.del_slot(slots),.del_valid(valids),.del_flit(flits),
 .w_v(wv),.w_addr(wa),.w_mask(wm),.w_data(wd),.busy(busy),.done(done),.fault(fault),.stat_cycles(cycles));
 function automatic[544:0]make_flit(input integer rank_,f);
  reg[544:0]v;v=0;v[544]=1;v[535:528]=8'(GB+rank_);v[527:512]=16'(rank_*PF+f);
  for(integer j=0;j<8;j=j+1)begin
   v[32*j+:32]=(8*f+j<int'(ns[rank_]))?a[rank_*2048+8*f+j]:32'hffffffff;
   v[256+32*j+:32]=(8*f+j<int'(ns[rank_]))?b[rank_*2048+8*f+j]:32'hffffffff;
  end return v;
 endfunction
 always @(negedge clk)begin
  slots=0;valids=0;flits=0;
  // the ctl's input face flop delays del_* and start alike: drive one core edge ahead (core tick + IREG)
  if(dut.u_ctl.busy_c&&(dut.u_ctl.tick+IREG)>=8&&(dut.u_ctl.tick+IREG)<dut.u_ctl.ingress_end&&((dut.u_ctl.tick+IREG-8)%8==0))begin
   for(integer l=0;l<4;l=l+1)begin:drive
    integer ix;ix=((int'(dut.u_ctl.tick)+IREG-8)/8)*4+l;
    if(ix<G*PF)begin slots[l]=1;valids[l]=1;flits[545*l+:545]=make_flit(((ix/PF)+rotate)%G,ix%PF);end
   end
   if(slotmut!=0&&dut.u_ctl.tick+IREG==8)valids[0]=0;
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
  if($value$plusargs("SLOT_MUT=%d",slotmut))begin end
  if($value$plusargs("ROTATE=%d",rotate))begin end
  $readmemh({dir,"/cfg.hex"},cfg);$readmemh({dir,"/a.hex"},a);$readmemh({dir,"/b.hex"},b);
  $readmemh({dir,"/o.hex"},eo);$readmemh({dir,"/r.hex"},er);$readmemh({dir,"/n.hex"},ns);
  G=cfg[0];N=cfg[1];K=cfg[2];HASR=cfg[4];NOUT=cfg[5];OB=cfg[9];RB=cfg[10];GB=G>=96?0:(int'(cfg[3])/G)*G;PF=(N+7)/8;
  expected=8+((G*PF+3)/4)*8+2*(3*((KMAX+63)/64)+8+XS+PIPE)+3*((NOUT+3)/4)+24+1;
  repeat(10)@(negedge clk);rst_n=1;repeat(10)@(negedge clk);start=1;@(negedge clk);start=0;
  while(!done&&elapsed<expected+20)begin @(negedge clk);elapsed=elapsed+1;end
  if(!done||cycles!=32'(expected))begin errs=errs+1;$display("TIMELINE got%0d expected%0d done%0d",cycles,expected,done);end
  if(fault!=(cfg[6]!=0||slotmut!=0))begin errs=errs+1;$display("FAULT got%0d",fault);end
  if(cfg[6]==0&&slotmut==0)for(integer i=0;i<NOUT;i=i+1)if(!seeno[i]||(HASR&&!seenr[i]))errs=errs+1;
  if(errs)$fatal(1,"TKM_STATIC FAIL errors=%0d words=%0d cycles=%0d",errs,words,cycles);
  $display("TKM_STATIC PASS words=%0d cycles=%0d",words,cycles);$finish;
 end
endmodule
