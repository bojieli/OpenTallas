`timescale 1ns/1ps
// DIE-HBM-61/SPLIT 11-03: TKM tp192 tile RE-FORM proof (the split changes the chain length, so the proof is at the TKM
// level, where the chain's latency is observable): two face-shelled TKM chains on the same delivery stream
//   REF   : root twin ot_hgi_coll_tkm_static_pdh #(PTILE 64) + 31 x ot_hgi_coll_tkm_tp192_tile_core__idpin__strap +
//           1 x __terminal_idpin__strap (the uncut KIT cores, kit face shells);
//   SPLIT : root twin #(PTILE 32) + 31 x <idpin>__split + 1 x <terminal>__split (2 face-shelled half tiles each).
// Chain wiring = ot_hbm_tkm_path_tkx_ft21 (root face shell modelled on the tile-facing pins: entry +2 / up0 +2 = FRT 4;
// conv: root face + CB 21 broadcast stages to the deepest slot, forwarded up slot to slot; clr: systolic down
// through each slot's clr_o).  PIPE 1, HOP 2, FRT 4, CB 21, CLRB 0, DELIVERED_RESET 1, TP 192, KMAX 2048.
// Checks: (1) golden O/R words (NumPy oracle) + exact timeline in BOTH chains; (2) lock-step: every SPLIT write
// (v, addr, mask, data) and done / fault == REF exactly SHIFT edges earlier, SHIFT = 2*dSETTLE + 2*dXL.
// Chain length NT0 = KMAX/64 tiles (KMAX 2048: 32 tiles; reduced-chain receipt KMAX 256: 4 tiles = first, 2 middle, terminal).
// MUTN (root timeline for 32 elements on the split chain) and MUTP (pair-internal conv / up-hop mutants) must FAIL.
module tb;
 parameter integer MUTN=0,MUTP=0,KMAX=2048,TP=192,PIPE=1,HOP=2,FRT=4,CB=21,CLRB=0;
 localparam integer EW=86,NT0=KMAX/64,NT1=2*NT0,SN0=(3+HOP)*(NT0-1)+11-CB,XL0=FRT+CB+HOP*(NT0-1),
  NL1=(MUTN!=0)?NT0:NT1,SN1=(3+HOP)*(NL1-1)+11-CB,XL1=FRT+CB+HOP*(NL1-1),SHIFT=2*(SN1-SN0)+2*(XL1-XL0);
 reg clk=0,rst_n=0,start=0;always #1 clk=~clk;
 reg[31:0]cfg[0:15],a[0:TP*2048-1],b[0:TP*2048-1],eo[0:2047],er[0:2047],ns[0:TP-1];
 reg[3:0]slots=0,valids=0;reg[2179:0]flits=0;
 integer G,N,K,PF,NOUT,HASR,OB,RB,GB,elapsed=0;string dir;
 wire[1:0]wv,busy,done,fault;wire[39:0]wa[0:1];wire[15:0]wm[0:1];wire[511:0]wd[0:1];wire[31:0]cyc[0:1];
 for(genvar m=0;m<2;m=m+1)begin:g_chain
  localparam integer PTL=(m==0)?64:32;
  wire tclr,tconv,tev;wire[4*EW-1:0]tent,tup0;
  ot_hgi_coll_tkm_static_pdh #(.PTILE(PTL),.EXT(1),.NTT((m==1&&MUTN!=0)?NT0:0),.KMAX(KMAX),.TP(TP),.PIPE(1),.HOP(HOP),.FRT(FRT),.CB(CB),.CLRB(CLRB),.DELIVERED_RESET(1)) root(
   .clk(clk),.rst_n(rst_n),.start(start),.tile_clk({32{clk}}),.buffer_clk(clk),
   .cfg_n(12'(N)),.cfg_k(13'(K)),.cfg_nout(13'(NOUT)),.cfg_g(8'(G)),.cfg_gbase(8'(GB)),.cfg_pf(16'(PF)),
   .cfg_obase(40'(OB)),.cfg_rbase(40'(RB)),.cfg_has_r(1'(HASR)),.del_slot(slots),.del_valid(valids),.del_flit(flits),
   .w_v(wv[m]),.w_addr(wa[m]),.w_mask(wm[m]),.w_data(wd[m]),.busy(busy[m]),.done(done[m]),.fault(fault[m]),.stat_cycles(cyc[m]),
   .t_clr(tclr),.t_conv(tconv),.t_entry_v(tev),.t_entry(tent),.t_up0(tup0));
  // root face shell (tile-facing pins): +1 out, +1 in
  reg fclr,fconv,fev;reg[4*EW-1:0]fent,fup0;assign tup0=fup0;
  always @(posedge clk)begin fclr<=tclr;fconv<=tconv;fev<=tev;fent<=tent;end
  wire[4*EW-1:0]down[0:NT0],up[0:NT0];wire[NT0:0]dv;wire[NT0-1:0]clr_l,conv_l;
  always @(posedge clk)fup0<=up[0];
  assign down[0]=fent;assign dv[0]=fev;
  reg bc[0:CB-1];always @(posedge clk)begin bc[0]<=fconv;for(integer j=1;j<CB;j=j+1)bc[j]<=bc[j-1];end
  for(genvar t=0;t<NT0;t=t+1)begin:g_t
   wire ci=(t==0)?fclr:clr_l[t-1];wire vi=(t==NT0-1)?bc[CB-1]:conv_l[t+1];
   if(m==0&&t<NT0-1)begin:r ot_hgi_coll_tkm_tp192_tile_core__idpin__strap tile(.tile_clk(clk),.tile_clr(ci),.tile_clr_o(clr_l[t]),
     .tile_conv(vi),.tile_conv_o(conv_l[t]),.tile_ins_v(dv[t]),.tile_ins_b(down[t]),.tile_up_in(up[t+1]),
     .tile_ovf_v(dv[t+1]),.tile_ovf_b(down[t+1]),.tile_up_out(up[t])); end
   else if(m==0)begin:e ot_hgi_coll_tkm_tp192_tile_core__terminal_idpin__strap tile(.tile_clk(clk),.tile_clr(ci),.tile_clr_o(clr_l[t]),
     .tile_conv(vi),.tile_conv_o(conv_l[t]),.tile_ins_v(dv[t]),.tile_ins_b(down[t]),.tile_up_out(up[t])); end
   else if(t<NT0-1)begin:r ot_hgi_coll_tkm_tp192_tile_core__idpin__strap__split #(.MUT(MUTP)) tile(.tile_clk(clk),.tile_clr(ci),.tile_clr_o(clr_l[t]),
     .tile_conv(vi),.tile_conv_o(conv_l[t]),.tile_ins_v(dv[t]),.tile_ins_b(down[t]),.tile_up_in(up[t+1]),
     .tile_ovf_v(dv[t+1]),.tile_ovf_b(down[t+1]),.tile_up_out(up[t])); end
   else begin:e ot_hgi_coll_tkm_tp192_tile_core__terminal_idpin__strap__split #(.MUT(MUTP)) tile(.tile_clk(clk),.tile_clr(ci),.tile_clr_o(clr_l[t]),
     .tile_conv(vi),.tile_conv_o(conv_l[t]),.tile_ins_v(dv[t]),.tile_ins_b(down[t]),.tile_up_out(up[t])); end
  end
 end
 // delivery stream (as tb_hbm_tkm_bound_tkx_ft21): driven from the REF root's ingress (identical in both roots)
 function automatic[544:0]make_flit(input integer rank_,f);
  reg[544:0]v;v=0;v[544]=1;v[535:528]=8'(GB+rank_);v[527:512]=16'(rank_*PF+f);
  for(integer j=0;j<8;j=j+1)begin
   v[32*j+:32]=(8*f+j<int'(ns[rank_]))?a[rank_*2048+8*f+j]:32'hffffffff;
   v[256+32*j+:32]=(8*f+j<int'(ns[rank_]))?b[rank_*2048+8*f+j]:32'hffffffff;
  end return v;
 endfunction
 always @(negedge clk)begin
  slots=0;valids=0;flits=0;
  if(busy[0]&&g_chain[0].root.tick>=8&&g_chain[0].root.tick<g_chain[0].root.ingress_end&&((g_chain[0].root.tick-8)%8==0))
   for(integer l=0;l<4;l=l+1)begin:drive
    integer ix;ix=((int'(g_chain[0].root.tick)-8)/8)*4+l;
    if(ix<G*PF)begin slots[l]=1;valids[l]=1;flits[545*l+:545]=make_flit(ix/PF,ix%PF);end
   end
 end
 // golden O/R words, per chain
 integer errs[0:1],words[0:1];bit seeno[0:1][0:2047],seenr[0:1][0:2047];
 initial begin errs[0]=0;errs[1]=0;words[0]=0;words[1]=0;end
 for(genvar m=0;m<2;m=m+1)begin:g_gold
  always @(negedge clk)if(rst_n&&wv[m])
   for(integer j=0;j<16;j=j+1)if(wm[m][j])begin:w
    integer ix;ix=int'(wa[m])+j;
    if(ix>=OB&&ix<OB+NOUT)begin
     if(seeno[m][ix-OB]||wd[m][32*j+:32]!==eo[ix-OB])begin errs[m]=errs[m]+1;if(errs[m]<6)$display("GOLD%0d MISMATCH O %0d got%h exp%h",m,ix-OB,wd[m][32*j+:32],eo[ix-OB]);end
     seeno[m][ix-OB]=1;words[m]=words[m]+1;
    end else if(HASR&&ix>=RB&&ix<RB+NOUT)begin
     if(seenr[m][ix-RB]||wd[m][32*j+:32]!==er[ix-RB])begin errs[m]=errs[m]+1;if(errs[m]<6)$display("GOLD%0d MISMATCH R %0d got%h exp%h",m,ix-RB,wd[m][32*j+:32],er[ix-RB]);end
     seenr[m][ix-RB]=1;words[m]=words[m]+1;
    end else begin errs[m]=errs[m]+1;$display("GOLD%0d OUTSIDE %0d",m,ix);end
   end
 end
 // lock-step SPLIT vs REF delayed SHIFT edges
 localparam integer DL=(SHIFT>0?SHIFT:1)+1;
 reg[570:0]rq[0:DL-1];initial for(integer j=0;j<DL;j=j+1)rq[j]=0;
 wire[570:0]rnow={wv[0],wv[0]?wa[0]:40'd0,wv[0]?wm[0]:16'd0,wv[0]?wd[0]:512'd0,done[0],fault[0]};
 wire[570:0]snow={wv[1],wv[1]?wa[1]:40'd0,wv[1]?wm[1]:16'd0,wv[1]?wd[1]:512'd0,done[1],fault[1]};
 always @(posedge clk)begin rq[0]<=rnow;for(integer j=1;j<DL;j=j+1)rq[j]<=rq[j-1];end
 integer lerrs=0,lchk=0,lw=0;wire[570:0]rdel=(SHIFT>0)?rq[SHIFT-1]:rnow;
 always @(negedge clk)if(rst_n)begin lchk=lchk+1;if(wv[1])lw=lw+1;
  if(snow!==rdel)begin lerrs=lerrs+1;if(lerrs<6)$display("LOCKSTEP MISMATCH edge%0d split v%0d a%h d%0d f%0d | ref-%0d v%0d a%h d%0d f%0d",lchk,wv[1],wa[1],done[1],fault[1],SHIFT,rdel[570],rdel[569:530],rdel[1],rdel[0]);end
 end
 integer exp0,exp1,tot;
 initial begin
  if(!$value$plusargs("DIR=%s",dir))$fatal(1,"missing DIR");
  $readmemh({dir,"/cfg.hex"},cfg);$readmemh({dir,"/a.hex"},a);$readmemh({dir,"/b.hex"},b);
  $readmemh({dir,"/o.hex"},eo);$readmemh({dir,"/r.hex"},er);$readmemh({dir,"/n.hex"},ns);
  G=cfg[0];N=cfg[1];K=cfg[2];HASR=cfg[4];NOUT=cfg[5];OB=cfg[9];RB=cfg[10];GB=G>=96?0:(int'(cfg[3])/G)*G;PF=(N+7)/8;
  exp0=8+((G*PF+3)/4)*8+2*SN0+3*((NOUT+3)/4)+24+1+2*PIPE+2*XL0+2*CLRB;
  exp1=8+((G*PF+3)/4)*8+2*SN1+3*((NOUT+3)/4)+24+1+2*PIPE+2*XL1+2*CLRB;
  repeat(10)@(negedge clk);rst_n=1;repeat(20)@(negedge clk);
  start=1;@(negedge clk);start=0;
  while(!(done[1]||(MUTN!=0&&done[0]&&elapsed>exp1+SHIFT+40))&&elapsed<exp1+80)begin @(negedge clk);elapsed=elapsed+1;end
  repeat(4)@(negedge clk);
  tot=lerrs+errs[0]+errs[1];
  if(cyc[0]!=32'(exp0))begin tot++;$display("TIMELINE REF got%0d exp%0d",cyc[0],exp0);end
  if(cyc[1]!=32'(exp1))begin tot++;$display("TIMELINE SPLIT got%0d exp%0d",cyc[1],exp1);end
  if(fault!=0)begin tot++;$display("FAULT %b",fault);end
  for(integer m=0;m<2;m=m+1)for(integer i=0;i<NOUT;i=i+1)if(!seeno[m][i]||(HASR&&!seenr[m][i]))begin tot++;if(tot<12)$display("MISSING chain%0d word %0d",m,i);end
  if(tot)$display("TKM_SPLIT FAIL total=%0d gold_ref=%0d gold_split=%0d lockstep=%0d words=%0d/%0d cycles=%0d/%0d shift=%0d",tot,errs[0],errs[1],lerrs,words[0],words[1],cyc[0],cyc[1],SHIFT);
  else $display("TKM_SPLIT PASS words=%0d/%0d cycles ref=%0d split=%0d shift=%0d lockstep_edges=%0d split_writes=%0d",words[0],words[1],cyc[0],cyc[1],SHIFT,lchk,lw);
  $finish;
 end
endmodule
