`timescale 1ns/1ps
// Real static S81 collective datapath composition, native candidate.
// Clocks are delivered pins from the die PLL tree; no common-pin phase waiver.
// Configuration ROM/memory macro and production placement/phase/image are open
// qualification gates. Missing ROM fails closed, never fabricates a schedule.
module s81_static_collective_slab #(
 parameter ROM_FILE="",parameter integer CYCLES=1
)(
 input wire ck_control,input wire[7:0]ck_lane,input wire[15:0]ck_hc_lane,
 input wire rst_n,input wire[1:0]f_rank,
 input wire[84:0]c_cmd,output wire[8:0]c_done,output wire[1:0]c_st,
 output reg[14:0]t_crq,input wire[512:0]f_crs,output reg[2203:0]t_vm,
 input wire[7:0]phy_rx_valid,input wire[4095:0]phy_rx_data,
 input wire[7:0]phy_rx_fault,input wire[7:0]phy_rx_live,
 output wire[7:0]phy_tx_valid,output wire[4095:0]phy_tx_data,
 input wire[513:0]f_wfc,output wire[513:0]t_wfc,
 input wire[76:0]f_host,output wire[514:0]t_host,
 output wire[8191:0]t_hc_y,output wire t_hc_yv
);
 wire read_slot;
 wire [13:0]read_row;
 wire issue_slot;
 wire [31:0]tag;
 wire [15:0]seq;
 wire last;
 wire [3:0]rankmask;
 wire commit_slot;
 wire [31:0]commit_tag;
 wire [15:0]commit_seq;
 wire commit_last;
 wire [3:0]commit_rankmask;
 wire [59:0]commit_rows;
 wire tx_beat_slot;
 wire [1:0]tx_phase;
 wire tx_frame_slot;
 wire rx_beat_slot;
 wire [1:0]rx_phase;
 wire rx_frame_slot;
 wire [4:0]channel_tx_slot;
 wire [9:0]channel_tx_kind;
 wire [49:0]channel_tx_seq;
 wire [4:0]channel_tx_last;
 wire [4:0]channel_rx_slot;
 wire [9:0]channel_rx_kind;
 wire [49:0]channel_rx_seq;
 wire [4:0]channel_rx_last;
 wire [4:0]channel_tx_beat_slot;
 wire [4:0]channel_tx_frame_slot;
 wire [9:0]channel_tx_phase;
 wire [4:0]channel_rx_beat_slot;
 wire [4:0]channel_rx_frame_slot;
 wire [9:0]channel_rx_phase;
 wire hc_reduce_slot;
 wire hc_write_slot;
 wire [3:0]hc_word_index;
 wire [15:0]hc_expect_seq;
 wire hc_expect_last;
 wire hc_emit_slot;
 wire [31:0]hc_emit_tag;
 wire commit_gather;
 wire raw_capture_payload_slot;
 wire raw_capture_meta_slot;
 wire raw_rx_write_slot;
 wire [13:0]raw_rx_payload_row;
 wire [13:0]raw_rx_meta_row;
 wire [7:0]raw_rx_tag;
 wire hc_assemble_slot;
 wire[1:0]controller_status;wire busy;wire transport_fault,channel_fault,raw_fault,reduce_fault,assemble_fault;
 reg boundary_fault;
 wire datapath_fault=transport_fault|channel_fault|raw_fault|reduce_fault|assemble_fault|boundary_fault;
 s81_static_calendar_controller #(.ROM_FILE(ROM_FILE),.CYCLES(CYCLES)) calendar(
 .clk(ck_control),.rst_n(rst_n),.c_cmd(c_cmd),.c_done(c_done),.c_st(controller_status),
 .datapath_fault(datapath_fault),.busy(busy),
 .read_slot(read_slot),
 .read_row(read_row),
 .issue_slot(issue_slot),
 .tag(tag),
 .seq(seq),
 .last(last),
 .rankmask(rankmask),
 .commit_slot(commit_slot),
 .commit_tag(commit_tag),
 .commit_seq(commit_seq),
 .commit_last(commit_last),
 .commit_rankmask(commit_rankmask),
 .commit_rows(commit_rows),
 .tx_beat_slot(tx_beat_slot),
 .tx_phase(tx_phase),
 .tx_frame_slot(tx_frame_slot),
 .rx_beat_slot(rx_beat_slot),
 .rx_phase(rx_phase),
 .rx_frame_slot(rx_frame_slot),
 .channel_tx_slot(channel_tx_slot),
 .channel_tx_kind(channel_tx_kind),
 .channel_tx_seq(channel_tx_seq),
 .channel_tx_last(channel_tx_last),
 .channel_rx_slot(channel_rx_slot),
 .channel_rx_kind(channel_rx_kind),
 .channel_rx_seq(channel_rx_seq),
 .channel_rx_last(channel_rx_last),
 .channel_tx_beat_slot(channel_tx_beat_slot),
 .channel_tx_frame_slot(channel_tx_frame_slot),
 .channel_tx_phase(channel_tx_phase),
 .channel_rx_beat_slot(channel_rx_beat_slot),
 .channel_rx_frame_slot(channel_rx_frame_slot),
 .channel_rx_phase(channel_rx_phase),
 .hc_reduce_slot(hc_reduce_slot),
 .hc_write_slot(hc_write_slot),
 .hc_word_index(hc_word_index),
 .hc_expect_seq(hc_expect_seq),
 .hc_expect_last(hc_expect_last),
 .hc_emit_slot(hc_emit_slot),
 .hc_emit_tag(hc_emit_tag),
 .commit_gather(commit_gather),
 .raw_capture_payload_slot(raw_capture_payload_slot),
 .raw_capture_meta_slot(raw_capture_meta_slot),
 .raw_rx_write_slot(raw_rx_write_slot),
 .raw_rx_payload_row(raw_rx_payload_row),
 .raw_rx_meta_row(raw_rx_meta_row),
 .raw_rx_tag(raw_rx_tag),
 .hc_assemble_slot(hc_assemble_slot));
 // The controller's status is already pin registered. Faults are collected at
 // this boundary so c_st also has a final output register.
 reg[1:0]status_q;
 always @(posedge ck_control or negedge rst_n)
  if(!rst_n)status_q<=0;else status_q<={controller_status[1],controller_status[0]|datapath_fault};
 assign c_st=status_q;
 wire[3:0]gather_we;wire[59:0]gather_rows;wire[2047:0]gather_data;
 wire[31:0]gather_tag;wire[15:0]gather_seq;wire gather_last;
 wire raw_capture=raw_capture_payload_slot|raw_capture_meta_slot;
 s81_static_fmt1_rank_dynamic_clocked tp4(
 .rank(f_rank),.clk_core(ck_control),.clk_lane(ck_lane[2:0]),.rst_n(rst_n),
 .issue_slot(issue_slot),.src_valid(f_crs[0]&&!raw_capture),.src_data(f_crs[512:1]),
 .tag(tag),.seq(seq),.last(last),.rankmask(rankmask),
 .commit_slot(commit_slot),.commit_tag(commit_tag),.commit_seq(commit_seq),
 .commit_last(commit_last),.commit_rankmask(commit_rankmask),.commit_rows(commit_rows),
 .tx_beat_slot(tx_beat_slot),.tx_phase(tx_phase),.tx_frame_slot(tx_frame_slot),
 .rx_beat_slot(rx_beat_slot),.rx_phase(rx_phase),.rx_frame_slot(rx_frame_slot),
 .phy_tx_valid(phy_tx_valid[2:0]),.phy_tx_data(phy_tx_data[1535:0]),
 .phy_rx_valid(phy_rx_valid[2:0]),.phy_rx_data(phy_rx_data[1535:0]),
 .vm_we(gather_we),.vm_rows(gather_rows),.vm_data(gather_data),
 .gather_tag(gather_tag),.gather_seq(gather_seq),.gather_last(gather_last),.fault(transport_fault));
 reg gather_mode_q;reg[13:0]reduce_row[0:17];integer p;
 always @(posedge ck_control)begin
  gather_mode_q<=commit_gather;reduce_row[0]<=gather_rows[13:0];
  for(p=1;p<18;p=p+1)reduce_row[p]<=reduce_row[p-1];
 end
 wire reduced_valid,reduced_last,reduced_error;
 wire[511:0]reduced_data;wire[31:0]reduced_tag;wire[15:0]reduced_seq;
 s81_static_hc_reduce_clocked reduce(
 .clk_lane(ck_hc_lane),.clk_control(ck_control),.rst_n(rst_n),.slot(hc_reduce_slot),
 .rank_valid(gather_we&{4{hc_reduce_slot}}),.rank_data(gather_data),
 .tag(gather_tag),.seq(gather_seq),.last(gather_last),
 .word_valid(reduced_valid),.word_data(reduced_data),.word_tag(reduced_tag),
 .word_seq(reduced_seq),.word_last(reduced_last),.word_error(reduced_error),.fault(reduce_fault));
 wire[31:0]row_tag;
 s81_static_hc_assemble_clocked assemble(
 .clk_lane(ck_hc_lane),.clk_control(ck_control),.rst_n(rst_n),.write_slot(hc_assemble_slot),
 .word_index(hc_word_index),.word_valid(reduced_valid&&hc_assemble_slot),
 .word_data(reduced_data),.word_tag(reduced_tag),.word_error(reduced_error),
 .emit_slot(hc_emit_slot),.emit_tag(hc_emit_tag),.row_valid(t_hc_yv),
 .row_data(t_hc_y),.row_tag(row_tag),.fault(assemble_fault));
 wire raw_send;reg raw_send_q;reg[2:0]raw_channel;reg raw_last;
 integer c;reg[2:0]raw_tx_count;
 always @*begin
  raw_send_q=0;raw_channel=0;raw_last=0;raw_tx_count=0;
  for(integer j=0;j<5;j=j+1)if(channel_tx_slot[j]&&channel_tx_kind[j*2+:2]==0)begin
   raw_send_q=1;raw_channel=3'(j);raw_last=channel_tx_last[j];raw_tx_count=raw_tx_count+1;
  end
 end
 assign raw_send=raw_send_q;
 wire vm_tx_valid,vm_tx_last,vm_rx_valid,vm_rx_last;
 wire[2:0]vm_tx_channel,vm_rx_channel;
 wire[551:0]vm_tx_payload,vm_rx_payload;
 wire[1101:0]raw_sources;
 s81_static_raw_vm_rows #(.REGISTER_VM_WRITES(0)) raw_rows(
 .clk(ck_control),.rst_n(rst_n),.capture_payload_slot(raw_capture_payload_slot),
 .capture_meta_slot(raw_capture_meta_slot),.f_crs({f_crs[512:1],f_crs[0]&&raw_capture}),
 .send_slot(raw_send),.send_last(raw_last),.send_channel(raw_channel),
 .vm_tx_valid(vm_tx_valid),.vm_tx_last(vm_tx_last),.vm_tx_channel(vm_tx_channel),.vm_tx_payload(vm_tx_payload),
 .rx_slot(raw_rx_write_slot),.rx_valid(vm_rx_valid),.rx_last(vm_rx_last),.rx_payload(vm_rx_payload),
 .rx_payload_row(raw_rx_payload_row),.rx_meta_row(raw_rx_meta_row),.rx_tag(raw_rx_tag),
 .vm_write_sources(raw_sources),.fault(raw_fault));
 wire[515:0]host_rx;
 s81_static_fmt1_channels_clocked channels(
 .clk_adapter(ck_control),.clk_lane(ck_lane[7:3]),.rst_n(rst_n),
 .tx_slot(channel_tx_slot),.rx_slot(channel_rx_slot),.tx_kind(channel_tx_kind),.rx_kind(channel_rx_kind),
 .vm_tx_last(vm_tx_last),.vm_tx_valid(vm_tx_valid),.vm_tx_channel(vm_tx_channel),.vm_tx_payload(vm_tx_payload),
 .wfc_tx(f_wfc),.host_tx_valid(f_host[76]),.host_status(f_host[75:65]),.host_completion(f_host[64:0]),
 .vm_rx_last(vm_rx_last),.vm_rx_valid(vm_rx_valid),.vm_rx_channel(vm_rx_channel),.vm_rx_payload(vm_rx_payload),
 .wfc_rx(t_wfc),.host_rx(host_rx),.tx_seq(channel_tx_seq),
 .rx_expected_seq(channel_rx_seq),.rx_expected_last(channel_rx_last),
 .tx_beat_slot(channel_tx_beat_slot),.tx_frame_slot(channel_tx_frame_slot),.tx_phase(channel_tx_phase),
 .rx_beat_slot(channel_rx_beat_slot),.rx_frame_slot(channel_rx_frame_slot),.rx_phase(channel_rx_phase),
 .phy_tx_valid(phy_tx_valid[7:3]),.phy_tx_data(phy_tx_data[4095:1536]),
 .phy_rx_valid(phy_rx_valid[7:3]),.phy_rx_data(phy_rx_data[4095:1536]),.fault(channel_fault));
 // Native host ingress omits the historical credit bit. Its wire reservation
 // remains zero; accepting a nonzero bit would silently restore flow control.
 assign t_host=host_rx[514:0];
 reg[2203:0]next_vm;reg pack_bad;reg[3:0]occupied;
 reg[550:0]word;integer k;
 always @*begin
  next_vm=0;pack_bad=0;occupied=0;word=0;
  if(|gather_we)begin
   if(gather_mode_q)begin
    for(integer j=0;j<4;j=j+1)if(gather_we[j])begin
     if(gather_rows[j*15+14])pack_bad=1;
     next_vm[j*551+:551]={gather_tag[7:0],gather_data[j*512+:512],16'hffff,gather_rows[j*15+:14],1'b1};occupied[j]=1;
    end
   end else if(!hc_reduce_slot)pack_bad=1;
  end
  if(hc_write_slot)begin
   if(occupied[0]||!reduced_valid||reduced_error||reduced_seq!=hc_expect_seq||reduced_last!=hc_expect_last)pack_bad=1;
   next_vm[0+:551]={reduced_tag[7:0],reduced_data,16'hffff,reduce_row[17],1'b1};occupied[0]=1;
  end
  if(reduced_valid!=hc_write_slot)pack_bad=1;
  for(integer j=0;j<2;j=j+1)begin
   word=raw_sources[j*551+:551];
   if(word[0])begin if(occupied[j])pack_bad=1;next_vm[j*551+:551]=word;occupied[j]=1;end
  end
  if(pack_bad||boundary_fault)for(integer j=0;j<4;j=j+1)next_vm[j*551]=0;
 end
 always @(posedge ck_control or negedge rst_n)begin
  if(!rst_n)begin t_crq<=0;t_vm<=0;boundary_fault<=0;end
  else begin
   t_crq<={read_row,read_slot};t_vm<=next_vm;
   if(pack_bad||(|phy_rx_fault)||(issue_slot&&raw_capture)||
      (raw_capture_payload_slot&&raw_capture_meta_slot)||raw_tx_count>1||
      (host_rx[0]&&host_rx[515]))boundary_fault<=1;
   for(integer j=0;j<8;j=j+1)if(phy_rx_valid[j]&&!phy_rx_live[j])boundary_fault<=1;
  end
 end
endmodule
