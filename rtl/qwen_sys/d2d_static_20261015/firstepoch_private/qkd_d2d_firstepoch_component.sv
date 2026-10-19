`timescale 1ns/1ps
// Private verification component: no parent binding or physical qualification.
// Original payload captures are retained, including parallel copies.
module qkd_d2d_firstepoch_component #(
 parameter integer ENABLE_FIRST_EPOCH_GUARD=0, FIXED_IMAGE=1, ORIGINAL=0
)(input wire ck,rst_n,input wire [142:0] boot_pr,input wire [3:0] boot_image_target,
 input wire boot_image_ready,boot_image_fault,input wire [15:0] boot_image_epoch,
 input wire reload,epoch_go,halt,input wire [15:0] epoch_id,input wire epoch_valid,
 // Verification injection at actual SF pin inputs; zero is transparent.
 input wire [15:0] drop_word, input wire corrupt_half,corrupt_base,corrupt_epoch,corrupt_valid,
 input wire [7:0] corrupt_start,input wire wrong_start_epoch,
 output wire [127:0] original_outputs,output wire [31:0] calendar_outputs,
 output wire pair_ready,pair_poison,output wire [15:0] pair_epoch,
 output wire [63:0] seen_pair,output wire [1:0] base_pair,first_pair,
 output wire dispatcher_fault,bc_fault,output wire tx_event,rx_event,
 output wire [2:0] tx_port,rx_port,output wire [3:0] tx_kind,rx_kind,
 output wire [4:0] tx_beat,rx_beat,output wire cal_start_o,cal_seg_o,
 output wire [5:0] layer_o);
 `include "d2d_cal_image_mu.svh"
 wire dt,dr; wire[5:0] da; wire[31:0] dd;
 qkd_static_kv_boot_dispatch #(.LINKCFG(1)) u_dispatch (
 .ck(ck),.rst_n(rst_n),.boot_pr(boot_pr),.boot_image_target(boot_image_target),
 .boot_image_ready(boot_image_ready),.boot_image_fault(boot_image_fault),.boot_image_epoch(boot_image_epoch),
 .boot_image_digest(64'd0),.execution_active(1'b0),.sink_applied(160'd0),.local_configured(3'd0),
 .sink_fault(1'b0),.diecfg_sealed(1'b0),.diecfg_fault(1'b0),
 .link_cfg_tx_we(dt),.link_cfg_rx_we(dr),.link_cfg_addr(da),.link_cfg_data(dd),.fault(dispatcher_fault));
 // Dispatcher output metadata is captured on the same edge as link_cfg_*.
 reg[16:0] dm; reg[39:0] r0,r1; reg[16:0] m0,m1;
 always @(posedge ck or negedge rst_n)
  if (!rst_n) dm<=0;
  else dm<={boot_image_epoch,boot_pr[74] && boot_image_target==11 && !boot_image_fault && !dispatcher_fault};
 always @(posedge ck) begin
  r0<={dt,dr,da,dd}; r1<=r0; m0<=dm; m1<=m0;
 end
 wire ct,cr,cs,seg,ready,run,adm,tok; wire[5:0] ca,ly; wire[31:0] cd;
 wire[15:0] ce,se; wire cv,sv;wire bc_generation_poison;
 generate if(ORIGINAL) begin:g_original_bc
  qkd_d2d_cal_seq_pin_bc u_bc(.ck(ck),.rst_n(rst_n),.reload(reload),.epoch_go(epoch_go),.halt(halt),
  .bcfg_tx_we(r1[39]),.bcfg_rx_we(r1[38]),.bcfg_addr(r1[37:32]),.bcfg_data(r1[31:0]),
  .cfg_tx_we(ct),.cfg_rx_we(cr),.cfg_addr(ca),.cfg_data(cd),.cal_start(cs),.cal_seg(seg),
  .cal_ready(ready),.running(run),.layer(ly),.adm_done(adm),.tok_start(tok),.fault(bc_fault));
  assign ce=0;assign se=0;assign cv=0;assign sv=0;assign bc_generation_poison=0;
 end else begin:g_private_bc
  qkd_d2d_cal_seq_pin_bc_fe #(.ENABLE_FIRST_EPOCH_GUARD(ENABLE_FIRST_EPOCH_GUARD),.FIXED_IMAGE(FIXED_IMAGE)) u_bc(
  .ck(ck),.rst_n(rst_n),.reload(reload),.epoch_go(epoch_go),.halt(halt),
  .bcfg_tx_we(r1[39]),.bcfg_rx_we(r1[38]),.bcfg_addr(r1[37:32]),.bcfg_data(r1[31:0]),
  .bcfg_epoch(m1[16:1]),.bcfg_valid(m1[0]),.epoch_id(epoch_id),.epoch_valid(epoch_valid),
  .pair_epoch(pair_epoch),.pair_ready(pair_ready),.pair_poison(pair_poison),
  .cfg_epoch(ce),.cfg_valid(cv),.start_epoch(se),.start_valid(sv),.generation_poison(bc_generation_poison),
  .cfg_tx_we(ct),.cfg_rx_we(cr),.cfg_addr(ca),.cfg_data(cd),.cal_start(cs),.cal_seg(seg),
  .cal_ready(ready),.running(run),.layer(ly),.adm_done(adm),.tok_start(tok),.fault(bc_fault));
 end endgenerate
 // Exact original SF pin captures: 40 scalar cfg + 150 copies; 2 scalar start + 16 copies.
 reg qt,qr;reg[5:0] qa;reg[31:0] qd;
 (* keep="true",dont_touch="true" *) reg[11:0] sf_addr;
 (* keep="true",dont_touch="true" *) reg[127:0] sf_data;
 (* keep="true",dont_touch="true" *) reg[9:0] sf_base;
 (* keep="true",dont_touch="true" *) reg[7:0] sf_start,sf_seg;
 reg qs,qseg;reg[16:0] cfg_meta,start_meta;
 always @(posedge ck) begin
 qt<=ct;qr<=cr;qa<=ca;qd<=cd;
 sf_addr<={2{ca}};sf_data<={4{cd}};sf_base<={2{cd[4:0]}};
 sf_start<={8{cs}};sf_seg<={8{seg}};qs<=cs;qseg<=seg;
 cfg_meta<={ce,cv};start_meta<={se,sv};
 end
 wire[1:0] rr,poison,fc,cf,running;wire[31:0] seen0,seen1;wire[15:0] ep0,ep1;
 assign pair_ready=(&rr) && ep0==ep1;
 assign pair_poison=(|poison) || bc_generation_poison;assign pair_epoch=ep0;assign seen_pair={seen1,seen0};assign first_pair=fc;
 assign original_outputs={dispatcher_fault,dt,dr,da,dd,ct,cr,ca,cd,cs,seg,ready,run,ly,adm,tok,bc_fault};
 assign calendar_outputs={cf,running,tx_event,tx_port,tx_kind,tx_beat,rx_event,rx_port,rx_kind,rx_beat};
 assign cal_start_o=qs;assign cal_seg_o=qseg;assign layer_o=ly;
 generate if(ORIGINAL) begin:g_tx_original
 ot_qwen_d2d_cal_sf u_cal(.ck(ck),.rst_n(rst_n),.cfg_we((qt) && !(drop_word[15] && qa==drop_word[5:0] && drop_word[6]==1'b0)),
 .cfg_addr(sf_addr[0+:6]),.cfg_data_c(sf_data[0+:64] ^ (corrupt_half ? 64'h0000000100000000 : 64'd0)),
 .cfg_base_c(sf_base[0+:5] ^ (corrupt_base ? 5'd1 : 5'd0)),
 .start_c(sf_start[0+:4] ^ corrupt_start[0+:4]),.seg_c(sf_seg[0+:4]),.halt_c({4{halt}}),
 .ev_v(tx_event),.ev_port(tx_port),.ev_kind(tx_kind),.ev_beat(tx_beat),.running(running[0]),.fault(cf[0]));
 assign rr[0]=0;assign poison[0]=0;assign fc[0]=0;assign seen0=0;assign ep0=0;assign base_pair[0]=0;
 end else begin:g_tx_private
 ot_qwen_d2d_cal_sf_fe #(.ENABLE_FIRST_EPOCH_GUARD(ENABLE_FIRST_EPOCH_GUARD),.FIXED_IMAGE(FIXED_IMAGE),
 .EXPECTED_IMAGE(D2D_CAL_K_TX_IMG),.EXPECTED_BOOT_BASE(D2D_CAL_K_TX_SEG2[4:0]),.EXPECTED_TOKEN_BASE(D2D_CAL_K_TX_SEG1[4:0])) u_cal(
 .cfg_epoch(cfg_meta[16:1] ^ (corrupt_epoch ? 16'd1 : 16'd0)),.cfg_valid(cfg_meta[0] && !corrupt_valid),
 .start_epoch(start_meta[16:1] ^ (wrong_start_epoch ? 16'd1 : 16'd0)),.start_valid(start_meta[0]),
 .pair_ready(pair_ready),.pair_poison(pair_poison),.reload(reload),
 .receipt_ready(rr[0]),.receipt_epoch(ep0),.seen(seen0),.base_seen(base_pair[0]),.poisoned(poison[0]),.first_consumed(fc[0]),
 .ck(ck),.rst_n(rst_n),.cfg_we((qt) && !(drop_word[15] && qa==drop_word[5:0] && drop_word[6]==1'b0)),
 .cfg_addr(sf_addr[0+:6]),.cfg_data_c(sf_data[0+:64] ^ (corrupt_half ? 64'h0000000100000000 : 64'd0)),
 .cfg_base_c(sf_base[0+:5] ^ (corrupt_base ? 5'd1 : 5'd0)),
 .start_c(sf_start[0+:4] ^ corrupt_start[0+:4]),.seg_c(sf_seg[0+:4]),.halt_c({4{halt}}),
 .ev_v(tx_event),.ev_port(tx_port),.ev_kind(tx_kind),.ev_beat(tx_beat),.running(running[0]),.fault(cf[0]));
 end endgenerate
 generate if(ORIGINAL) begin:g_rx_original
 ot_qwen_d2d_cal_sf u_cal(.ck(ck),.rst_n(rst_n),.cfg_we((qr) && !(drop_word[15] && qa==drop_word[5:0] && drop_word[6]==1'b1)),
 .cfg_addr(sf_addr[6+:6]),.cfg_data_c(sf_data[64+:64] ^ (corrupt_half ? 64'h0000000100000000 : 64'd0)),
 .cfg_base_c(sf_base[5+:5] ^ (corrupt_base ? 5'd1 : 5'd0)),
 .start_c(sf_start[4+:4] ^ corrupt_start[4+:4]),.seg_c(sf_seg[4+:4]),.halt_c({4{halt}}),
 .ev_v(rx_event),.ev_port(rx_port),.ev_kind(rx_kind),.ev_beat(rx_beat),.running(running[1]),.fault(cf[1]));
 assign rr[1]=0;assign poison[1]=0;assign fc[1]=0;assign seen1=0;assign ep1=0;assign base_pair[1]=0;
 end else begin:g_rx_private
 ot_qwen_d2d_cal_sf_fe #(.ENABLE_FIRST_EPOCH_GUARD(ENABLE_FIRST_EPOCH_GUARD),.FIXED_IMAGE(FIXED_IMAGE),
 .EXPECTED_IMAGE(D2D_CAL_K_RX_IMG),.EXPECTED_BOOT_BASE(D2D_CAL_K_RX_SEG2[4:0]),.EXPECTED_TOKEN_BASE(D2D_CAL_K_RX_SEG1[4:0])) u_cal(
 .cfg_epoch(cfg_meta[16:1] ^ (corrupt_epoch ? 16'd1 : 16'd0)),.cfg_valid(cfg_meta[0] && !corrupt_valid),
 .start_epoch(start_meta[16:1] ^ (wrong_start_epoch ? 16'd1 : 16'd0)),.start_valid(start_meta[0]),
 .pair_ready(pair_ready),.pair_poison(pair_poison),.reload(reload),
 .receipt_ready(rr[1]),.receipt_epoch(ep1),.seen(seen1),.base_seen(base_pair[1]),.poisoned(poison[1]),.first_consumed(fc[1]),
 .ck(ck),.rst_n(rst_n),.cfg_we((qr) && !(drop_word[15] && qa==drop_word[5:0] && drop_word[6]==1'b1)),
 .cfg_addr(sf_addr[6+:6]),.cfg_data_c(sf_data[64+:64] ^ (corrupt_half ? 64'h0000000100000000 : 64'd0)),
 .cfg_base_c(sf_base[5+:5] ^ (corrupt_base ? 5'd1 : 5'd0)),
 .start_c(sf_start[4+:4] ^ corrupt_start[4+:4]),.seg_c(sf_seg[4+:4]),.halt_c({4{halt}}),
 .ev_v(rx_event),.ev_port(rx_port),.ev_kind(rx_kind),.ev_beat(rx_beat),.running(running[1]),.fault(cf[1]));
 end endgenerate
endmodule
