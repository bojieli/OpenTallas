`timescale 1ns/1ps
`default_nettype none
module tb;
 reg fast_clk=1,slow_clk=1;always #3 fast_clk=~fast_clk;always #4 slow_clk=~slow_clk;
 reg cold_n=0,fast_rst_n=0,slow_rst_n=0,tok_start=0,permit=0,corrupt=0;
 wire vi_re,vi_reply_ready,l_re,hq_v,caller_fault;wire [29:0] vi_addr,hq_addr;
 wire [11:0] l_addr;wire [5:0] hq_len;wire [3:0] fault_why;
 wire [4:0] rv,rr,qv,qr;
 assign rv=5'b00010&{5{vi_re&&permit}};assign qr=5'b00010&{5{vi_reply_ready}};
 wire [19:0] ren=20'h00010;
 wire [599:0] ra={450'b0,vi_addr,120'b0};
 wire [824:0] ctx={630'b0,vi_addr,165'b0};
 wire [10239:0] qdata;wire [1139:0] qowner;
 wire [29:0] reply_cookie=qowner[228+59+:30]^{29'b0,corrupt};
 reg [3:0] me_en=0;reg [119:0] me_a=0;reg [63:0] me_mask=0;reg [2047:0] me_d=0;
 wire [2:0] wr,vis,pend;wire [127:0] row_visible;wire [494:0] wc=0;
 wire parent_fault,quar;wire [7:0] debt;wire [3:0] nwa,nack;wire nra;
 reg [159:0] l_q=0,desc=0;
 integer accepted=0,delivered=0,cyc=0,held=0;
 always @(posedge fast_clk)begin
  cyc<=cyc+1;
  if(l_re)l_q<=l_addr==0 ? desc : 160'b0;
  if(vi_re&&!permit)held<=held+1;
  if(rv[1]&&rr[1])accepted<=accepted+1;
  if(qv[1]&&qr[1])delivered<=delivered+1;
  if(parent_fault||quar)$fatal(1,"unexpected provider fault");
 end
 ot_ds_native_vm_related_parent #(.ENABLE(1)) provider(
 .fast_clk(fast_clk),.slow_clk(slow_clk),.cold_n(cold_n),.fast_rst_n(fast_rst_n),.slow_rst_n(slow_rst_n),.abort_fast(1'b0),.abort_slow(1'b0),
 .r_v(rv),.r_ready(rr),.r_enable(ren),.r_addr(ra),.r_context(ctx),.q_v(qv),.q_ready(qr),.q_data(qdata),.q_owner(qowner),
 .me_en(me_en),.me_wordaddr(me_a),.me_mask(me_mask),.me_data(me_d),.row_en(128'b0),.row_addr(3840'b0),.row_data(4096'b0),
 .coll_en(4'b0),.coll_wordaddr(60'b0),.coll_data(2048'b0),.w_context(wc),.w_ready(wr),.w_visible(vis),.w_pending(pend),.row_visible_mask(row_visible),
 .fault(parent_fault),.quarantined(quar),.debt(debt),.debug_native_write_accept(nwa),.debug_native_visible(nack),.debug_native_read_accept(nra));

 ot_hdc_qstream_related_ID #(.VM_RESPONSE_WAIT(1),.FULL_SHAPE(1),.ALLOW_QE_STALL(1),.LWIN(10),.LA(8)) caller(
 .clk(fast_clk),.rst_n(fast_rst_n),.cfg_base(30'd0),.cfg_lbase(12'd0),.cfg_lead(21'd0),.cfg_rate(16'd0),.tok_start(tok_start),.pos(21'd0),
 .l_re(l_re),.l_addr(l_addr),.l_q(l_q),.vi_re(vi_re),.vi_addr(vi_addr),.vi_q(qdata[2048+:32]),
 .vi_req_ready(rr[1]&&permit),.vi_reply_v(qv[1]),.vi_reply_cookie(reply_cookie),.vi_reply_ready(vi_reply_ready),
 .wrel_v(1'b0),.qd_v(1'b0),.qd_nb(8'd0),.qd_tiles(21'd0),.qr_re(1'b0),.qr_addr(30'd0),.win_q(4352'b0),
 .hq_v(hq_v),.hq_rdy(1'b0),.hq_addr(hq_addr),.hq_len(hq_len),.hq_room(8'hff),
 .hr_v(8'b0),.hr_tag(80'b0),.hr_beat(40'b0),.hr_data(2048'b0),.fault(caller_fault),.fault_why(fault_why));
 task start;
 begin @(negedge fast_clk);tok_start=1;@(negedge fast_clk);tok_start=0;end endtask
 initial begin
  // Actual retained160-bit descriptor schema: one indirect FP8 word.
  desc[0+:30]=100;desc[30+:30]=200;desc[60+:21]=1;
  desc[84]=1;desc[85+:30]=512;desc[115+:30]=7;
  repeat(5)@(negedge slow_clk);cold_n=1;fast_rst_n=1;slow_rst_n=1;
  @(negedge fast_clk);me_en=1;me_a=32;me_mask=1;me_d=3;
  do @(posedge fast_clk);while(!wr[0]);@(negedge fast_clk);me_en=0;wait(vis[0]);wait(debt==0);
  start();wait(vi_re);
  repeat(10)begin @(negedge fast_clk);if(!vi_re||vi_addr!=512||hq_v)$fatal(1,"ID request not held or prematurely consumed");end
  permit=1;wait(hq_v);@(negedge fast_clk);
  $display("ID_BOUNDARY fault%0d requests%0d replies%0d hbm%0d len%0d rom%0d held%0d",caller_fault,accepted,delivered,hq_addr,hq_len,caller.e_rom,held);
  if(caller_fault||accepted!=1||delivered!=1||hq_addr!=457||hq_len!=17||caller.e_rom!=221||held<9)$fatal(1,"indirect ID exact native result addr%0d accepted%0d delivered%0d",hq_addr,accepted,delivered);
  wait(debt==0);$display("PASS ID_NATIVE held_request=1 matching_reply=1 macros=256 expertID=3 rom=221 hbm=457 requests=1");
  // A wrong owner cookie must never retire the accepted reply or publish HBM.
  @(negedge fast_clk);fast_rst_n=0;repeat(2)@(negedge fast_clk);fast_rst_n=1;corrupt=1;permit=1;
  start();wait(caller_fault);@(negedge fast_clk);
  if(hq_v||!caller.vi_bad||delivered!=1||accepted!=2||debt==0)$fatal(1,"wrong ID identity released accepted work");
  $display("PASS ID_NATIVE_WRONG_COOKIE debt_held=1 no_publication=1 no_unchecked_retirement=1");$finish;
 end
 initial begin repeat(20000)@(posedge fast_clk);$fatal(1,"finite ID service stalled");end
endmodule
`default_nettype wire
