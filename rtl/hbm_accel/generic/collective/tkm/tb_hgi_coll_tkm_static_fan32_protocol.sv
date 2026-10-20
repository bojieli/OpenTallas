`timescale 1ns/1ps
module tb_hgi_coll_tkm_static_fan32_protocol;
 parameter integer KMAX=64,MUT=0,TP=192,TIE_W_MUT=0,FAN32=1;
 // HH-4 10-18: tile chain hop edges (tkm_static TLAT): 4 for the e86 shape (EW 86 = 78 + RANK_W 8), else 3.
 localparam integer RW_=TIE_W_MUT?7:$clog2(TP),TL=(78+RW_==86&&KMAX>=64)?4:3;
 reg clk=0,rst_n=0,start=0;always #0.4167 clk=~clk;
 reg[31:0]cfg[0:15],a[0:TP*2048-1],b[0:TP*2048-1],eo[0:2047],er[0:2047],ns[0:TP-1];
 reg[3:0]slots=0,valids=0;reg[2179:0]flits=0;
 wire wv,busy,done,fault;wire[39:0]wa;wire[15:0]wm;wire[511:0]wd;wire[31:0]cycles;
 integer G,N,K,PF,NOUT,HASR,OB,RB,GB,errs=0,words=0,elapsed=0,expected,slotmut=0,rotate=0;
 integer protocol_mut=0;reg[31:0] bad_read2;
 bit seeno[0:2047],seenr[0:2047];string dir;
 ot_hgi_coll_tkm_static #(.KMAX(KMAX),.MUT(MUT),.TP(TP),.FAN32(FAN32),.RANK_W(TIE_W_MUT?7:$clog2(TP)))dut(.clk(clk),.rst_n(rst_n),.start(start),.tile_clk({32{clk}}),.buffer_clk(clk),
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
  if(busy&&dut.tick>=8&&dut.tick<dut.ingress_end&&((dut.tick-8)%8==0))begin
   for(integer l=0;l<4;l=l+1)begin:drive
    integer ix;ix=((int'(dut.tick)-8)/8)*4+l;
    if(ix<G*PF)begin slots[l]=1;valids[l]=1;flits[545*l+:545]=make_flit(((ix/PF)+rotate)%G,ix%PF);end
   end
   if(slotmut!=0&&dut.tick==8)valids[0]=0;
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
  if($value$plusargs("PROTOCOL_MUT=%d",protocol_mut))begin end
  if(protocol_mut==1)force dut.clr=1'b0;
  if(!$value$plusargs("DIR=%s",dir))$fatal(1,"missing DIR");
  if($value$plusargs("SLOT_MUT=%d",slotmut))begin end
  if($value$plusargs("ROTATE=%d",rotate))begin end
  $readmemh({dir,"/cfg.hex"},cfg);$readmemh({dir,"/a.hex"},a);$readmemh({dir,"/b.hex"},b);
  $readmemh({dir,"/o.hex"},eo);$readmemh({dir,"/r.hex"},er);$readmemh({dir,"/n.hex"},ns);
  G=cfg[0];N=cfg[1];K=cfg[2];HASR=cfg[4];NOUT=cfg[5];OB=cfg[9];RB=cfg[10];GB=G>=96?0:(int'(cfg[3])/G)*G;PF=(N+7)/8;
  expected=8+((G*PF+3)/4)*8+2*(TL*((KMAX+63)/64)+8)+3*((NOUT+3)/4)+24+1;
  repeat(10)@(negedge clk);rst_n=1;repeat(10)@(negedge clk);start=1;@(negedge clk);start=0;
  if(protocol_mut==2)begin bad_read2=dut.clear2-6;force dut.read2=bad_read2;end
  $display("PARENT_PROTOCOL_MODE %0d",protocol_mut);
  while(!done&&elapsed<expected+20)begin @(negedge clk);elapsed=elapsed+1;end
  if(!done||cycles!=32'(expected))begin errs=errs+1;$display("TIMELINE got%0d expected%0d done%0d",cycles,expected,done);end
  if(fault!=(cfg[6]!=0||slotmut!=0))begin errs=errs+1;$display("FAULT got%0d",fault);end
  if(cfg[6]==0&&slotmut==0)for(integer i=0;i<NOUT;i=i+1)if(!seeno[i]||(HASR&&!seenr[i]))errs=errs+1;
  if(errs)$fatal(1,"TKM_STATIC FAIL errors=%0d words=%0d cycles=%0d",errs,words,cycles);
  $display("TKM_STATIC PASS words=%0d cycles=%0d",words,cycles);$finish;
 end
// Direct source capture timestamps: pre-edge controls select each actual FF.
 // Observations are admitted by the real parent w_v/calendar, never a warm mask.
 always @(posedge clk) begin:protocol_trace
  integer t; reg c0,c63; reg active;
  t=int'(dut.tick);active=rst_n&&busy;
  c0=dut.g_tiles[0].e86.u_tile.u.g_crep.g_xr[0].g_s[0].m[0];
  c63=dut.g_tiles[0].e86.u_tile.u.g_crep.g_xr[63].g_s[0].m[0];
  if(active&&(t<16||dut.clr||t+4>=int'(dut.clear2)&&t<=int'(dut.clear2)+14||wv||dut.cap_tap))
   $display("PARENT_PROTOCOL_PRE time=%0t tick=%0d clr=%b ins=%b read=%b bufv=%b clearX0=%b clearX63=%b cap=%b wv=%b first=%0d clear2=%0d read2=%0d second=%0d",$time,t,dut.clr,dut.entry_v,dut.read_v,dut.buf_valid,c0,c63,dut.cap_tap,wv,dut.first,dut.clear2,dut.read2,dut.second);
  #0.001;
  if(active&&protocol_mut==0&&(t==4||t==int'(dut.clear2)+3)&&(!c0||dut.g_tiles[0].e86.u_tile.u.X[0]!==0))$fatal(1,"PROTOCOL_CLEAR_X0");
  if(active&&protocol_mut==0&&(t==4||t==int'(dut.clear2)+3)&&(!c63||dut.g_tiles[0].e86.u_tile.u.X[63]!==0))$fatal(1,"PROTOCOL_CLEAR_X63");
  if(active&&(c0||c63))$display("PARENT_PROTOCOL_CAPTURE time=%0t oldtick=%0d X0=%h X63=%h",$time,t,dut.g_tiles[0].e86.u_tile.u.X[0],dut.g_tiles[0].e86.u_tile.u.X[63]);
 end
// Every kept clear/select copy must select the same actual capture edge.
 for(genvar pos=0;pos<64;pos=pos+1)begin:g_capture_contract
  for(genvar word=0;word<5;word=word+1)begin:g_word
   always @(posedge clk)begin
    if(rst_n&&busy&&protocol_mut==0&&(dut.tick==4||dut.tick==dut.clear2+3))begin
     if(dut.g_tiles[0].e86.u_tile.u.g_crep.g_xr[pos].g_s[word].m!==4'b0001)
      $fatal(1,"PROTOCOL_NONUNIFORM_CLEAR pos=%0d word=%0d",pos,word);
    end
   end
  end
 end
endmodule
