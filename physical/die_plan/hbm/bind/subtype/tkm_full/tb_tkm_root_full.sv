`timescale 1ns/1ps
// BIND-SUBTYPE-2 11-11 (DO_NOT_COUNT): full-shape exactness bench of the BOUND TKM pieces of plan 29333b2b (root partition):
//   root  = the root kit top ot_hgi_coll_tkm_m_tp192__root (kit face shell + wrap) around ot_hgi_coll_tkm_tp192_root_core in
//           the plan's form (part 19: rest_extract_mem.sh of ot_hgi_coll_tkm_m_tp192_pfdh32 = static_pdh PTILE 32, minus 64 htiles);
//   tiles = 31 x ot_hgi_coll_tkm_tp192_tile_core__idpin__strap (p19glue) + 1 x __terminal_idpin__strap (p19glue), each
//           u_fcore.u_core (__splitc) = 2 x ot_hgi_coll_tkm_tp192_htile_core in kit face-shell form (+1 in / +1 out);
//   chain = ot_hbm_tkm_path_tkx_ft21 wiring as tb_tkm_tile_split.sv (DIE-HBM-61/SPLIT): root<->tile0 direct (both faces are
//           in the kit shells: FRT 4), tile<->tile direct (HOP 2), clr systolic down through clr_o, conv = root conv pin ->
//           CB 21 broadcast stages -> deepest slot, forwarded up through conv_o.  PIPE 1, HOP 2, FRT 4, CB 21, CLRB 0.
// One TKM merge op per case (cfg/a/b from tkm_split_vectors.py: the NumPy oracle hgi_coll_tkm_vectors.write_case = the golden
// order).  Checks: every O/R word == golden, each written once, none outside, no fault, stat_cycles == the derived
// timeline of the 64-element chain (exp1), and exp1 - exp0 == 448 (the priced TKM +448 vs the 32-element chain).
// Negative controls (each must FAIL): MUTN = the root core built for 32 elements (the 10-23 static_p extraction, same
// ports) on this 64-element chain; MUTU = bits 0/1 of the up hop tile MUTT -> tile MUTT-1 swapped.
module tb;
 parameter integer MUTU=0,MUTT=5,KMAX=2048,TP=192,PIPE=1,HOP=2,FRT=4,CB=21,CLRB=0;
 localparam integer EW=86,NT=32,NT0=KMAX/64,NT1=2*NT0,SN0=(3+HOP)*(NT0-1)+11-CB,XL0=FRT+CB+HOP*(NT0-1),
  SN1=(3+HOP)*(NT1-1)+11-CB,XL1=FRT+CB+HOP*(NT1-1),SHIFT=2*(SN1-SN0)+2*(XL1-XL0);
 reg clk=0,rst_n=0,start=0;always #1 clk=~clk;
 reg[31:0]cfg[0:15],a[0:TP*2048-1],b[0:TP*2048-1],eo[0:2047],er[0:2047],ns[0:TP-1];
 reg[3:0]slots=0,valids=0;reg[2179:0]flits=0;wire[2115:0]dflit;
 `include "tb_dflit_map.svh"
 integer G,N,K,PF,NOUT,HASR,OB,RB,GB,elapsed=0;string dir;
 wire wv,busy,done,fault;wire[39:0]wa;wire[15:0]wm;wire[511:0]wd;wire[31:0]cyc;
 wire tclr,tconv,tev;wire[4*EW-1:0]tent,tup0;
 ot_hgi_coll_tkm_m_tp192__root root(
  .clk(clk),.rst_n(rst_n),.start(start),.arg_mode(1'b0),.buffer_clk(clk),
  .cfg_n(12'(N)),.cfg_k(13'(K)),.cfg_nout(13'(NOUT)),.cfg_g(8'(G)),.cfg_gbase(8'(GB)),.cfg_pf(16'(PF)),
  .cfg_obase(40'(OB)),.cfg_rbase(40'(RB)),.cfg_has_r(1'(HASR)),.del_slot(slots),.del_valid(valids),.del_flit(dflit),
  .w_v(wv),.w_addr(wa),.w_mask(wm),.w_data(wd),.busy(busy),.done(done),.fault(fault),.stat_cycles(cyc),
  .x_u_u_g_tiles_0_e86_u_tile_clr(tclr),.x_u_u_g_tiles_0_e86_u_tile_conv(tconv),
  .x_u_u_g_tiles_0_e86_u_tile_ins_v(tev),.x_u_u_g_tiles_0_e86_u_tile_ins_b(tent),.x_u_u_g_tiles_0_e86_u_tile_up_out(tup0));
 wire[4*EW-1:0]down[0:NT],up[0:NT],upx[0:NT];wire[NT:0]dv;wire[NT-1:0]clr_l,conv_l;
 assign tup0=upx[0];assign down[0]=tent;assign dv[0]=tev;
 for(genvar t=0;t<NT;t=t+1)begin:g_u   // up hop t -> t-1 (MUTU: bits 0/1 swapped on the hop out of tile MUTT)
  if(MUTU!=0&&t==MUTT)begin:m assign upx[t]={up[t][4*EW-1:2],up[t][0],up[t][1]};end else begin:p assign upx[t]=up[t];end
 end
 reg bc[0:CB-1];always @(posedge clk)begin bc[0]<=tconv;for(integer j=1;j<CB;j=j+1)bc[j]<=bc[j-1];end
 for(genvar t=0;t<NT;t=t+1)begin:g_t
  wire ci=(t==0)?tclr:clr_l[t-1];wire vi=(t==NT-1)?bc[CB-1]:conv_l[t+1];
  if(t<NT-1)begin:r ot_hgi_coll_tkm_tp192_tile_core__idpin__strap tile(.tile_clk(clk),.tile_clr(ci),.tile_clr_o(clr_l[t]),
    .tile_conv(vi),.tile_conv_o(conv_l[t]),.tile_ins_v(dv[t]),.tile_ins_b(down[t]),.tile_up_in(upx[t+1]),
    .tile_ovf_v(dv[t+1]),.tile_ovf_b(down[t+1]),.tile_up_out(up[t])); end
  else begin:e ot_hgi_coll_tkm_tp192_tile_core__terminal_idpin__strap tile(.tile_clk(clk),.tile_clr(ci),.tile_clr_o(clr_l[t]),
    .tile_conv(vi),.tile_conv_o(conv_l[t]),.tile_ins_v(dv[t]),.tile_ins_b(down[t]),.tile_up_out(up[t])); end
 end
 // delivery stream = tb_tkm_tile_split.sv, timed by the root's tick (bench copy tk: 0 at the start capture, +1 per edge);
 // the root kit's input face delays start and del_* by the same one edge, so the relative timing is the root's.
 function automatic[544:0]make_flit(input integer rank_,f);
  reg[544:0]v;v=0;v[544]=1;v[535:528]=8'(GB+rank_);v[527:512]=16'(rank_*PF+f);
  for(integer j=0;j<8;j=j+1)begin
   v[32*j+:32]=(8*f+j<int'(ns[rank_]))?a[rank_*2048+8*f+j]:32'hffffffff;
   v[256+32*j+:32]=(8*f+j<int'(ns[rank_]))?b[rank_*2048+8*f+j]:32'hffffffff;
  end return v;
 endfunction
 reg run=0;reg[31:0]tk=0;
 always @(posedge clk)if(start)begin run<=1;tk<=0;end else if(run)tk<=tk+1;
 always @(negedge clk)begin
  slots=0;valids=0;flits=0;
  if(run&&tk>=8&&((tk-8)%8==0))
   for(integer l=0;l<4;l=l+1)begin:drive
    integer ix;ix=((int'(tk)-8)/8)*4+l;
    if(ix<G*PF)begin slots[l]=1;valids[l]=1;flits[545*l+:545]=make_flit(ix/PF,ix%PF);end
   end
 end
 integer errs=0,words=0;bit seeno[0:2047],seenr[0:2047];
 always @(negedge clk)if(rst_n&&wv)
  for(integer j=0;j<16;j=j+1)if(wm[j])begin:w
   integer ix;ix=int'(wa)+j;
   if(ix>=OB&&ix<OB+NOUT)begin
    if(seeno[ix-OB]||wd[32*j+:32]!==eo[ix-OB])begin errs=errs+1;if(errs<6)$display("GOLD MISMATCH O %0d got%h exp%h",ix-OB,wd[32*j+:32],eo[ix-OB]);end
    seeno[ix-OB]=1;words=words+1;
   end else if(HASR&&ix>=RB&&ix<RB+NOUT)begin
    if(seenr[ix-RB]||wd[32*j+:32]!==er[ix-RB])begin errs=errs+1;if(errs<6)$display("GOLD MISMATCH R %0d got%h exp%h",ix-RB,wd[32*j+:32],er[ix-RB]);end
    seenr[ix-RB]=1;words=words+1;
   end else begin errs=errs+1;$display("GOLD OUTSIDE %0d",ix);end
  end
 integer exp0,exp1,tot,nw;
 initial begin
  if(!$value$plusargs("DIR=%s",dir))$fatal(1,"missing DIR");
  $readmemh({dir,"/cfg.hex"},cfg);$readmemh({dir,"/a.hex"},a);$readmemh({dir,"/b.hex"},b);
  $readmemh({dir,"/o.hex"},eo);$readmemh({dir,"/r.hex"},er);$readmemh({dir,"/n.hex"},ns);
  G=cfg[0];N=cfg[1];K=cfg[2];HASR=cfg[4];NOUT=cfg[5];OB=cfg[9];RB=cfg[10];GB=G>=96?0:(int'(cfg[3])/G)*G;PF=(N+7)/8;
  exp0=8+((G*PF+3)/4)*8+2*SN0+3*((NOUT+3)/4)+24+1+2*PIPE+2*XL0+2*CLRB;
  exp1=8+((G*PF+3)/4)*8+2*SN1+3*((NOUT+3)/4)+24+1+2*PIPE+2*XL1+2*CLRB;
  repeat(10)@(negedge clk);rst_n=1;repeat(20)@(negedge clk);
  start=1;@(negedge clk);start=0;
  while(!done&&elapsed<exp1+200)begin @(negedge clk);elapsed=elapsed+1;end
  repeat(4)@(negedge clk);
  tot=errs;nw=HASR?2*NOUT:NOUT;
  if(cyc!=32'(exp1))begin tot++;$display("TIMELINE got%0d exp%0d",cyc,exp1);end
  if(exp1-exp0!=448||SHIFT!=448)begin tot++;$display("SHIFT exp1-exp0=%0d SHIFT=%0d (priced 448)",exp1-exp0,SHIFT);end
  if(!done)begin tot++;$display("NO DONE after %0d edges",elapsed);end
  if(fault)begin tot++;$display("FAULT");end
  for(integer i=0;i<NOUT;i=i+1)if(!seeno[i]||(HASR&&!seenr[i]))begin tot++;if(tot<12)$display("MISSING word %0d",i);end
  if(tot)$display("TKM_FULL FAIL total=%0d gold=%0d words=%0d/%0d cycles=%0d exp=%0d exp0=%0d",tot,errs,words,nw,cyc,exp1,exp0);
  else $display("TKM_FULL PASS words=%0d/%0d cycles=%0d exp=%0d exp0=%0d shift=%0d",words,nw,cyc,exp1,exp0,exp1-exp0);
  $finish;
 end
endmodule
