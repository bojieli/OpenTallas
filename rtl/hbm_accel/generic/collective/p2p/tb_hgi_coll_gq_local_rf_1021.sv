`timescale 1ns/1ps
module tb;
reg  clk=0;
reg  rst_n=0;
reg [1:0] qid=0;
reg [7:0] tgt=0;
reg  cfg_v=0;
reg [7:0] cfg_target=0;
reg [11:0] cfg_addr=0;
reg [255:0] cfg_data=0;
reg  desc_v=0;
reg [11:0] desc_base=0;
reg [12:0] desc_limit=0;
reg [15:0] desc_loops=0;
reg  launch_v=0;
wire  configured;
wire  tgt_fault;
wire  active;
wire  done;
wire  fault;
reg [57:0] isa_ring=0;
reg [255:0] isa_lp_data=0;
wire  ra_lp_we;
wire [2:0] ra_lp_tag;
wire [255:0] ra_lp_data;
wire  ra_state_read_add;
wire  ra_state_read_tx;
wire  ra_state_read_rr;
wire [2:0] ra_state_add_tag;
wire [2:0] ra_state_tx_tag;
wire [2:0] ra_state_rr_tag;
wire [1:0] ra_state_add_src;
wire  ra_state_add_rhs_acc;
wire  ra_state_tx_acc;
wire  ra_add_v;
wire [2:0] ra_add_tag;
wire [1:0] ra_add_src;
wire  ra_add_rhs_acc;
wire [1:0] ra_tx_inject;
wire [1:0] ra_tx_forward;
wire [2:0] ra_tx_tag;
wire [1:0] ra_tx_dst;
wire  ra_tx_result;
wire  ra_tx_acc;
wire  ra_tx_gather;
wire [3:0] ra_tx_ttl;
wire [1:0] ra_rx_slot;
wire [3:0] ra_rx_kind;
wire [3:0] ra_rx_src;
wire [5:0] ra_rx_tag;
wire  ra_rr_local;
wire [2:0] ra_rr_local_tag;
wire  rb_lp_we;
wire [2:0] rb_lp_tag;
wire [255:0] rb_lp_data;
wire  rb_state_read_tx;
wire [2:0] rb_state_tx_tag;
wire [1:0] rb_tx_inject;
wire [1:0] rb_tx_forward;
wire [2:0] rb_tx_tag;
wire [3:0] rb_tx_ttl;
wire [1:0] rb_rx_slot;
wire [3:0] rb_rx_kind;
wire [3:0] rb_rx_src;
wire [5:0] rb_rx_tag;
wire [67:0] vm_rq_lo;
wire [67:0] vm_rq_hi;
reg [1027:0] vm_rr_lo=0;
reg [1027:0] vm_rr_hi=0;
wire  ld_fire;
wire [52:0] ld_desc;
wire  ld_ev_v;
wire [9:0] ld_ev_k;
wire [1:0] ld_p_v;
wire [511:0] ld_p_d;
ot_hgi_coll_gq_issue #(.VM_RT(74))gq(.clk(clk),.rst_n(rst_n),.qid(qid),.tgt(tgt),.cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),.desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),.desc_loops(desc_loops),.launch_v(launch_v),.configured(configured),.tgt_fault(tgt_fault),.active(active),.done(done),.fault(fault),.isa_ring(isa_ring),.isa_lp_data(isa_lp_data),.ra_lp_we(ra_lp_we),.ra_lp_tag(ra_lp_tag),.ra_lp_data(ra_lp_data),.ra_state_read_add(ra_state_read_add),.ra_state_read_tx(ra_state_read_tx),.ra_state_read_rr(ra_state_read_rr),.ra_state_add_tag(ra_state_add_tag),.ra_state_tx_tag(ra_state_tx_tag),.ra_state_rr_tag(ra_state_rr_tag),.ra_state_add_src(ra_state_add_src),.ra_state_add_rhs_acc(ra_state_add_rhs_acc),.ra_state_tx_acc(ra_state_tx_acc),.ra_add_v(ra_add_v),.ra_add_tag(ra_add_tag),.ra_add_src(ra_add_src),.ra_add_rhs_acc(ra_add_rhs_acc),.ra_tx_inject(ra_tx_inject),.ra_tx_forward(ra_tx_forward),.ra_tx_tag(ra_tx_tag),.ra_tx_dst(ra_tx_dst),.ra_tx_result(ra_tx_result),.ra_tx_acc(ra_tx_acc),.ra_tx_gather(ra_tx_gather),.ra_tx_ttl(ra_tx_ttl),.ra_rx_slot(ra_rx_slot),.ra_rx_kind(ra_rx_kind),.ra_rx_src(ra_rx_src),.ra_rx_tag(ra_rx_tag),.ra_rr_local(ra_rr_local),.ra_rr_local_tag(ra_rr_local_tag),.rb_lp_we(rb_lp_we),.rb_lp_tag(rb_lp_tag),.rb_lp_data(rb_lp_data),.rb_state_read_tx(rb_state_read_tx),.rb_state_tx_tag(rb_state_tx_tag),.rb_tx_inject(rb_tx_inject),.rb_tx_forward(rb_tx_forward),.rb_tx_tag(rb_tx_tag),.rb_tx_ttl(rb_tx_ttl),.rb_rx_slot(rb_rx_slot),.rb_rx_kind(rb_rx_kind),.rb_rx_src(rb_rx_src),.rb_rx_tag(rb_rx_tag),.vm_rq_lo(vm_rq_lo),.vm_rq_hi(vm_rq_hi),.vm_rr_lo(vm_rr_lo),.vm_rr_hi(vm_rr_hi),.ld_fire(ld_fire),.ld_desc(ld_desc),.ld_ev_v(ld_ev_v),.ld_ev_k(ld_ev_k),.ld_p_v(ld_p_v),.ld_p_d(ld_p_d));
always #3 clk=~clk;
reg qclk=0;initial begin #3;qclk=1;forever #4 qclk=~qclk;end
integer qcyc=0;always @(posedge qclk)if(rst_n)qcyc<=qcyc+1;
integer cyc=0,reads=0,lps=0,rrs=0,wr=0,finished=0;
always @(posedge clk)if(rst_n)cyc<=cyc+1;
wire[279:0]cw,ccw;wire rv,rfault;wire[2:0]rt;wire[255:0]rd;
ot_hgi_coll_ring_ag #(.SPLIT_CLOCKS(1),.AG(1))ring(.clk(clk),.clk_ctl(clk),.clk_state({8{clk}}),.clk_add({8{clk}}),.rst_n(rst_n),.qid(2'd0),
.cw_i(280'd0),.ccw_i(280'd0),.cw_o(cw),.ccw_o(ccw),.lp_we(ra_lp_we),.lp_tag(ra_lp_tag),.lp_data(ra_lp_data),
.state_read_add(ra_state_read_add),.state_read_tx(ra_state_read_tx),.state_read_rr(ra_state_read_rr),
.state_add_tag(ra_state_add_tag),.state_tx_tag(ra_state_tx_tag),.state_rr_tag(ra_state_rr_tag),
.state_add_src(ra_state_add_src),.state_add_rhs_acc(ra_state_add_rhs_acc),.state_tx_acc(ra_state_tx_acc),
.add_v(ra_add_v),.add_tag(ra_add_tag),.add_src(ra_add_src),.add_rhs_acc(ra_add_rhs_acc),
.tx_inject(ra_tx_inject),.tx_forward(ra_tx_forward),.tx_tag(ra_tx_tag),.tx_dst(ra_tx_dst),.tx_result(ra_tx_result),.tx_acc(ra_tx_acc),
.tx_gather(ra_tx_gather),.tx_ttl(ra_tx_ttl),.rx_slot(ra_rx_slot),.rx_kind(ra_rx_kind),.rx_src(ra_rx_src),.rx_tag(ra_rx_tag),
.rr_local(ra_rr_local),.rr_local_tag(ra_rr_local_tag),.rr_v(rv),.rr_tag(rt),.rr_d(rd),.fault(rfault));
wire[527:0]ob0,ob1;wire[267:0]rb0,rb1;wire[260:0]cb0,cb1;
wire sfault,rc_coll,cqfault,rrwv;wire[4:0]rrwa;wire[255:0]rrwd;
reg redsv=0;reg[31:0]redtag=0;wire[31:0]sfux;
ot_hbm_su_static_cxport_rc_s cs(.clk_s(clk),.rst_s_n(rst_n),.rr_v(rv),.rr_tag(rt),.rr_d(rd),.ro_v(16'd0),.ro_x(512'd0),
.ob0(ob0),.ob1(ob1),.rb0(rb0),.rb1(rb1),.cb0(cb0),.cb1(cb1),.sfault_s(sfault),.rc_coll(rc_coll));
ot_hbm_su_static_cxport_rc_q cq(.clk_q(qclk),.rst_q_n(rst_n),.red_sv(redsv),.red_tag(redtag),.red_x(32'd0),
.rr_wv(rrwv),.rr_wa(rrwa),.rr_wd(rrwd),.red_sel(12'd0),.sfu_x(sfux),.ob0(ob0),.ob1(ob1),.rb0(rb0),.rb1(rb1),
.cb0(cb0),.cb1(cb1),.sfault_s(sfault),.rc_coll(rc_coll),.fault(cqfault));
reg[53:0]rf_cmd=0;wire[127:0]rf_word;wire[35:0]rf_bcmd;wire qfault;
ot_hbm_su_static_qcore_r13 #(.COLLPORT(1),.RF_LOCAL(1),.PRETREE(1))core(.clk_ctl(qclk),.rst_n(rst_n),
.rf_rd_cmd(rf_cmd),.red_cmd(74'd0),.rf_drain_cmd(2'd0),.slice_x(128'd0),.slice_t(268'd0),
.rf_wv(4'd0),.rf_wa(32'd0),.rf_wd(128'd0),.rf_bword(rf_word),.rf_bcmd(rf_bcmd),
.rr_wv(rrwv),.rr_wa(rrwa),.rr_wd(rrwd),.sfu_x(sfux),.fault(qfault));
// Exact native request/response age: old six-stagebank+register, plus74
// existing declared GQ path edges. No output or RFword injection.
reg[256:0]mp[0:79];reg[256:0]ret=0;

always @*begin vm_rr_lo=0;vm_rr_hi=0;vm_rr_lo[0+:257]=ret;end
always @(posedge clk)begin
 ret<=mp[79];for(integer i=79;i>0;i=i-1)mp[i]<=mp[i-1];mp[0]<=0;
 if(vm_rq_lo[16])begin
  if(vm_rq_lo[15:0]!==16'd6248)$fatal(1,"READ_SECTOR");
  mp[0]<={1'b1,224'd0,32'h417deb6d};reads<=reads+1;$display("VMREAD cyc=%0d",cyc);
 end
 if(ra_lp_we)begin lps<=lps+1;if(ra_lp_data[31:0]!==32'h417deb6d)$fatal(1,"LP_DATA");$display("LOCAL_LOAD cyc=%0d",cyc);end
 if(rv)begin rrs<=rrs+1;if(rd[31:0]!==32'h417deb6d)$fatal(1,"RR_DATA");$display("RING_RR cyc=%0d",cyc);end
 if(done)begin finished<=finished+1;$display("GQ_DONE cyc=%0d",cyc);end
 if(gq.fire)$display("GQ_FIRE cyc=%0d",cyc);
 if(rst_n&&(fault||tgt_fault||rfault||sfault||cqfault||qfault))$fatal(1,"FAULT cyc=%0d gq%0d ring%0d sf%0d cq%0d q%0d",cyc,fault,rfault,sfault,cqfault,qfault);
 if(rst_n&&(cw[279]||ccw[279]||ld_fire||ld_p_v||rb_lp_we||rb_tx_inject||rb_rx_slot))$fatal(1,"UNEXPECTED_PEER_OR_LANDING");
 if(cyc>900)$fatal(1,"TIMEOUT");
end
always @(negedge clk)begin
 isa_ring=0;
 if(cyc==152)isa_ring=58'd1<<11;
 if(cyc==154)isa_ring=58'd1<<54;
end
always @(posedge qclk)if(rrwv)begin wr<=wr+1;$display("RF_INGRESS stream=%0d serial=%0d",cyc,qcyc);if(rrwa!==1||rrwd[31:0]!==32'h417deb6d)$fatal(1,"RF_INGRESS");end
initial begin
 for(integer i=0;i<80;i=i+1)mp[i]=0;
 #24;rst_n=1;tgt=176;qid=0;
 repeat(16)@(negedge qclk);redsv=1;$display("RF_ARM stream=%0d serial=%0d",cyc,qcyc);redtag=(32'd1<<23)|(32'd1<<13)|(32'd1<<18);
 @(negedge qclk);redsv=0;
 repeat(4)@(negedge clk);cfg_v=1;cfg_target=176;cfg_addr=0;
 cfg_data=(256'hc7a1<<240)|(256'd1<<101)|(256'd128<<85)|(256'd8<<69)|(256'd6248<<37)|(256'd1<<19)|(256'd8<<3);
 @(negedge clk);cfg_v=0;repeat(4)@(negedge clk);desc_v=1;desc_base=0;desc_limit=1;desc_loops=1;
 @(negedge clk);desc_v=0;repeat(4)@(negedge clk);launch_v=1;
 @(negedge clk);launch_v=0;
 repeat(150)@(negedge qclk);
 rf_cmd=(54'd256|54'd8)<<9;
 repeat(8)@(negedge qclk);
 if(rf_word[32+:32]!==32'h417deb6d||reads!=1||lps!=1||rrs!=1||wr!=1||finished!=1)$fatal(1,"FINAL reads%0d lp%0d rr%0d wr%0d done%0d RF%h",reads,lps,rrs,wr,finished,rf_word[32+:32]);
 $display("SELECTED_I10_GQ_LOCAL_TO_RF_PASS reads=%0d lp=%0d rr=%0d rf=%h",reads,lps,rrs,rf_word[32+:32]);$finish;
end
endmodule
