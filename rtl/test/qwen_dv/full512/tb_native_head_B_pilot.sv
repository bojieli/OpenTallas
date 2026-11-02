`timescale 1ns/1fs
// Public native ROM/converter + unchanged public PART1 numerical boundary.
// Fresh immutable mask contexts; no selected ROM_TILE identity retarget.
module tb_native_head_B_pilot;
 reg clk=0;always #0.416500 clk=~clk;
 reg rst=0,go=0;integer tile=0,cyc=0,nreq=0,nret=0,nraw=0,fd,idx,g;
 integer launch[0:63];reg[23:0]base;reg[31:0]gb;
 reg[17:0]nout;reg[378:0]ib;
 reg[378:0]ibs[0:3];reg[31:0]H[0:4095];reg[1023:0]romgold[0:63];reg[511:0]rawgold[0:63];
 reg[127:0]xread;wire[127:0]xq;
 wire wr;wire[23:0]wa;wire[1023:0]rq,lateq,mq;
 wire[511:0]td;wire tv,tf,fault,ready,idle;
 string control="baseline";
 wire[23:0]producer_addr=wa+(control=="wrongAddress"?24'd1:24'd0);
 native_head_rom_return_cut rom(.clk(clk),.rst_n(rst),.wrom_re(wr),.wrom_addr(producer_addr[17:0]),.wrom_q(rq));
 ot_hdc_delay #(.W(1024),.D(1)) wrongcycle(.clk(clk),.rst_n(rst),.d(rq),.q(lateq));
 assign mq=control=="wrongCycle"?lateq:rq;
 // Selected NX0 disables public X requests. Preserve it. Stream H for issued
 // group/K uses the real code request address, one read edge then delay8.
 always @(posedge clk)if(wr)for(integer xg=0;xg<4;xg=xg+1)
  xread[32*xg+:32]<=H[8*((gb+xg)&511)+((wa-base)>>3)];
 ot_hdc_delay #(.W(128),.D(8)) xreturn(.clk(clk),.rst_n(rst),.d(xread),.q(xq));
 wire[17:0]bn,bt,bk;wire ws,rounding,mm,oe,am,rm;
 wire[23:0]wb,ts,ks,js,xb,xks,xjs,xcs,wcs,ob,ots,ojs,mb;
 wire[2:0]jsh;wire[3:0]split;
 assign {bn,bt,bk,ws,wb,ts,ks,js,xb,xks,xjs,xcs,jsh,split,wcs,rounding,ob,ots,ojs,mm,oe,am,rm,mb}=ib;
 ot_qwen_w12_matvec_part #(.W(16),.G(4),.IL(8),.AW(24),.NW(18),.INT8_WEIGHT(1),.INT8_SCALE_WCS_BASE(1),
  .PART(1),.GT(3072),.GBASE_PORT(1),.SMIN(7),.NX(0),.MEM_EXTRA(8),.ACC_LAT(7),.TREE_LAT(7),
  .FAST_ISSUE(1),.KV_PREP(4),.MUL_LAT(8),.WCONV(1),.LRST(3),.HIER(2),.HIER_HARD(1),.LRR(1),.XTX(2),
  .LOCAL_ROOTS(1),.CHILD_CLOCKS(1),.REGROOT(3),.ANR(1)) part1(
  .ck_lsl({8{clk}}),.ck_tx({8{clk}}),.ck_reg({4{clk}}),.clk(clk),.rst_n(rst),.go(go),.go_cp({32{go}}),.ready(ready),.idle(idle),
  .i_nout(nout),.i_tiles(18'd1),.i_k(bk),.i_wsrc(ws),.i_wbase(base),.i_ts(ts),.i_ks(ks),.i_js(js),
  .i_xbase(xb),.i_xks(xks),.i_xjs(xjs),.i_xcs(xcs),.i_jsh(jsh),.i_split(split),.i_split_copy(split),
  .i_wcs(wcs),.i_round(rounding),.i_obase(ob),.i_ots(ots),.i_ojs(ojs),.i_mmode(mm),.i_oen(oe),.i_amax(am),.i_rmax(rm),.i_mbase(mb),
  .wrom_re(wr),.wrom_addr(wa),.wrom_q(mq),.scale_re(),.scale_gre(),.scale_addr(),.scale_q(1024'd0),
  .kv_re(),.kv_addr(),.kv_q(2048'd0),.x_re(),.x_addr(),.x_q(xq),.ov(),.o_we(),.o_addr(),.o_mask(),.o_data(),
  .am_idx(),.am_val(),.am_any(),.mx_we(),.mx_addr(),.mx_mask(),.mx_data(),.progress(),.fault(fault),
  .i_gbase(gb),.t_in(512'd0),.t_fault_in(1'b0),.t_out(td),.t_vout(tv),.t_fault(tf),.active_o());
 always @(posedge clk)begin
  cyc=cyc+1;if(cyc>1000)$fatal(1,"Bpilot watchdog req=%0d ret=%0d raw=%0d",nreq,nret,nraw);
  #0.2;
  if(rst&&(fault||tf))$fatal(1,"native PART1 fault");
  if(wr)begin
   if(nreq>=64||wa!==base+nreq)$fatal(1,"native request/address mismatch ordinal=%0d addr=%h",nreq,wa);
   launch[nreq]=cyc;nreq=nreq+1;
  end
  if(nret<nreq&&cyc==launch[nret]+9)begin
   if(mq!==romgold[nret])$fatal(1,"ROM_RESPONSE_CONTEXT_ADDRESS_CYCLE mismatch tile=%0d ordinal=%0d cycle=%0d actual=%h expected=%h",tile,nret,cyc,mq,romgold[nret]);
   $fdisplay(fd,"%0d\t%0d\t%0d\t%0d\t%0d\t%0256h",tile,nret,base+nret,launch[nret],cyc,mq);
   nret=nret+1;
  end
  if(tv)begin
   if(nraw>=64||td!==rawgold[nraw])$fatal(1,"PART1_RAW mismatch tile=%0d ordinal=%0d actual=%h expected=%h",tile,nraw,td,rawgold[nraw]);
   if(nraw==0||nraw==56)$display("RAW_SAMPLE tile=%0d ordinal=%0d lane0=%h",tile,nraw,td[31:0]);
   nraw=nraw+1;
  end
 end
 initial begin
  if(!$value$plusargs("TILE=%d",tile))$fatal(1,"TILE required");
  if($value$plusargs("CONTROL=%s",control))begin end
  if(tile!=0&&tile!=639)$fatal(1,"only immutable pilot contexts0/639");
  base=tile==0?18432:19968;gb=4*tile;nout=tile==0?768:560;
  $readmemh("resident_ib379.hex",ibs);ib=ibs[tile==0?0:3];
  $readmemh("H4096_me_fp32.hex",H);$readmemh("rom_response_expected.hex",romgold);$readmemh("raw_prefix_expected.hex",rawgold);
  fd=$fopen($sformatf("actual_ROM_transcript_%s.tsv",control),"w");if(!fd)$fatal(1,"transcript open");
  repeat(24)@(negedge clk);rst=1;repeat(24)@(negedge clk);
  if(!ready)$fatal(1,"PART1 not ready after actual reset drain");go=1;@(negedge clk);go=0;
  while(nraw<64)@(negedge clk);
  while(!idle)@(negedge clk);
  repeat(2)@(negedge clk);
  if(nreq!=64||nret!=64||nraw!=64)$fatal(1,"Bpilot counts");
  $fclose(fd);
  $display("PASS_NATIVE_B_PILOT tile=%0d raw_requests64 responses64 raw_vectors64 useful_vectors=%0d nominal833ps",tile,tile==0?64:24);$finish;
 end
endmodule
