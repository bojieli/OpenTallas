`timescale 1ns/1ps
`default_nettype none
// Pipelined component successor: eight actual ring tags and sixteen actual
// reducer tags, plus two physical SRAM functional models. Compiler reserves
// every memory and arithmetic edge. Boundary inputs are canonical128-row SM
// subtree nodes; native SM production, physical views and price remain separate.
module ot_hgi_attn_pv_stream #(
 parameter integer MUT_CARRY=0,MUT_BANK=0
)(
 input wire clk,rst_n,
 input ot_hgi_attn_pv_pkg::ring_cmd_t cmd[0:3],
 input wire [255:0] boundary_data[0:3],
 input wire [1:0] dest_q,
 input wire [4:0] landing_slot,
 input ot_hgi_attn_pv_stream_pkg::stream_cmd_t local_cmd,
 output wire final_v,
 output wire [255:0] out_data,
 output reg [6:0] out_batch,
 output reg [1:0] out_destination,
 output wire [3:0] ring_fault,
 output wire local_fault,
 output reg scratch_fault
);
 wire [279:0] cw[0:3],ccw[0:3];
 wire [3:0] rr_v;
 wire [255:0] rr_data[0:3];
 for(genvar q=0;q<4;q=q+1)begin:g_q
  wire [2:0] unused_tag;
  ot_hgi_coll_pring_static #(.SPLIT_CLOCKS(1),.MUT_CARRY(MUT_CARRY)) ring(
   .clk(clk),.rst_n(rst_n),.clk_state({8{clk}}),.clk_add({8{clk}}),.qid(2'(q)),
   .cw_i(cw[(q==0)?2:(q==1)?0:(q==3)?1:3]),
   .ccw_i(ccw[(q==0)?1:(q==1)?3:(q==3)?2:0]),.cw_o(cw[q]),.ccw_o(ccw[q]),
   .lp_we(cmd[q].lp_we),.lp_tag(cmd[q].lp_tag),.lp_data(boundary_data[q]),
   .state_read_add(cmd[q].read_add),.state_read_tx(cmd[q].read_tx),.state_read_rr(cmd[q].read_rr),
   .state_add_tag(cmd[q].read_add_tag),.state_add_src(cmd[q].read_add_src),.state_add_rhs_acc(cmd[q].read_rhs_acc),
   .state_tx_tag(cmd[q].read_tx_tag),.state_tx_acc(cmd[q].read_tx_acc),.state_rr_tag(cmd[q].read_rr_tag),
   .add_v(cmd[q].add_v),.add_tag(cmd[q].add_tag),.add_src(cmd[q].add_src),.add_rhs_acc(cmd[q].rhs_acc),
   .tx_inject(cmd[q].inject),.tx_forward(cmd[q].fwd),.tx_tag(cmd[q].tx_tag),.tx_dst(cmd[q].dst),
   .tx_result(cmd[q].result),.tx_acc(cmd[q].acc),.rx_slot(cmd[q].rx),.rx_kind(cmd[q].kind),
   .rx_src(cmd[q].src),.rx_tag(cmd[q].tag),.rr_local(cmd[q].rr),.rr_local_tag(cmd[q].rr_tag),
   .rr_v(rr_v[q]),.rr_tag(unused_tag),.rr_d(rr_data[q]),.fault(ring_fault[q]));
 end
 wire reduce_v;
 wire [544:0] reduce_out;
 wire [7:0] reduce_cause;
 wire [511:0] ram_data[0:1];
 reg read_bank;
 wire [255:0] read_data=ram_data[read_bank][255:0];
 wire ring_write=rr_v[dest_q];
 wire local_write=local_cmd.capture;
 wire [4:0] local_slot=local_cmd.capture_slot ^ (MUT_BANK?5'd16:5'd0);
 for(genvar b=0;b<2;b=b+1)begin:g_memory
  wire rw=ring_write && landing_slot[4]==b;
  wire lw=local_write && local_slot[4]==b;
  wire [5:0] address={2'b00,rw?landing_slot[3:0]:local_slot[3:0]};
  ot_sram_1r1w_64x512_m1_r2c2 storage(
   .clk(clk),.r_ce_in(local_cmd.scratch_read_v && local_cmd.scratch_read_slot[4]==b),
   .r_addr_in({2'b00,local_cmd.scratch_read_slot[3:0]}),.rd_out(ram_data[b]),
   .w_ce_in(rw|lw),.w_addr_in(address),
   .wd_in({256'b0,rw?rr_data[dest_q]:out_data}),.w_mask_in({512{1'b1}}),
   .rr_en(2'b00),.rr_addr(12'b0),.cr_en(2'b00),.cr_sel(18'b0));
 end
 ot_hgi_coll_reduce_static reducer(
  .clk_control(clk),.clk_state({16{clk}}),.clk_add({16{clk}}),.rst_n(rst_n),.clear(1'b0),
  .in_v(local_cmd.load_v|local_cmd.add_read),.in_flit({289'b0,read_data}),
  .load_v(local_cmd.load_v),.load_tag(local_cmd.load_tag),
  .add_read(local_cmd.add_read),.read_tag(local_cmd.read_tag),.add_issue(local_cmd.add_issue),
  .pub_read(local_cmd.pub_read),.pub_tag_a(local_cmd.pub_tag),.pub_tag_b(4'b0),
  .pub_bf16(1'b0),.pub_meta(33'b0),.pub_release(1'b1),.pub_issue(local_cmd.pub_issue),
  .out_v(reduce_v),.out_flit(reduce_out),.fault(local_fault),.fault_cause(reduce_cause));
 assign out_data=reduce_out[255:0];
 reg final_q;
 assign final_v=reduce_v && final_q;
 reg [31:0] valid;
 reg read_valid,read_reserved;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   valid<=0;read_valid<=0;read_reserved<=0;read_bank<=0;scratch_fault<=0;final_q<=0;out_batch<=0;out_destination<=0;
  end else begin
   final_q<=local_cmd.final_pub;
   read_reserved<=local_cmd.scratch_read_v;
   if((local_cmd.load_v|local_cmd.add_read)!=read_reserved)scratch_fault<=1;
   if(local_cmd.pub_issue)begin out_batch<=local_cmd.batch;out_destination<=local_cmd.destination;end
   if(local_cmd.clear_bank_v)valid[local_cmd.clear_bank*16+:16]<=0;
   if(local_cmd.scratch_read_v)begin
    read_bank<=local_cmd.scratch_read_slot[4];read_valid<=valid[local_cmd.scratch_read_slot];
    if(!valid[local_cmd.scratch_read_slot])scratch_fault<=1;
   end
   if((local_cmd.load_v||local_cmd.add_read) && !read_valid)scratch_fault<=1;
   if(ring_write)begin
    if(valid[landing_slot])scratch_fault<=1;
    valid[landing_slot]<=1;
   end
   if(local_write)begin
    if(!reduce_v)scratch_fault<=1;
    valid[local_slot]<=1;
   end
   if(ring_write && local_write && landing_slot[4]==local_slot[4])scratch_fault<=1;
   if(local_cmd.clear_bank_v && ((ring_write && landing_slot[4]==local_cmd.clear_bank)||
      (local_write && local_slot[4]==local_cmd.clear_bank)))scratch_fault<=1;
   if(local_cmd.final_pub && !local_cmd.pub_issue)scratch_fault<=1;
  end
 end
endmodule
`default_nettype wire
