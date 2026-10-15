`timescale 1ns/1ps
// Real static S81 collective datapath composition, native candidate.
// ck_control[0..4] = sequencer/ROM, TP4 core, VM boundary, pass adapter, HC metadata.
// Clocks are delivered pins from the die PLL tree; no common-pin phase waiver.
// Configuration ROM/memory macro and production placement/phase/image are open
// qualification gates. Missing ROM fails closed, never fabricates a schedule.
module s81_static_collective_slab #(
 parameter ROM_FILE="",parameter integer CYCLES=1,parameter integer MUT=0,parameter integer VMB_PINCAP=1
)(
 input wire[4:0]ck_control,input wire[7:0]ck_lane,input wire[15:0]ck_hc_lane,
 input wire rst_n,input wire[1:0]f_rank,
 input wire[84:0]c_cmd,output wire[8:0]c_done,output wire[1:0]c_st,
 output wire[14:0]t_crq,input wire[512:0]f_crs,output wire[2203:0]t_vm,
 input wire[7:0]phy_rx_valid,input wire[4095:0]phy_rx_data,
 input wire[7:0]phy_rx_fault,input wire[7:0]phy_rx_live,
 output wire[7:0]phy_tx_valid,output wire[4095:0]phy_tx_data,
 input wire[513:0]f_wfc,output wire[513:0]t_wfc,
 input wire[76:0]f_host,output wire[514:0]t_host,
 output wire[8191:0]t_hc_y,output wire t_hc_yv,output wire[31:0]t_hc_tag
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
 wire[4:0]rn_control;
 genvar root;
 generate for(root=0;root<5;root=root+1)begin:reset_root
  reg[1:0]rr;
  always @(posedge ck_control[root] or negedge rst_n)
   if(!rst_n)rr<=0;else rr<={rr[0],1'b1};
  assign rn_control[root]=rr[1];
 end endgenerate
 wire[1:0]controller_status;wire busy;wire transport_fault,channel_fault,raw_fault,reduce_fault,assemble_fault,host_queue_fault;
 wire boundary_fault;
 wire pack_bad;
 wire datapath_fault=transport_fault|channel_fault|raw_fault|reduce_fault|assemble_fault|boundary_fault|host_queue_fault;
 s81_static_calendar_controller #(.ROM_FILE(ROM_FILE),.CYCLES(CYCLES)) calendar(
 .clk(ck_control[0]),.rst_n(rn_control[0]),.c_cmd(c_cmd),.c_done(c_done),.c_st(controller_status),
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
 always @(posedge ck_control[2] or negedge rn_control[2])
  if(!rn_control[2])status_q<=0;else status_q<={controller_status[1],controller_status[0]|datapath_fault};
 assign c_st=status_q;
 wire[3:0]gather_we;wire[59:0]gather_rows;wire[2047:0]gather_data;
 wire[31:0]gather_tag;wire[15:0]gather_seq;wire gather_last;
 wire raw_capture=raw_capture_payload_slot|raw_capture_meta_slot;
 s81_static_fmt1_rank_dynamic_clocked #(.LOCAL_RESET_SYNC(1)) tp4(
 .rank(f_rank),.clk_core(ck_control[1]),.clk_lane(ck_lane[2:0]),.rst_n(rn_control[1]),
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
 wire reduced_valid,reduced_last,reduced_error;
 wire[511:0]reduced_data;wire[31:0]reduced_tag;wire[15:0]reduced_seq;
 s81_static_hc_reduce_clocked #(.LOCAL_RESET_SYNC(1)) reduce(
 .clk_lane(ck_hc_lane),.clk_control(ck_control[4]),.rst_n(rn_control[4]),.slot(hc_reduce_slot),
 .rank_valid(gather_we&{4{hc_reduce_slot}}),.rank_data(gather_data),
 .tag(gather_tag),.seq(gather_seq),.last(gather_last),
 .word_valid(reduced_valid),.word_data(reduced_data),.word_tag(reduced_tag),
 .word_seq(reduced_seq),.word_last(reduced_last),.word_error(reduced_error),.fault(reduce_fault));
 wire[31:0]row_tag;
 assign t_hc_tag=row_tag;
 s81_static_hc_assemble_clocked assemble(
 .clk_lane(ck_hc_lane),.clk_control(ck_control[4]),.rst_n(rn_control[4]),.write_slot(hc_assemble_slot),
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
 .clk(ck_control[2]),.rst_n(rn_control[2]),.capture_payload_slot(raw_capture_payload_slot),
 .capture_meta_slot(raw_capture_meta_slot),.f_crs({f_crs[512:1],f_crs[0]&&raw_capture}),
 .send_slot(raw_send),.send_last(raw_last),.send_channel(raw_channel),
 .vm_tx_valid(vm_tx_valid),.vm_tx_last(vm_tx_last),.vm_tx_channel(vm_tx_channel),.vm_tx_payload(vm_tx_payload),
 .rx_slot(raw_rx_write_slot),.rx_valid(vm_rx_valid),.rx_last(vm_rx_last),.rx_payload(vm_rx_payload),
 .rx_payload_row(raw_rx_payload_row),.rx_meta_row(raw_rx_meta_row),.rx_tag(raw_rx_tag),
 .vm_write_sources(raw_sources),.fault(raw_fault));
 wire[515:0]host_rx;
 // S-BIND r6 2026-10-15: static host face. The host's completions are single-edge pulses; this queue (adapter clock,
 // where the channel samples the host word) holds them for the compiled host tx slot. No credit, no ready.
 reg host_slot;
 always @* begin host_slot=1'b0; for(integer h=0;h<5;h=h+1)if(channel_tx_slot[h]&&channel_tx_kind[h*2+:2]==2'd2)host_slot=1'b1; end
 wire host_tx_valid_q;wire[10:0]host_status_q;wire[64:0]host_completion_q;
 s81_static_host_queue #(.DEPTH(16),.MUT(MUT)) host_queue(.clk(ck_control[3]),.rst_n(rn_control[3]),.f_host(f_host),
  .slot(host_slot),.host_tx_valid(host_tx_valid_q),.host_status(host_status_q),.host_completion(host_completion_q),
  .fault(host_queue_fault));
 s81_static_fmt1_channels_clocked #(.LOCAL_RESET_SYNC(1)) channels(
 .clk_adapter(ck_control[3]),.clk_lane(ck_lane[7:3]),.rst_n(rn_control[3]),
 .tx_slot(channel_tx_slot),.rx_slot(channel_rx_slot),.tx_kind(channel_tx_kind),.rx_kind(channel_rx_kind),
 .vm_tx_last(vm_tx_last),.vm_tx_valid(vm_tx_valid),.vm_tx_channel(vm_tx_channel),.vm_tx_payload(vm_tx_payload),
 .wfc_tx(f_wfc),.host_tx_valid(host_tx_valid_q),.host_status(host_status_q),.host_completion(host_completion_q),
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
 // VMB_PINCAP=1: native boundary leaf (write path pin-captured, collective->VM write +1 fixed edge; reads unchanged)
 s81_static_vm_boundary #(.MUT(MUT),.PINCAP(VMB_PINCAP)) vm_boundary(
 .clk(ck_control[2]),.rst_n(rn_control[2]),.read_slot(read_slot),.read_row(read_row),.t_crq(t_crq),.t_vm(t_vm),
 .commit_gather(commit_gather),.hc_reduce_slot(hc_reduce_slot),.gather_we(gather_we),.gather_rows(gather_rows),.gather_data(gather_data),.gather_tag(gather_tag),
 .hc_write_slot(hc_write_slot),.reduced_valid(reduced_valid),.reduced_error(reduced_error),.reduced_last(reduced_last),.reduced_seq(reduced_seq),
 .hc_expect_seq(hc_expect_seq),.hc_expect_last(hc_expect_last),.reduced_data(reduced_data),.reduced_tag(reduced_tag),.raw_sources(raw_sources),
 .phy_rx_fault(phy_rx_fault),.phy_rx_valid(phy_rx_valid),.phy_rx_live(phy_rx_live),.issue_slot(issue_slot),.raw_capture(raw_capture),
 .raw_capture_payload_slot(raw_capture_payload_slot),.raw_capture_meta_slot(raw_capture_meta_slot),.raw_tx_count(raw_tx_count),.host_rx(host_rx),
 .pack_bad_out(pack_bad),.fault(boundary_fault));

endmodule
