`timescale 1ns/1fs
module tb_qwen_kvc_write_bridge_fenced;
 parameter integer HOPS=54,NEG=0;
 reg core=0,ha=0,hb=0,ctl=0,rst_n=0,run=0,stopa=0,stopb=0,fencea=0,fenceb=0;
 always #0.555556 core=~core;
 always #0.416667 ha=~ha;
 initial begin #0.123;forever #0.416667 hb=~hb;end
 initial begin #0.081;forever #0.512 ctl=~ctl;end
 wire [2111:0] alo,blo;wire [527:0] ab[0:HOPS],ba[0:HOPS];wire ac[0:HOPS],bc[0:HOPS];
 assign ab[0]=alo[527:0];assign ba[HOPS]=blo[527:0];assign ac[0]=ha;assign bc[HOPS]=hb;
 genvar h;generate for(h=0;h<HOPS;h=h+1)begin:path
 ot_qwen_die_link_fwd_full_tmr #(.NL(1),.ENABLE(1)) u(.rst_n(rst_n),.fclk_ab_i(ac[h]),.fclk_ab_o(ac[h+1]),.fclk_ba_i(bc[h+1]),.fclk_ba_o(bc[h]),.a_i(ab[h]),.b_o(ab[h+1]),.b_i(ba[h+1]),.a_o(ba[h]));
 end endgenerate
 wire axv,bxv,axcr,bxcr,aov,bov,acr,bcr,af,bf;wire[511:0] axd,bxd,aod,bod;wire[10:0] axt,bxt,aot,bot;wire[1:0] aos,bos;
 wire[511:0] mutated_axd=axd; wire[511:0] mutated_bxd=mutate_ack(bxd);
 ot_qwen_die_hub_identity #(.ENABLE_IDENTITY(1)) A(.ck(ha),.rst_n(rst_n),.fck({{3{hb}},bc[0]}),.l_i({1584'b0,ba[0]}),.l_o(alo),.x3_v(axv),.x3_d(mutated_axd),.x3_tag(axt),.x3_cr(axcr),.ar_v(aov),.ar_d(aod),.ar_tag(aot),.ar_source(aos),.ar_cr(acr),.fault(af));
 ot_qwen_die_hub_identity #(.ENABLE_IDENTITY(1)) B(.ck(hb),.rst_n(rst_n),.fck({{3{ha}},ac[HOPS]}),.l_i({1584'b0,ab[HOPS]}),.l_o(blo),.x3_v(bxv),.x3_d(mutated_bxd),.x3_tag(mutated_bxd[481:471]),.x3_cr(bxcr),.ar_v(bov),.ar_d(bod),.ar_tag(bot),.ar_source(bos),.ar_cr(bcr),.fault(bf));
 reg wv=0;reg[23:0] sec=0;reg[255:0] data=0;reg[8:0] tag=0;
 wire room,wdv,cf,sf,lwv,aq,bq,au,bu;wire[8:0] wdtag,lwt;wire[23:0] lws;wire[255:0] lwd;wire[3:0] ao,bo,acan,bcan;
 wire fba,fbb,fda,fdb;wire[7:0]ea,eb;reg ledger_ready=0;
 reg cancel_phase=0,cancel_v=0,inject_canceled_done=0;reg[8:0]cancel_tag=0;wire cancel_take;
 reg lroom=0,ldv=0;reg[8:0] ldt=0;
 ot_qwen_kvc_write_link_bridge_fenced #(.ENABLE(1),.ROLE(0),.PC(7'd3)) C(
 .rst_n(rst_n),.local_clk(core),.hub_clk(ha),.hub_fault(af),.stop(stopa),.fence_req(fencea),.next_epoch(8'd1),.ledger_epoch_ready(1'b0),.fence_busy(fba),.fence_done(fda),.active_epoch(ea),
 .w_v(wv),.w_sec(sec),.w_data(data),.w_tag(tag),.w_room(room),.wd_v(wdv),.wd_tag(wdtag),
 .ledger_w_v(),.ledger_w_sec(),.ledger_w_data(),.ledger_w_tag(),.ledger_w_room(1'b0),.ledger_wd_v(1'b0),.ledger_wd_tag(9'b0),.ledger_cancel_v(1'b0),.ledger_cancel_tag(9'b0),.ledger_cancel_take(),
 .outstanding(ao),.canceled_at_fence(acan),.upstream_quiescent(au),.transport_quiet(aq),.fault(cf),
 .x3_v(axv),.x3_d(axd),.x3_tag(axt),.x3_cr(axcr),.ar_v(aov),.ar_d(aod),.ar_tag(aot),.ar_source((NEG==14&&aod[507:504]==4)?2'd1:aos),.ar_cr(acr));
 ot_qwen_kvc_write_link_bridge_fenced #(.ENABLE(1),.ROLE(1),.PC(7'd3)) S(
 .rst_n(rst_n),.local_clk(ctl),.hub_clk(hb),.hub_fault(bf),.stop(stopb),.fence_req(1'b0),.next_epoch(8'd1),.ledger_epoch_ready(ledger_ready),.fence_busy(fbb),.fence_done(fdb),.active_epoch(eb),
 .w_v(1'b0),.w_sec(24'b0),.w_data(256'b0),.w_tag(9'b0),.w_room(),.wd_v(),.wd_tag(),
 .ledger_w_v(lwv),.ledger_w_sec(lws),.ledger_w_data(lwd),.ledger_w_tag(lwt),.ledger_w_room(lroom),.ledger_wd_v(ldv),.ledger_wd_tag(ldt),.ledger_cancel_v(cancel_v),.ledger_cancel_tag(cancel_tag),.ledger_cancel_take(cancel_take),
 .outstanding(bo),.canceled_at_fence(bcan),.upstream_quiescent(bu),.transport_quiet(bq),.fault(sf),
 .x3_v(bxv),.x3_d(mutated_bxd),.x3_tag(mutated_bxd[481:471]),.x3_cr(bxcr),.ar_v(bov),.ar_d(bod),.ar_tag(bot),.ar_source(bos),.ar_cr(bcr));
 function automatic[255:0] word(input integer i);
  integer j;begin for(j=0;j<8;j=j+1)word[j*32+:32]=32'h96131ac9^(i*103)^j;end
 endfunction
 integer issued=0,received=0,completed=0,limit=64,cticks=0,head=0,tail=0,qn=0,checks=0;
 reg duplicate_pending=0; reg[8:0] duplicate_tag=0;
 real first_issue=-1,first_completion=-1; integer max_owned=0,source_stalls=0;
 integer due[0:255];reg[8:0] tq[0:255];
 // Actual service emits a registered pulse after sampling room.
 always @(posedge core)begin
  if(rst_n)begin
   wv<=0;
   if(wv&&first_issue<0)first_issue=$realtime;
   if(ao>max_owned)max_owned=ao;
   if(run&&issued<limit&&!room)source_stalls=source_stalls+1;
   if(run&&issued<limit&&room)begin wv<=1;sec<=24'h120000+issued;data<=word(issued);tag<=9'h100+issued;issued=issued+1;end
   if(wdv)begin
    if(first_completion<0)first_completion=$realtime;
    if(wdtag!==(9'h100+completed))$fatal(1,"COMPLETION_TAG index=%0d got=%h",completed,wdtag);
    completed=completed+1;checks=checks+1;
   end
   if((NEG==0||NEG==7||NEG==11)&&(cf||sf||af||bf))$fatal(1,"UNEXPECTED_FAULT c=%b s=%b hub=%b%b t=%0t",cf,sf,af,bf,$time);
  end
 end
 always @(posedge ctl)if(rst_n)begin
  cticks=cticks+1;ldv<=0;
  if(lwv)begin
   if(lws!==(24'h120000+received)||lwd!==word(received)||lwt!==(9'h100+received))$fatal(1,"LEDGER_DATA index=%0d bridge_fault=%b/%b",received,cf,sf);
   if(qn>=16)$fatal(1,"LEDGER_OVERFLOW");
   tq[tail]=lwt;due[tail]=cticks+17;tail=tail+1;qn=qn+1;received=received+1;checks=checks+1;
  end
  if(duplicate_pending)begin ldv<=1;ldt<=duplicate_tag;duplicate_pending<=0;end
  else if(!cancel_phase&&qn>0&&cticks>=due[head]&&cticks%7!=0)begin ldv<=1;ldt<=tq[head];
   if(1'b0)begin duplicate_pending<=1;duplicate_tag<=tq[head];end
   head=head+1;qn=qn-1;end
  if(inject_canceled_done)begin ldv<=1;ldt<=9'h140;end
  lroom<=!stopb&&qn<=13&&!(cticks%151>=90&&cticks%151<120);
 end

 function automatic[31:0] crc(input[477:0] body);
  reg[31:0]v;integer b;begin v=32'hffffffff;
   for(b=477;b>=0;b=b-1)v={v[30:0],1'b0}^((v[31]^body[b])?32'h04c11db7:0);
   crc=v^32'hffffffff;
  end
 endfunction
 function automatic[511:0] mutate_ack(input[511:0] d);
  reg[509:0]p;begin p=d[509:0];
   if(p[505:502]==4)begin
    case(NEG)
     3:p[214]=!p[214];
     4:p[215+:25]=p[190+:25];
     5:p[438]=!p[438];
     6:p[471]=!p[471];
     12:p[494]=!p[494];
     13:p[487]=!p[487];
    endcase
    p[31:0]=crc(p[509:32]);
   end
   mutate_ack={d[511:510],p};
  end
 endfunction
 reg[509:0]saved_ack=0,saved_done=0;
 integer ack_sent=0,fence_sent=0;
 always @(posedge hb)if(bxv)begin
  if(bxd[505:502]==2&&saved_done==0)saved_done=bxd[509:0];
  if(bxd[505:502]==4)begin ack_sent=ack_sent+1;saved_ack=bxd[509:0];end
 end
 always @(posedge ha)if(axv&&axd[505:502]==3)begin
  fence_sent=fence_sent+1;
  if(NEG==11&&(axd[486:471]!=16'hffff||axd[470:462]!=1))$fatal(1,"FFFF_WATERMARK");
 end
 task request_fence;
  begin @(negedge core);fencea=1;@(negedge core);fencea=0;end
 endtask
 task inject_packet(input[509:0]packet);
  begin
   @(negedge ctl);while(!S.tx_ready)@(negedge ctl);
   force S.transport.tx_v=1'b1;
   force S.transport.tx_packet=packet;
   @(negedge ctl);release S.transport.tx_v;release S.transport.tx_packet;
  end
 endtask
 task await_source_fault(input integer expected_epoch,expected_owned);
  integer watchdog;begin watchdog=0;
   while(!cf)begin @(negedge core);watchdog=watchdog+1;if(watchdog>1000)$fatal(1,"EXPECTED_SOURCE_FAULT_MISSING");end
   if(ea!=expected_epoch||ao!=expected_owned||wdv)$fatal(1,"FAULT_CHANGED_OWNERSHIP");
   $display("PASS_FENCE_NEGATIVE kind=%0d epoch=%0d retained=%0d",NEG,ea,ao);$finish;
  end
 endtask
 initial begin
  #0.02;rst_n=0;repeat(8)@(negedge core);rst_n=1;
  if(NEG==1)begin
   repeat(15)@(negedge ctl);force S.enc_i_v=1'b1;
   @(negedge ctl);release S.enc_i_v;
   await_source_fault(0,0);
  end
  if(NEG==11)begin
   C.next_seq=16'hfffe;S.next_seq=16'hfffe;limit=2;
  end
  // Start immediately after cold POR, with no implicit link-online delay.
  run=1;
  if(NEG==11)begin
   while(completed<2)@(negedge core);
   run=0;stopa=1;stopb=1;ledger_ready=1;
   request_fence();wait(fda);@(negedge core);
   if(ea!=1||eb!=1||ao||bo||fence_sent!=1)$fatal(1,"FFFF_FENCE_FAILED");
   limit=4;stopa=0;stopb=0;run=1;
   while(completed<4)@(negedge core);
   if(C.next_seq!=2||S.next_seq!=2||C.exhausted||S.exhausted)$fatal(1,"FFFF_NEW_EPOCH");
   $display("PASS_FENCE_FFFF checks=%0d next_seq=%0d",checks,C.next_seq);$finish;
  end
  while(completed<64)@(negedge core);
  run=0;stopa=1;repeat(HOPS+50)@(negedge core);
  if(ao||bo||!aq||!bq)$fatal(1,"INITIAL_DRAIN");
  cancel_phase=1;stopb=0;stopa=0;limit=68;run=1;
  while(issued<68)@(negedge core);
  repeat(3)@(negedge core);run=0;stopa=1;
  while(bo!=4||ao!=4||received!=68)@(negedge core);
  stopb=1;ledger_ready=(NEG==7);
  request_fence();wait(fbb);
  repeat(30)@(negedge ctl);
  if(ack_sent||fda||fdb||ea||eb||ao!=4||bo!=4)$fatal(1,"EARLY_FENCE_DISCARDED_HANDED");
  for(integer ci=0;ci<4;ci=ci+1)begin
   @(negedge ctl);cancel_v=1;cancel_tag=9'h140+ci;
   @(negedge ctl);cancel_v=0;
  end
  head=tail;qn=0;ledger_ready=1;
  if(NEG==8||NEG==9)begin
   wait(S.fstate==2&&S.enc_v);@(negedge ctl);
   if(NEG==8)begin ldv=1;ldt=9'h055;end
   else begin cancel_v=1;cancel_tag=9'h055;end
   @(negedge ctl);ldv=0;cancel_v=0;
   repeat(HOPS+40)@(negedge core);
   if(!sf||ack_sent||ea||eb||ao!=4||bo!=4)$fatal(1,"SAME_EDGE_FAULT_COMMITTED_ACK");
   $display("PASS_FENCE_NEGATIVE kind=%0d same_edge_commit_veto=1",NEG);$finish;
  end
  if((NEG>=3&&NEG<=6)||NEG==12||NEG==13||NEG==14)await_source_fault(0,4);
  wait(fda);@(negedge core);
  if(ea!=1||eb!=1||ao||bo||acan!=4||bcan!=4||completed!=64||ack_sent!=1||fence_sent!=1)$fatal(1,"INBAND_FENCE");
  if(C.transport.txq.wr_bin!=5||S.transport.txq.wr_bin!=1||C.transport.returns!=1||S.transport.returns!=5)$fatal(1,"TRANSPORT_COUNTER_RESET");
  if(NEG==2)begin inject_packet(saved_ack);await_source_fault(1,0);end
  if(NEG==10)begin inject_packet(saved_done);await_source_fault(1,0);end
  cancel_phase=0;completed=68;limit=100;stopa=0;stopb=0;ledger_ready=0;run=1;
  while(completed<100)@(negedge core);
  run=0;stopa=1;repeat(HOPS+50)@(negedge core);
  if(ao||bo||!aq||!bq)$fatal(1,"FINAL_DRAIN");
  $display("PASS fenced_bridge HOPS=%0d NEG=%0d writes=96 canceled=4 checks=%0d epochs=2 control_flits=%0d/%0d",HOPS,NEG,checks,fence_sent,ack_sent);$finish;
 end
 initial begin #20000;$fatal(1,"TIMEOUT issued=%0d received=%0d completed=%0d c=%b s=%b fs=%0d/%0d",issued,received,completed,cf,sf,C.fstate,S.fstate);end
endmodule
