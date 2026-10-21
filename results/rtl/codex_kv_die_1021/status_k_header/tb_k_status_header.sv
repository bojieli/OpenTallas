`timescale 1ns/1ps
module tb_k_status_header;
 parameter integer MUT_LEGACY=0;
 reg ck=0;always #5 ck=~ck;
 reg rst_n=0;reg [582:0] pin=0;
 wire[23:0]hk;wire[383:0]he;wire[547:0]payload;
 reg event_v=0;wire obs_v;wire[15:0]obs_epoch;wire[207:0]obs;wire fault;
 ot_qwen_static_slot_ctl_sfm3_obs1 #(.NG(24)) h(.clk(ck),.rst_n(rst_n),.eb_c(12'd0),.epoch(8'd0),
  .wr_v(1'b0),.wr_observed_v(1'b0),.wr_slot(6'd0),.q_data(548'd0),.rd_v(1'b0),.rd_slot(6'd0),
  .rx_expect_v(1'b0),.rx_expect_slot(6'd0),.p_tx_up(1'b1),.p_rx_v(1'b0),.p_rx_flit(pin),
  .rx_flit(payload),.hk_c(hk),.he_c(he));
 wire[23:0]matched_hk=MUT_LEGACY?{24{payload[511:156]==0}}:hk;
 ot_qwen_d2d_status_rx_sfm3_obs1 #(.NG(24)) r(.ck(ck),.rst_n(rst_n),.epoch16(16'd64),
  .rx_event(event_v),.rx_slot(event_v),.ev_c({24{event_v}}),.rs_c({24{event_v}}),.hk_c(matched_hk),.he_c(he),
  .rx_payload(payload),.epoch_begin(1'b0),.fault(fault),.status_obs_v(obs_v),.status_obs_epoch16(obs_epoch),.status_obs_payload(obs));
 task tick(input integer n);repeat(n)begin @(posedge ck);#1;end endtask
 task reset;@(negedge ck);rst_n=0;event_v=0;pin=0;tick(6);@(negedge ck);rst_n=1;tick(6);endtask
 task load(input[207:0]ext,input bad_gap);
  @(negedge ck);pin={35'd0,5'd0,4'd15,6'd63,16'd64,5'd0,ext,148'd0,156'd0};
  if(bad_gap)pin[156]=1;tick(3);
  @(negedge ck);event_v=1;tick(1);@(negedge ck);event_v=0;tick(2);
 endtask
 reg[207:0]ext;reg[58:0]tag;
 initial begin
  reset();ext=0;ext[207:204]=1;
  load(ext,0);if(fault||obs!==ext||obs_epoch!==64)$fatal(1,"K_STATUS_EXTENSION_REJECTED");
  // True operation owner/epoch differs from receipt epoch and remains visible.
  tag={16'd66,6'd1,18'd20,13'd100,6'd0};ext[94]=1;ext[92:61]=1;ext[60:2]=tag;
  load(ext,0);if(fault||obs!==ext)$fatal(1,"K_STATUS_TRUE_IDENTITY_LOST");
  reset();ext[207:204]=2;load(ext,0);if(!fault)$fatal(1,"K_STATUS_UNKNOWN_VERSION_ACCEPTED");
  reset();ext=0;ext[207:204]=1;load(ext,1);if(!fault)$fatal(1,"K_STATUS_RESERVED_GAP_ACCEPTED");
  $display("K_STATUS_HEADER_PASS groups24 extension208 true_native_epoch66 owner2 receipt64 unknown_version reserved");$finish;
 end
endmodule
