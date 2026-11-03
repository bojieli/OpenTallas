`timescale 1ns/1fs
// HEAD tail publisher (option A) lockstep bench.
// Three PART1 engines with the selected native HEAD parameters (B-pilot set: REGROOT3, MEM_EXTRA8, MUL8/ACC7/TREE7,
// XTX2, HIER2 hard leaves) share one ROM/X stream:
//   r  = the ORIGINAL rc14 ot_qwen_w12_matvec_part (renamed ref_w12_matvec_part, body byte-identical)
//   d0 = the rc16 copy, TAILPUB 0 (must equal r on every output, every cycle)
//   d1 = the rc16 copy, TAILPUB 1 (the real publisher, checked fatally)
//   m1..m5 = TAILPUB 1 bench mutants TPMUT 1..5 (row compare off by one, block149 never masked, predicate line one
//   edge short, lease guard ignored, line one edge long): each must be CAUGHT by the same checks in some scenario;
//   d0 against the contract is the raw-publisher control (it must FAIL the contract on a q4/q5 HEAD op)
// Checked every cycle: d1 equals r on every output except t_vout (requests, data, faults, ready/idle, dates),
// and d1.t_vout == r.t_vout && expected_visible(op, raw ordinal), the expectation computed here independently from
// the HEAD station contract (row0 = t*768 + q*128 + j*16 < nout, only on HEAD-lease ops).  Genuine contexts (tile0
// block0 / tile639 block148) also check every raw and published word against Codex's independent hdc_golden prefix.
`define TP_OUTS(P) \
 wire P``_ready,P``_idle,P``_wr,P``_sre,P``_kre,P``_ov,P``_amany,P``_mxwe,P``_fault,P``_tv,P``_tf,P``_act; \
 wire[23:0]P``_wa,P``_sad,P``_mxa;wire[3:0]P``_sgre,P``_xre,P``_owe;wire[95:0]P``_kad,P``_xad,P``_oad; \
 wire[63:0]P``_om;wire[2047:0]P``_od;wire[17:0]P``_ami;wire[31:0]P``_amv;wire[15:0]P``_mxm,P``_prog; \
 wire[511:0]P``_mxd,P``_td;wire[95:0]P``_sad4;
`define TP_PORTS(P) ( \
  .ck_lsl({8{clk}}),.ck_tx({8{clk}}),.ck_reg({4{clk}}),.clk(clk),.rst_n(rst),.go(go),.go_cp({32{go}}),.ready(P``_ready),.idle(P``_idle), \
  .i_nout(nout),.i_tiles(tiles),.i_k(bk),.i_wsrc(ws),.i_wbase(base),.i_ts(ts),.i_ks(ks),.i_js(js), \
  .i_xbase(xb),.i_xks(xks),.i_xjs(xjs),.i_xcs(xcs),.i_jsh(jsh),.i_split(split),.i_split_copy(split), \
  .i_wcs(wcs),.i_round(rounding),.i_obase(ob),.i_ots(ots),.i_ojs(ojs),.i_mmode(mm),.i_oen(oe),.i_amax(am),.i_rmax(rm),.i_mbase(mb), \
  .wrom_re(P``_wr),.wrom_addr(P``_wa),.wrom_q(rq),.scale_re(P``_sre),.scale_gre(P``_sgre),.scale_addr(P``_sad4[95:0]),.scale_q(1024'd0), \
  .kv_re(P``_kre),.kv_addr(P``_kad),.kv_q(2048'd0),.x_re(P``_xre),.x_addr(P``_xad),.x_q(xq),.ov(P``_ov),.o_we(P``_owe),.o_addr(P``_oad),.o_mask(P``_om),.o_data(P``_od), \
  .am_idx(P``_ami),.am_val(P``_amv),.am_any(P``_amany),.mx_we(P``_mxwe),.mx_addr(P``_mxa),.mx_mask(P``_mxm),.mx_data(P``_mxd),.progress(P``_prog),.fault(P``_fault), \
  .i_gbase(gb),.t_in(512'd0),.t_fault_in(1'b0),.t_out(P``_td),.t_vout(P``_tv),.t_fault(P``_tf),.active_o(P``_act))
`define TP_PARAMS .W(16),.G(4),.IL(8),.AW(24),.NW(18),.INT8_WEIGHT(1),.INT8_SCALE_WCS_BASE(1), \
  .PART(1),.GT(3072),.GBASE_PORT(1),.SMIN(7),.NX(0),.MEM_EXTRA(8),.ACC_LAT(7),.TREE_LAT(7), \
  .FAST_ISSUE(1),.KV_PREP(4),.MUL_LAT(8),.WCONV(1),.LRST(3),.HIER(2),.HIER_HARD(1),.LRR(1),.XTX(2), \
  .LOCAL_ROOTS(1),.CHILD_CLOCKS(1),.REGROOT(3),.ANR(1)
`define TP_BUNDLE(P) {P``_ready,P``_idle,P``_wr,P``_wa,P``_sre,P``_sgre,P``_sad4[95:0],P``_kre,P``_kad,P``_xre,P``_xad,P``_ov,P``_owe,P``_oad,P``_om,P``_od, \
  P``_ami,P``_amv,P``_amany,P``_mxwe,P``_mxa,P``_mxm,P``_mxd,P``_prog,P``_fault,P``_td,P``_tf,P``_act}
module tb_head_tailpub_lockstep;
 reg clk=0;always #0.416500 clk=~clk;
 reg rst=0,go=0;integer cyc=0,fd;
 reg[23:0]base;reg[31:0]gb;reg[17:0]nout,tiles;
 reg[378:0]ib;reg[378:0]ibs[0:3];reg[31:0]H[0:4095];reg[511:0]rawgold[0:63];
 integer scen=0,gold=0;
 // op queue (in issue order): raw words, nout, tiles, K, lease, gb
 integer nop=0,curop=0,opraw[0:3],opn[0:3],opk[0:3],oplease[0:3],opbase[0:3];
 integer nraw=0,npub=0,opord=0,firstpub=-1,lastpub=-1,firstraw=-1,lastraw=-1,nreq=0;
 integer pubcnt[0:3],rawcnt[0:3];
 reg[127:0]xread;wire[127:0]xq;wire[1023:0]rq;
 `TP_OUTS(r) `TP_OUTS(d0) `TP_OUTS(d1) `TP_OUTS(m1) `TP_OUTS(m2) `TP_OUTS(m3) `TP_OUTS(m4) `TP_OUTS(m5)
 native_head_rom_return_cut rom(.clk(clk),.rst_n(rst),.wrom_re(r_wr),.wrom_addr(r_wa[17:0]),.wrom_q(rq));
 always @(posedge clk)if(r_wr)for(integer xg=0;xg<4;xg=xg+1)
  xread[32*xg+:32]<=H[(8*((gb+xg)&511)+((r_wa-base)>>3))&4095];
 ot_hdc_delay #(.W(128),.D(8)) xreturn(.clk(clk),.rst_n(rst),.d(xread),.q(xq));
 wire[17:0]bn,bt,bk;wire ws,rounding,mm,oe,am,rm;
 wire[23:0]wb,ts,ks,js,xb,xks,xjs,xcs,wcs,ob,ots,ojs,mb;
 wire[2:0]jsh;wire[3:0]split;
 assign {bn,bt,bk,ws,wb,ts,ks,js,xb,xks,xjs,xcs,jsh,split,wcs,rounding,ob,ots,ojs,mm,oe,am,rm,mb}=ib;
 ref_w12_matvec_part #(`TP_PARAMS) r `TP_PORTS(r);
 ot_qwen_w12_matvec_part #(`TP_PARAMS,.TAILPUB(0)) d0 `TP_PORTS(d0);
 ot_qwen_w12_matvec_part #(`TP_PARAMS,.TAILPUB(1),.TPMUT(0)) d1 `TP_PORTS(d1);
 ot_qwen_w12_matvec_part #(`TP_PARAMS,.TAILPUB(1),.TPMUT(1)) m1 `TP_PORTS(m1);
 ot_qwen_w12_matvec_part #(`TP_PARAMS,.TAILPUB(1),.TPMUT(2)) m2 `TP_PORTS(m2);
 ot_qwen_w12_matvec_part #(`TP_PARAMS,.TAILPUB(1),.TPMUT(3)) m3 `TP_PORTS(m3);
 ot_qwen_w12_matvec_part #(`TP_PARAMS,.TAILPUB(1),.TPMUT(4)) m4 `TP_PORTS(m4);
 ot_qwen_w12_matvec_part #(`TP_PARAMS,.TAILPUB(1),.TPMUT(5)) m5 `TP_PORTS(m5);
 wire[5:1]mtv={m5_tv,m4_tv,m3_tv,m2_tv,m1_tv};
 wire[5:1]mwork={`TP_BUNDLE(m5)!==`TP_BUNDLE(r),`TP_BUNDLE(m4)!==`TP_BUNDLE(r),`TP_BUNDLE(m3)!==`TP_BUNDLE(r),
                 `TP_BUNDLE(m2)!==`TP_BUNDLE(r),`TP_BUNDLE(m1)!==`TP_BUNDLE(r)};
 reg[5:1]caught=0;integer rawbad=0;
 // independent expectation from the HEAD station contract
 function integer expvis(input integer op,input integer ord);
  integer t,j,q,row0;
  begin
   t=ord/(opk[op]*8);j=ord%8;q=(opbase[op]>>9);
   row0=t*768+q*128+j*16;
   expvis=(!oplease[op])||(row0<opn[op]);
  end
 endfunction
 reg ev;
 always @(posedge clk)begin
  cyc=cyc+1;if(cyc>4000)$fatal(1,"TAILPUB watchdog raw=%0d pub=%0d",nraw,npub);
  #0.2;
  if(rst&&(r_fault||r_tf||d1_fault||d1_tf))$fatal(1,"PART1 fault");
  if(`TP_BUNDLE(d0)!==`TP_BUNDLE(r)||d0_tv!==r_tv)$fatal(1,"TAILPUB0_NOT_LOCKSTEP cycle=%0d",cyc);
  if(`TP_BUNDLE(d1)!==`TP_BUNDLE(r))$fatal(1,"TAILPUB1_RAW_WORK_OR_DATE_DIFFERS cycle=%0d",cyc);
  if(r_wr)nreq=nreq+1;
  if(rst)caught=caught|mwork;
  if(rst&&r_tv)begin
   while(curop<nop&&opord>=opraw[curop])begin curop=curop+1;opord=0;end
   if(curop>=nop)$fatal(1,"raw publication beyond the issued ops");
   ev=expvis(curop,opord);
   if(gold&&curop==0&&r_td!==rawgold[opord])$fatal(1,"PART1_RAW mismatch ordinal=%0d",opord);
   if(firstraw<0)firstraw=cyc;lastraw=cyc;
   for(integer mi=1;mi<=5;mi=mi+1)if(mtv[mi]!==ev)caught[mi]=1'b1;
   if(d0_tv!==ev)rawbad=rawbad+1;
   if(d1_tv!==ev)$fatal(1,"TAILPUB_PUBLISH_MISMATCH op=%0d ordinal=%0d slot=%0d published=%b expected=%b cycle=%0d",curop,opord,opord%8,d1_tv,ev,cyc);
   if(d1_tv)begin
    if(d1_td!==r_td)$fatal(1,"published data differs");
    npub=npub+1;pubcnt[curop]=pubcnt[curop]+1;if(firstpub<0)firstpub=cyc;lastpub=cyc;
    $fdisplay(fd,"PUB\t%0d\t%0d\t%0d\t%0d\t%0128h",curop,opord,opord%8,cyc,d1_td);
   end
   rawcnt[curop]=rawcnt[curop]+1;nraw=nraw+1;opord=opord+1;
  end else begin
   if(rst)caught=caught|mtv;
   if(d1_tv)$fatal(1,"TAILPUB published without a raw valid cycle=%0d",cyc);
  end
 end
 task automatic issue(input integer ibi,input integer tilen,input integer n,input integer tl,input integer wbase_ov,input integer lease);
  begin
   while(!r_ready)@(negedge clk);
   // ib = {nout18,tiles18,k18,wsrc1,wbase24,...}: K = ib[342:325], wbase = ib[323:300]
   ib=ibs[ibi];nout=n;tiles=tl;base=(wbase_ov>=0)?wbase_ov:ib[323:300];
   opraw[nop]=tl*ib[342:325]*8;opn[nop]=n;opk[nop]=ib[342:325];oplease[nop]=lease;opbase[nop]=gb;pubcnt[nop]=0;rawcnt[nop]=0;nop=nop+1;
   go=1;@(negedge clk);go=0;
  end
 endtask
 integer tile,expect0,expect1;
 initial begin
  if(!$value$plusargs("SCEN=%d",scen))$fatal(1,"SCEN required");
  if(!$value$plusargs("TILE=%d",tile))$fatal(1,"TILE required");
  if(!$value$plusargs("GOLD=%d",gold))gold=0;
  gb=4*tile;
  $readmemh("resident_ib379.hex",ibs);$readmemh("H4096_me_fp32.hex",H);
  if(gold)$readmemh("raw_prefix_expected.hex",rawgold);
  fd=$fopen($sformatf("tailpub_scen%0d_tile%0d.tsv",scen,tile),"w");
  ib=ibs[0];nout=0;tiles=1;base=0;
  repeat(24)@(negedge clk);rst=1;repeat(24)@(negedge clk);
  if(!r_ready)$fatal(1,"PART1 not ready after reset drain");
  case(scen)
   // 1: last HEAD chunk, one round, nout 560 (HEAD IB3 code base 19968)
   1: issue(3,tile,560,1,19968,1);
   // 2: first HEAD chunk shape, one round, nout 768 (Codex tile0 context, base 18432)
   2: issue(0,tile,768,1,18432,1);
   // 3: full HEAD chunk, nout 6144, 8 rounds, base 18432
   3: issue(0,tile,6144,8,18432,1);
   // 4: same last-chunk shape OUTSIDE the HEAD lease (base 17920): raw publication preserved
   4: issue(3,tile,560,1,17920,0);
   // 5: early GO: full chunk then the last chunk accepted on the first ready (old publications still draining)
   5: begin issue(0,tile,6144,8,18432,1);issue(3,tile,560,1,19968,1);end
   default:$fatal(1,"bad SCEN");
  endcase
  begin:wait_all
   integer tot,i;tot=0;for(i=0;i<nop;i=i+1)tot=tot+opraw[i];
   while(nraw<tot)@(negedge clk);
  end
  while(!r_idle)@(negedge clk);
  repeat(4)@(negedge clk);
  $fclose(fd);
  $display("PASS_TAILPUB_LOCKSTEP scen=%0d tile=%0d q=%0d ops=%0d raw=%0d published=%0d op0=%0d/%0d op1=%0d/%0d first_raw=%0d first_pub=%0d last_raw=%0d last_pub=%0d requests=%0d",
   scen,tile,gb>>9,nop,nraw,npub,pubcnt[0],rawcnt[0],(nop>1)?pubcnt[1]:0,(nop>1)?rawcnt[1]:0,firstraw,firstpub,lastraw,lastpub,nreq);
  $display("TAILPUB_CONTROLS scen=%0d tile=%0d raw_publisher_contract_mismatches=%0d mutants_caught=%b (m5..m1)",scen,tile,rawbad,caught);
  $finish;
 end
endmodule
