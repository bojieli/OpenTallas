`timescale 1ns/1ps
module tb_qwen_kvc_ctrl_cancel_bridge;
 parameter integer HOPS=54,NEG=0,INFLIGHT=0,FENCE=0;
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
 wire[511:0] mutated_axd=axd;
 ot_qwen_die_hub_identity #(.ENABLE_IDENTITY(1)) A(.ck(ha),.rst_n(rst_n),.fck({{3{hb}},bc[0]}),.l_i({1584'b0,ba[0]}),.l_o(alo),.x3_v(axv),.x3_d(mutated_axd),.x3_tag(axt),.x3_cr(axcr),.ar_v(aov),.ar_d(aod),.ar_tag(aot),.ar_source(aos),.ar_cr(acr),.fault(af));
 ot_qwen_die_hub_identity #(.ENABLE_IDENTITY(1)) B(.ck(hb),.rst_n(rst_n),.fck({{3{ha}},ac[HOPS]}),.l_i({1584'b0,ab[HOPS]}),.l_o(blo),.x3_v(bxv),.x3_d(bxd),.x3_tag(bxt),.x3_cr(bxcr),.ar_v(bov),.ar_d(bod),.ar_tag(bot),.ar_source(bos),.ar_cr(bcr),.fault(bf));
 reg wv=0;reg[23:0] sec=0;reg[255:0] data=0;reg[8:0] tag=0;
 wire cancel_v,cancel_take;wire[8:0]cancel_tag;integer cancels=0;
 wire room,wdv,cf,sf,lwv,aq,bq,au,bu;wire[8:0] wdtag,lwt;wire[23:0] lws;wire[255:0] lwd;wire[3:0] ao,bo,acan,bcan;
 wire lroom,ldv;wire[8:0] ldt;
 ot_qwen_kvc_write_link_bridge_cancel #(.ENABLE(1),.ROLE(0),.PC(7'd3)) C(
 .rst_n(rst_n),.local_clk(core),.hub_clk(ha),.hub_fault(af),.stop(stopa),.epoch_fence(fencea),.global_quiescent(1'b1),.next_epoch(8'd1),
 .w_v(wv),.w_sec(sec),.w_data(data),.w_tag(tag),.w_room(room),.wd_v(wdv),.wd_tag(wdtag),
 .ledger_w_v(),.ledger_w_sec(),.ledger_w_data(),.ledger_w_tag(),.ledger_w_room(1'b0),.ledger_wd_v(1'b0),.ledger_wd_tag(9'b0),.ledger_cancel_v(1'b0),.ledger_cancel_tag(9'b0),.ledger_cancel_take(),
 .outstanding(ao),.canceled_at_fence(acan),.upstream_quiescent(au),.transport_quiet(aq),.fault(cf),
 .x3_v(axv),.x3_d(axd),.x3_tag(axt),.x3_cr(axcr),.ar_v(aov),.ar_d(aod),.ar_tag(aot),.ar_source(aos),.ar_cr(acr));
 ot_qwen_kvc_write_link_bridge_cancel #(.ENABLE(1),.ROLE(1),.PC(7'd3)) S(
 .rst_n(rst_n),.local_clk(ctl),.hub_clk(hb),.hub_fault(bf),.stop(stopb||svc_stop),.epoch_fence(fenceb),.global_quiescent(1'b1),.next_epoch(8'd1),
 .w_v(1'b0),.w_sec(24'b0),.w_data(256'b0),.w_tag(9'b0),.w_room(),.wd_v(),.wd_tag(),
 .ledger_w_v(lwv),.ledger_w_sec(lws),.ledger_w_data(lwd),.ledger_w_tag(lwt),.ledger_w_room(lroom),.ledger_wd_v(ldv),.ledger_wd_tag(ldt),.ledger_cancel_v(cancel_v),.ledger_cancel_tag(cancel_tag),.ledger_cancel_take(cancel_take),
 .outstanding(bo),.canceled_at_fence(bcan),.upstream_quiescent(bu),.transport_quiet(bq),.fault(sf),
 .x3_v(bxv),.x3_d(bxd),.x3_tag(bxt),.x3_cr(bxcr),.ar_v(bov),.ar_d(bod),.ar_tag(bot),.ar_source(bos),.ar_cr(bcr));
 reg cmd_v=0;reg[31:0]cmd=0;wire cmd_credit,svc_busy,svc_fault;
 wire sched_v;wire[4:0]sched_bank,sched_col;
 wire phy_row_v,phy_col_v,phy_col_we;wire[2:0]phy_row_op;
 wire[4:0]phy_row_bank,phy_col_bank,phy_col_col;wire[18:0]phy_row_row;
 wire[23:0]phy_w_sec;wire[255:0]phy_w_data;wire[8:0]phy_w_tag;
 reg done_v=0;reg[8:0]done_tag=0;
 wire svc_stop,quarantine,refresh_req,epoch_ready;
 wire[4:0]cancel_count;wire[6:0]committed_count;
 reg refresh_ack=0,upstream_quiescent=0,epoch_advance=0;
 ot_qwen_ctrl_write_cancel_service_pc #(.ENABLE(1),.PC(3)) service(
 .clk(ctl),.rst_n(rst_n),.cmd_v(cmd_v),.cmd(cmd),.read_credit(3'b0),
 .cmd_credit(cmd_credit),.busy(svc_busy),.fault(svc_fault),
 .w_v(lwv),.w_sec(lws),.w_data(lwd),.w_tag(lwt),.w_room(lroom),
 .sched_v(sched_v),.sched_bank(sched_bank),.sched_col(sched_col),
 .phy_row_v(phy_row_v),.phy_row_op(phy_row_op),.phy_row_bank(phy_row_bank),.phy_row_row(phy_row_row),
 .phy_col_v(phy_col_v),.phy_col_we(phy_col_we),.phy_col_bank(phy_col_bank),.phy_col_col(phy_col_col),
 .phy_w_sec(phy_w_sec),.phy_w_data(phy_w_data),.phy_w_tag(phy_w_tag),
 .done_v(done_v),.done_tag(done_tag),.wd_v(ldv),.wd_tag(ldt),
 .cancel_v(cancel_v),.cancel_tag(cancel_tag),.cancel_take(cancel_take),
 .stop(svc_stop),.quarantine(quarantine),.refresh_req(refresh_req),.refresh_ack(refresh_ack),
 .upstream_quiescent(upstream_quiescent),.epoch_advance(epoch_advance),.epoch_ready(epoch_ready),
 .cancel_count(cancel_count),.committed_count(committed_count));
 function automatic[255:0]word(input integer i);
 integer j;begin for(j=0;j<8;j=j+1)word[j*32+:32]=32'h96131ac9^(i*103)^j;end endfunction
 function automatic[23:0]sector(input integer i);
 reg[14:0]s;reg[4:0]bk;begin bk=5'(i);s={bk[4:2],5'b0,5'd3,bk[1:0]};sector={7'd7,s[7],s[6],2'b0,s[14:8],s[5:0]};end endfunction
 integer issued=0,received=0,completed=0,limit=16,cticks=0,head=0,tail=0;
 integer sent=0,acked=0,reads=0,writes=0,checks=0,max_owned=0;
 integer due[0:63],wr_tick[0:63];reg[8:0]tq[0:63];
 reg arb_enable=0,hand_allow=1,faulted=0;
 real first_issue=-1,first_wr=-1,first_completion=-1;
 always @(posedge core)if(rst_n)begin
  wv<=0;
  if(wv&&first_issue<0)first_issue=$realtime;
  if(ao>max_owned)max_owned=ao;
  if(run&&issued<limit&&room)begin
   wv<=1;sec<=sector(issued);data<=word(issued);tag<=9'h100+issued;issued=issued+1;
  end
  if(wdv)begin
   if(first_completion<0)first_completion=$realtime;
   if(wdtag!==(9'h100+completed)||completed>=writes)$fatal(1,"SOURCE_COMPLETION_CUSTODY");
   completed=completed+1;checks=checks+1;
  end
  if((cf||sf||af||bf)&&!FENCE)$fatal(1,"LINK_FAULT c=%b s=%b hub=%b%b",cf,sf,af,bf);
 end
 always @(posedge ctl)if(rst_n)begin
  cticks=cticks+1;
  if(cancel_v&&cancel_take)begin
   if(!faulted || cancel_tag!==9'(16+256+cancels) || committed_count!=0)$fatal(1,"WRONG_TYPED_CANCEL");
   cancels=cancels+1;
  end
  if(cmd_v)sent=sent+1;
  if(cmd_credit)acked=acked+1;
  if(quarantine)$fatal(1,"LEDGER_QUARANTINE");
  if(lwv)begin
   if(lws!==sector(received)||lwd!==word(received)||lwt!==(9'h100+received))$fatal(1,"NATIVE_DATA");
   received=received+1;checks=checks+1;
  end
  if(phy_col_v&&!phy_col_we)reads=reads+1;
  if(phy_col_we)begin
   if(faulted||phy_w_sec!==sector(writes)||phy_w_data!==word(writes)||phy_w_tag!==(9'h100+writes))$fatal(1,"ACTUAL_PHY_WR_CUSTODY");
   if(first_wr<0)first_wr=$realtime;
   tq[tail]=phy_w_tag;wr_tick[tail]=cticks;due[tail]=cticks+17;tail=tail+1;writes=writes+1;
  end
  if(done_v)begin
   if(head>=tail||done_tag!==tq[head]||cticks-wr_tick[head]!=17)$fatal(1,"PHY_COMPLETION_NOT_17_TICKS_FROM_ACTUAL_WR");
   head=head+1;
  end
  if(ldv && (!done_v||ldt!==done_tag))$fatal(1,"NATIVE_COMPLETION_CUSTODY");
  if(faulted&&(phy_row_v||phy_col_v||lroom||sched_v))$fatal(1,"COMMAND_ESCAPED_ABORT");
 end
 always @(negedge ctl)if(rst_n)begin
  done_v=0;
  if(head<tail && cticks+1>=due[head]-(NEG?1:0))begin done_v=1;done_tag=tq[head];end
  if(arb_enable)begin
   cmd_v=0;
   if(hand_allow&&sched_v&&sent-acked<8&&!svc_stop)begin cmd_v=1;cmd={2'b10,20'b0,sched_col,sched_bank};end
  end
 end
 task send(input[31:0]p);begin
  @(negedge ctl);while(sent-acked>=8)@(negedge ctl);cmd=p;cmd_v=1;
  @(negedge ctl);cmd_v=0;
 end endtask
 initial begin
  #0.02;rst_n=0;repeat(8)@(negedge core);rst_n=1;
  send({2'b00,11'd32,19'd7});send({2'b01,30'b0});
  wait(reads==32);arb_enable=1;if(INFLIGHT)limit=1;run=1;
  if(INFLIGHT)begin
   wait(writes==1);@(negedge ctl);#0.01;
   service.controller.trip_seen=1;faulted=1;run=0;stopa=1;
   if(FENCE)begin
    // Spoof global readiness while an actual PHY write is outstanding.
    fenceb=1;@(negedge ctl);fenceb=0;
    if(!sf||bo!=1||completed!=0||committed_count!=1)$fatal(1,"UNSAFE_FENCE_LOST_COMMIT");
    $display("PASS actual_ctrl_bridge early_fence_rejected owned=%0d committed=%0d completed=%0d",bo,committed_count,completed);$finish;
   end
   wait(completed==1);repeat(HOPS+60)@(negedge core);
   if(ao||bo||committed_count||!svc_fault||!refresh_req||writes!=1)$fatal(1,"COMMITTED_ABORT_DRAIN");
   $display("PASS actual_ctrl_bridge fault_pending actual_wr=1 true_done=1 owned=0 no_restart=1");$finish;
  end
  wait(completed==16);run=0;stopa=1;
  wait(ao==0&&bo==0&&aq&&bq&&committed_count==0);
  // Accept four real native records, but deliberately do not hand them into
  // the scheduler. Controller fault must retain canceled ownership, not wd.
  hand_allow=0;limit=20;stopa=0;run=1;
  wait(received==20);@(negedge ctl);#0.01;
  service.controller.trip_seen=1;faulted=1;run=0;stopa=1;
  repeat(HOPS+60)@(negedge core);
  if(ao!=4||bo!=4||cancel_count!=0||cancels!=4||S.handed!=0||completed!=16||writes!=16||!aq||!bq||!refresh_req||!svc_fault)$fatal(1,"ABORT_OWNERSHIP");
  refresh_ack=1;upstream_quiescent=1;epoch_advance=1;
  repeat(5)@(negedge ctl);
  if(epoch_ready||completed!=16||!svc_fault)$fatal(1,"PREMATURE_EPOCH_RELEASE");
  $display("MEASURE source_to_wr_ns=%0.3f source_to_done_ns=%0.3f max_owned=%0d",first_wr-first_issue,first_completion-first_issue,max_owned);
  $display("PASS actual_ctrl_bridge HOPS=%0d native=20 actual_wr=16 true_done=16 typed_canceled_owned=4 init_reads=%0d checks=%0d",HOPS,reads,checks);$finish;
 end
 initial begin #20000;$fatal(1,"TIMEOUT issued=%0d native=%0d writes=%0d completed=%0d ao=%0d bo=%0d aq=%b bq=%b cc=%0d run=%b limit=%0d",issued,received,writes,completed,ao,bo,aq,bq,committed_count,run,limit);end
endmodule
