`timescale 1ns/1ps
// HBM-P4-SPLIT (2026-10-23): tb_hgi_coll_tkm_static (golden O/R words + timeline) on the core-split twin
// ot_hgi_coll_tkm_static_p #(PIPE), PLUS a lock-step against the pinned ot_hgi_coll_tkm_static on the same inputs:
// every write (addr, mask, data) and done/fault of the twin must equal the pinned one exactly 2*PIPE edges later.
// PATH-HBM/TOK 2026-10-25 (claude/path-hbm-tok-1025): FACE-SHELLED successor of tb_hbm_tkm_l74 (r3).  DUT = the actual
// face_shell root wrapper ot_hgi_coll_tkm_m_tp192__root (root core re-extracted from ot_hgi_coll_tkm_static_p #(PIPE 1,
// HOP 2, FRT 4)) + 32 x the ONE common shelled tile ot_hgi_coll_tkm_tp192_tile_core__idpin with tile_tid driven per
// instance (0..31) as a timed input port, tile->tile hops face flop to face flop (no station), clr broadcast at equal
// latency, conv through the parent deskew ot_hgi_coll_tkm_conv_skew (HOP edges per tile, deepest tile first).
// Named plan_direct3: L74 2 cycles (LINK_STAGES 2), return L12 CTL = L13 DATA = 2 (coherent, no pad).
module tb_hbm_tkm_bound_ft21;
 parameter integer KMAX=2048,MUT=0,TP=192,TIE_W_MUT=0,PIPE=1,MUTP=0,LINK_STAGES=2,RETURN_CTL_STAGES=2,RETURN_DATA_STAGES=2,BEAT_WIDTH=2341,HOP=2,FRT=4,CTL_BCAST_STAGES=14,CLR_SYSTOLIC=0,CLR_HOP=3;
 localparam integer NT=(KMAX+63)/64,CB=CTL_BCAST_STAGES,CLRB=CLR_SYSTOLIC?0:CB,S0=3*NT+8,SN=(3+HOP)*(NT-1)+11-CB,XL=FRT+CB+HOP*(NT-1),ROOT_IO=2;
 // twin age vs the pinned PIPE-0 module: L74 forward + PIPE split + root face in/out (cfg/start/del in, w/done out) +
 // the face-path timeline growth (2 settles + 2 x conv-stream extra age XL, see ot_hgi_coll_tkm_static_p) + return
 localparam integer FORWARD_AGE=LINK_STAGES+3,RETURN_AGE=RETURN_CTL_STAGES,FACE_AGE=ROOT_IO+2*(SN-S0)+2*XL+2*CLRB,
  TOTAL_DELAY=FORWARD_AGE+2*PIPE+FACE_AGE+RETURN_AGE;
 reg clk=0,rst_n=0,start=0;always #0.4167 clk=~clk;
 reg[31:0]cfg[0:15],a[0:TP*2048-1],b[0:TP*2048-1],eo[0:2047],er[0:2047],ns[0:TP-1];
 reg[3:0]slots=0,valids=0;reg[2179:0]flits=0;
 wire wv,busy,done,fault;wire[39:0]wa;wire[15:0]wm;wire[511:0]wd;wire[31:0]cycles;
 integer G,N,K,PF,NOUT,HASR,OB,RB,GB,errs=0,words=0,elapsed=0,expected,slotmut=0,rotate=0;
 bit seeno[0:2047],seenr[0:2047];string dir;
 wire rv,rbusy,rdone,rfault;wire[39:0]ra;wire[15:0]rm;wire[511:0]rd;wire[31:0]rcycles;
 ot_hgi_coll_tkm_static #(.KMAX(KMAX),.MUT(MUT),.TP(TP),.RANK_W(TIE_W_MUT?7:$clog2(TP)))ref_u(.clk(clk),.rst_n(rst_n),.start(start),.tile_clk({32{clk}}),.buffer_clk(clk),
 .cfg_n(12'(N)),.cfg_k(13'(K)),.cfg_nout(13'(NOUT)),.cfg_g(8'(G)),.cfg_gbase(8'(GB)),.cfg_pf(16'(PF)),
 .cfg_obase(40'(OB)),.cfg_rbase(40'(RB)),.cfg_has_r(1'(HASR)),.del_slot(slots),.del_valid(valids),.del_flit(flits),
 .w_v(rv),.w_addr(ra),.w_mask(rm),.w_data(rd),.busy(rbusy),.done(rdone),.fault(rfault),.stat_cycles(rcycles));
 // lock-step: the pinned module's outputs delayed 2*PIPE edges must equal the twin's
 localparam integer DL=TOTAL_DELAY+2;
 reg[570:0]rq[0:DL-1];initial for(integer j=0;j<DL;j=j+1)rq[j]=0;wire[1+40+16+512+2-1:0]rnow={rv,ra,rm,rd,rdone,rfault};
 wire[1+40+16+512+2-1:0]rdel=rq[TOTAL_DELAY-1];
 integer lerrs=0,lchk=0,lw=0;
 always @(posedge clk)begin rq[0]<=rnow;for(integer j=1;j<DL;j=j+1)rq[j]<=rq[j-1];end
 always @(negedge clk)if(rst_n)begin
  lchk=lchk+1;if(wv)lw=lw+1;
  if({wv,wv?wa:40'd0,wv?wm:16'd0,wv?wd:512'd0,done,fault}!=={rdel[570],rdel[570]?rdel[569:530]:40'd0,rdel[570]?rdel[529:514]:16'd0,rdel[570]?rdel[513:2]:512'd0,rdel[1],rdel[0]})begin
   lerrs=lerrs+1;if(lerrs<6)$display("LOCKSTEP MISMATCH t%0d twin v%0d a%h done%0d f%0d | pinned-2P v%0d a%h done%0d f%0d",lchk,wv,wa,done,fault,rdel[570],rdel[569:530],rdel[1],rdel[0]);
  end
 end
 reg boot_start=0,send_start=0;wire slot0,tf,rf;
 reg[3748:0]tx_word;wire[3748:0]rx_word;wire[32:0]rx_side;
 wire[BEAT_WIDTH-1:0]beat;wire[32:0]side_beat;
 wire[BEAT_WIDTH-1:0]channel_beat;wire[32:0]channel_side;
 always @*begin tx_word=0;
  tx_word[19+:1]=1'b0;
  tx_word[20+:8]=8'(G);
  tx_word[28+:8]=8'(GB);
  tx_word[36+:1]=1'(HASR);
  tx_word[37+:13]=13'(K);
  tx_word[50+:12]=12'(N);
  tx_word[62+:13]=13'(NOUT);
  tx_word[75+:40]=40'(OB);
  tx_word[115+:16]=16'(PF);
  tx_word[131+:40]=40'(RB);
  tx_word[171+:2180]=flits;
  tx_word[2351+:4]=slots;
  tx_word[2355+:4]=valids;
  tx_word[2359+:1]=send_start;
 end
 wire[191:0]parent_ids;
 for(genvar t=0;t<32;t=t+1)begin:g_ids
  assign parent_ids[6*t+:6]=($test$plusargs("MUT_TID")&&t==5)?6'd6:6'(t);
 end
 wire[BEAT_WIDTH-1:0]observed_beat;wire[32:0]observed_side;
 ot_hbm_tkm_path_ft21 #(.LINK_STAGES(LINK_STAGES),.RETURN_CTL_STAGES(RETURN_CTL_STAGES),.RETURN_DATA_STAGES(RETURN_DATA_STAGES),.BEAT_WIDTH(BEAT_WIDTH)) bound(
 .nw_clk(clk),.clk(clk),.buffer_clk(clk),.tile_clk({32{clk}}),.nw_rst_n(rst_n),.root_rst_n(rst_n),.tx_boot_start(boot_start),.rx_boot_start(boot_start),.strap_tile_ids(parent_ids),
 .tx_word(tx_word),.tx_side(33'd0),.rx_word(rx_word),.rx_side(rx_side),.beat(observed_beat),.side_beat(observed_side),.tx_fault(tf),.rx_fault(rf),.slot0(slot0),
 .wv(wv),.busy(busy),.done(done),.fault(fault),.wa(wa),.wm(wm),.wd(wd),.cycles(cycles));
 integer tiderr=0;
 for(genvar t=0;t<32;t=t+1)begin:g_id_check
  wire[5:0]captured_id;
  if(t<31)assign captured_id=bound.actual_tiles[t].regular.tile.u_fcore.u_core.tile_tid;
  else assign captured_id=bound.actual_tiles[t].terminal.tile.u_fcore.u_core.tile_tid;
  always@(negedge clk)if(rst_n&&captured_id!==6'(t))$fatal(1,"TILE_TID mismatch tile%0d got%0d",t,captured_id);
 end
 always@(posedge clk)if(rst_n&&(tf||rf))$fatal(1,"L74_TKM_TRANSPORT fault tf=%0d rf=%0d",tf,rf);

 function automatic[544:0]make_flit(input integer rank_,f);
  reg[544:0]v;v=0;v[544]=1;v[535:528]=8'(GB+rank_);v[527:512]=16'(rank_*PF+f);
  for(integer j=0;j<8;j=j+1)begin
   v[32*j+:32]=(8*f+j<int'(ns[rank_]))?a[rank_*2048+8*f+j]:32'hffffffff;
   v[256+32*j+:32]=(8*f+j<int'(ns[rank_]))?b[rank_*2048+8*f+j]:32'hffffffff;
  end return v;
 endfunction
 always @(negedge clk)begin
  slots=0;valids=0;flits=0;
  if(rbusy&&ref_u.tick>=8&&ref_u.tick<ref_u.ingress_end&&((ref_u.tick-8)%8==0))begin
   for(integer l=0;l<4;l=l+1)begin:drive
    integer ix;ix=((int'(ref_u.tick)-8)/8)*4+l;
    if(ix<G*PF)begin slots[l]=1;valids[l]=1;flits[545*l+:545]=make_flit(((ix/PF)+rotate)%G,ix%PF);end
   end
   if(slotmut!=0&&ref_u.tick==8)valids[0]=0;
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
  expected=8+((G*PF+3)/4)*8+2*SN+3*((NOUT+3)/4)+24+1+2*PIPE+2*XL+2*CLRB;
  repeat(10)@(negedge clk);rst_n=1;repeat(10)@(negedge clk);boot_start=1;@(negedge clk);boot_start=0;
  repeat(16)@(negedge clk);while(!slot0)@(negedge clk);
  if($test$plusargs("MUT_PHASE"))@(negedge clk);
  send_start=1;@(negedge clk);send_start=0;start=1;@(negedge clk);start=0;
  while(!done&&elapsed<expected+TOTAL_DELAY+40)begin @(negedge clk);elapsed=elapsed+1;end
  if(!done||cycles!=32'(expected))begin errs=errs+1;$display("TIMELINE got%0d expected%0d done%0d",cycles,expected,done);end
  if(fault!=(cfg[6]!=0||slotmut!=0))begin errs=errs+1;$display("FAULT got%0d",fault);end
  if(cfg[6]==0&&slotmut==0)for(integer i=0;i<NOUT;i=i+1)if(!seeno[i]||(HASR&&!seenr[i]))errs=errs+1;
  repeat(2*PIPE+2)@(negedge clk);
  if(lerrs)errs=errs+lerrs;if(tiderr)errs=errs+tiderr;
  if(errs)$fatal(1,"TKM_L74 FAIL errors=%0d lockstep_errors=%0d tid_errors=%0d words=%0d cycles=%0d",errs,lerrs,tiderr,words,cycles);
  $display("TKM_L74 PASS words=%0d cycles=%0d pinned_cycles=%0d lockstep_edges=%0d lockstep_writes=%0d pipe=%0d",words,cycles,rcycles,lchk,lw,PIPE);
  $display("TKM_L74_AGE forward%0d split%0d face%0d(root_io%0d settle2x%0d xl2x%0d cb2x%0d) return%0d data_pad%0d total%0d",FORWARD_AGE,2*PIPE,FACE_AGE,ROOT_IO,SN-S0,XL,CB,RETURN_CTL_STAGES,RETURN_CTL_STAGES-RETURN_DATA_STAGES,TOTAL_DELAY);$finish;
 end
endmodule
