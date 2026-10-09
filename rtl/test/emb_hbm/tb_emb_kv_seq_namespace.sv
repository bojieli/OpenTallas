// Source-bound historical native identity compatibility gate; no integrated hub RTL.
`timescale 1ns/1fs
module tb_emb_kv_seq_namespace;
 parameter integer HOPS=0,NEG=0;
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
 wire[10:0] transmitted_axt=NEG==1?{1'b0,axt[9:0]}:axt;
 ot_qwen_die_hub_identity #(.ENABLE_IDENTITY(1)) A(.ck(ha),.rst_n(rst_n),.fck({{3{hb}},bc[0]}),.l_i({1584'b0,ba[0]}),.l_o(alo),.x3_v(axv),.x3_d(mutated_axd),.x3_tag(transmitted_axt),.x3_cr(axcr),.ar_v(aov),.ar_d(aod),.ar_tag(aot),.ar_source(aos),.ar_cr(acr),.fault(af));
 ot_qwen_die_hub_identity #(.ENABLE_IDENTITY(1)) B(.ck(hb),.rst_n(rst_n),.fck({{3{ha}},ac[HOPS]}),.l_i({1584'b0,ab[HOPS]}),.l_o(blo),.x3_v(bxv),.x3_d(bxd),.x3_tag(bxt),.x3_cr(bxcr),.ar_v(bov),.ar_d(bod),.ar_tag(bot),.ar_source(bos),.ar_cr(bcr),.fault(bf));
 reg wv=0;reg[23:0] sec=0;reg[255:0] data=0;reg[8:0] tag=0;
 wire room,wdv,cf,sf,lwv,aq,bq,au,bu;wire[8:0] wdtag,lwt;wire[23:0] lws;wire[255:0] lwd;wire[3:0] ao,bo,acan,bcan;
 reg lroom=0,ldv=0;reg[8:0] ldt=0;
 ot_qwen_kvc_write_link_bridge #(.ENABLE(1),.ROLE(0),.PC(7'd3)) C(
 .rst_n(rst_n),.local_clk(core),.hub_clk(ha),.hub_fault(af),.stop(stopa),.epoch_fence(fencea),.global_quiescent(1'b1),.next_epoch(8'd1),
 .w_v(wv),.w_sec(sec),.w_data(data),.w_tag(tag),.w_room(room),.wd_v(wdv),.wd_tag(wdtag),
 .ledger_w_v(),.ledger_w_sec(),.ledger_w_data(),.ledger_w_tag(),.ledger_w_room(1'b0),.ledger_wd_v(1'b0),.ledger_wd_tag(9'b0),
 .outstanding(ao),.canceled_at_fence(acan),.upstream_quiescent(au),.transport_quiet(aq),.fault(cf),
 .x3_v(axv),.x3_d(axd),.x3_tag(axt),.x3_cr(axcr),.ar_v(aov),.ar_d(aod),.ar_tag(aot),.ar_source(aos),.ar_cr(acr));
 ot_qwen_kvc_write_link_bridge #(.ENABLE(1),.ROLE(1),.PC(7'd3)) S(
 .rst_n(rst_n),.local_clk(ctl),.hub_clk(hb),.hub_fault(bf),.stop(stopb),.epoch_fence(fenceb),.global_quiescent(1'b1),.next_epoch(8'd1),
 .w_v(1'b0),.w_sec(24'b0),.w_data(256'b0),.w_tag(9'b0),.w_room(),.wd_v(),.wd_tag(),
 .ledger_w_v(lwv),.ledger_w_sec(lws),.ledger_w_data(lwd),.ledger_w_tag(lwt),.ledger_w_room(lroom),.ledger_wd_v(ldv),.ledger_wd_tag(ldt),
 .outstanding(bo),.canceled_at_fence(bcan),.upstream_quiescent(bu),.transport_quiet(bq),.fault(sf),
 .x3_v(bxv),.x3_d(bxd),.x3_tag(bxt),.x3_cr(bxcr),.ar_v(bov),.ar_d(bod),.ar_tag(bot),.ar_source(NEG==2?2'd1:bos),.ar_cr(bcr));
 function automatic[255:0] word(input integer i);
  integer j;begin for(j=0;j<8;j=j+1)word[j*32+:32]=32'h96131ac9^(i*103)^j;end
 endfunction
 integer issued=0,received=0,completed=0,limit=2048,cticks=0,head=0,tail=0,qn=0,checks=0;
 reg duplicate_pending=0; reg[8:0] duplicate_tag=0;
 real first_issue=-1,first_completion=-1; integer max_owned=0,source_stalls=0;
 integer due[0:4095];reg[8:0] tq[0:4095];
 // Actual service emits a registered pulse after sampling room.
 always @(posedge core)begin
  if(rst_n)begin
   wv<=0;
   if(wv&&first_issue<0)first_issue=$realtime;
   if(ao>max_owned)max_owned=ao;
   if(run&&issued<limit&&!room)source_stalls=source_stalls+1;
   if(run&&issued<limit&&(room||NEG==7))begin wv<=1;sec<=24'h120000+issued;data<=word(issued);tag<=9'h100+issued;issued=issued+1;end
   if(wdv)begin
    if(first_completion<0)first_completion=$realtime;
    if(wdtag!==((9'h100+completed)&9'h1ff))$fatal(1,"COMPLETION_TAG index=%0d got=%h",completed,wdtag);
    completed=completed+1;checks=checks+1;
   end
   if(NEG==0&&(cf||sf||af||bf))$fatal(1,"UNEXPECTED_FAULT c=%b s=%b hub=%b%b t=%0t",cf,sf,af,bf,$time);
  end
 end
 always @(posedge ctl)if(rst_n)begin
  cticks=cticks+1;ldv<=0;
  if(lwv)begin
   if(lws!==(24'h120000+received)||lwd!==word(received)||lwt!==((9'h100+received)&9'h1ff))$fatal(1,"LEDGER_DATA index=%0d",received);
   if(qn>=16)$fatal(1,"LEDGER_OVERFLOW");
   tq[tail]=lwt;due[tail]=cticks+17;tail=tail+1;qn=qn+1;received=received+1;checks=checks+1;
  end
  if(duplicate_pending)begin ldv<=1;ldt<=duplicate_tag;duplicate_pending<=0;end
  else if(NEG!=8&&qn>0&&cticks>=due[head]&&cticks%7!=0)begin ldv<=1;ldt<=NEG==3?9'h055:tq[head];
   if(NEG==5&&head==0)begin duplicate_pending<=1;duplicate_tag<=tq[head];end
   head=head+1;qn=qn-1;end
  lroom<=!stopb&&qn<=13&&!(cticks%151>=90&&cticks%151<120);
 end
 initial begin
  #0.02;rst_n=0;repeat(8)@(negedge core);rst_n=1;repeat(HOPS+40)@(negedge core);
  if(NEG==4)force C.epoch=8'd99;
  run=1;
  if(NEG==6)begin repeat(5)@(negedge core);fencea=1;end
  if(NEG==8)begin wait(S.handed!=0 && bq);@(negedge ctl);stopb=1;fenceb=1;end
  if(NEG!=0)begin
   repeat(400000)begin @(negedge core);if(cf||sf)begin if(NEG==8&&(bo==0||completed!=0))$fatal(1,"EARLY_FENCE_LOST_OWNERSHIP"); $display("PASS_EXPECTED_OUTER_NORMALIZATION_REJECTION kind=%0d c=%b s=%b completed=%0d",NEG,cf,sf,completed);$finish;end end
   $fatal(1,"NEGATIVE_MISSED");
  end
  while(completed<2048)@(negedge core);
  run=0;stopa=1;repeat(HOPS+100)@(negedge core);
  if(ao||bo||!aq||!bq)$fatal(1,"DRAIN_OWNERSHIP");
  if(tx_sequences!=2048||decoded_sequences!=2048||high_tags!=1024)$fatal(1,"SEQUENCE_COVERAGE tx=%0d dec=%0d high=%0d",tx_sequences,decoded_sequences,high_tags);
  $display("PASS_NATIVE_IDENTITY_ALL2048 tx=%0d decoded=%0d completions=%0d full510_exact=%0d high_outer_class_collisions=%0d",tx_sequences,decoded_sequences,completed,decoded_sequences,high_tags);$finish;
 end
 reg [509:0] packet_by_seq[0:2047];
 integer tx_sequences=0,decoded_sequences=0,high_tags=0;
 always @(posedge ha) if(rst_n&&axv) begin
  if(axd[486:471]!==tx_sequences[15:0]||axt!==tx_sequences[10:0])$fatal(1,"TX_SEQUENCE_PACKET");
  packet_by_seq[tx_sequences]=axd[509:0];
  tx_sequences=tx_sequences+1;
  if(axt[10])high_tags=high_tags+1;
 end
 always @(posedge ctl) if(rst_n&&S.dec_v) begin
  if(S.dec_seq!==decoded_sequences[15:0] || S.dec.o_packet!==packet_by_seq[decoded_sequences])$fatal(1,"FULL_PACKET_SEQUENCE_EXACT");
  decoded_sequences=decoded_sequences+1;
 end
 initial begin #1000000;$fatal(1,"TRANSPORT_DEADLOCK issued=%0d received=%0d completed=%0d c=%b s=%b",issued,received,completed,cf,sf);end
endmodule
