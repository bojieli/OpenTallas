`timescale 1ns/1ps
`default_nettype none
// One eight-FP32-lane head batch. Boundary inputs are block partials; all
// subsequent arithmetic, transit, landing and local-tree feedback is RTL.
// The compiler reserves each edge. This component is not physical signoff.
module ot_hgi_attn_pv_native #(
 parameter integer MUT_CARRY=0,MUT_TAG=0,MUT_SCRATCH=0
)(
 input wire clk,rst_n,
 input ot_hgi_attn_pv_pkg::ring_cmd_t cmd[0:3],
 input wire [255:0] boundary_data[0:3],
 input wire [1:0] dest_q,
 input wire [3:0] landing_slot,
 input ot_hgi_attn_pv_pkg::local_cmd_t local_cmd,
 // Single-node mode is the declared DS128 boundary and needs no addition.
 input wire single_v,input wire [255:0] single_data,
 output wire out_v,output wire [255:0] out_data,
 output wire [3:0] ring_fault,output wire local_fault,
 output reg scratch_fault,
 output wire [3:0] ring_rr_v
);
 wire [279:0] co[0:3],no[0:3];
 wire [3:0] rr_v,fault;
 wire [2:0] rr_tag[0:3];wire [255:0] rr_data[0:3];
 assign ring_fault=fault;assign ring_rr_v=rr_v;
    for(genvar q=0;q<4;q=q+1)begin:g_q
        ot_hgi_coll_pring_static #(.SPLIT_CLOCKS(1),.MUT_CARRY(MUT_CARRY),.MUT_TAG(MUT_TAG)) dut(
            .clk(clk),.rst_n(rst_n),.clk_state({8{clk}}),.clk_add({8{clk}}),.qid(2'(q)),.cw_i(co[((q==0)?2:(q==1)?0:(q==3)?1:3)]),.ccw_i(no[((q==0)?1:(q==1)?3:(q==3)?2:0)]),.cw_o(co[q]),.ccw_o(no[q]),
            .lp_we(cmd[q].lp_we),.lp_tag(cmd[q].lp_tag),.lp_data(boundary_data[q]),
            .state_read_add(cmd[q].read_add),.state_read_tx(cmd[q].read_tx),.state_read_rr(cmd[q].read_rr),
            .state_add_tag(cmd[q].read_add_tag),.state_add_src(cmd[q].read_add_src),.state_add_rhs_acc(cmd[q].read_rhs_acc),
            .state_tx_tag(cmd[q].read_tx_tag),.state_tx_acc(cmd[q].read_tx_acc),.state_rr_tag(cmd[q].read_rr_tag),
            .add_v(cmd[q].add_v),.add_tag(cmd[q].add_tag),.add_src(cmd[q].add_src),.add_rhs_acc(cmd[q].rhs_acc),
            .tx_inject(cmd[q].inject),.tx_forward(cmd[q].fwd),.tx_tag(cmd[q].tx_tag),.tx_dst(cmd[q].dst),
            .tx_result(cmd[q].result),.tx_acc(cmd[q].acc),.rx_slot(cmd[q].rx),.rx_kind(cmd[q].kind),.rx_src(cmd[q].src),.rx_tag(cmd[q].tag),
            .rr_local(cmd[q].rr),.rr_local_tag(cmd[q].rr_tag),.rr_v(rr_v[q]),.rr_tag(rr_tag[q]),.rr_d(rr_data[q]),.fault(fault[q]));
    end

 reg [255:0] scratch[0:15];
 reg [15:0] scratch_valid;
 wire [544:0] reduce_out;
 wire [7:0] fault_cause;
 reg [255:0] scratch_operand;
 wire [544:0] operand={289'b0,scratch_operand};
 ot_hgi_coll_reduce_static reducer(
  .clk_control(clk),.clk_state({16{clk}}),.clk_add({16{clk}}),
  .rst_n(rst_n),.clear(local_cmd.clear),
  .in_v(local_cmd.load_v|local_cmd.add_read),.in_flit(operand),
  .load_v(local_cmd.load_v),.load_tag(4'd0),
  .add_read(local_cmd.add_read),.read_tag(4'd0),.add_issue(local_cmd.add_issue),
  .pub_read(local_cmd.pub_read),.pub_tag_a(4'd0),.pub_tag_b(4'd0),
  .pub_bf16(1'b0),.pub_meta(33'd0),.pub_release(1'b1),.pub_issue(local_cmd.pub_issue),
  .out_v(out_v),.out_flit(reduce_out),.fault(local_fault),.fault_cause(fault_cause));
 assign out_data=reduce_out[255:0];
 // Ring rr and reducer out are registered faces. Captures occur one edge
 // after their publication; no testbench reads or copies intermediate data.
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin scratch_valid<=0;scratch_fault<=0;end
  else begin
   if(local_cmd.clear)scratch_valid<=0;
   if(rr_v[dest_q])begin
    if(scratch_valid[landing_slot])scratch_fault<=1;
    scratch[landing_slot]<=rr_data[dest_q];scratch_valid[landing_slot]<=1;
   end
   if(single_v)begin
    if(scratch_valid[0]||rr_v[dest_q])scratch_fault<=1;
    scratch[0]<=single_data;scratch_valid[0]<=1;
   end
   if(local_cmd.scratch_read_v)begin
    if(!scratch_valid[local_cmd.scratch_read])scratch_fault<=1;
    scratch_operand<=scratch[local_cmd.scratch_read];
   end
   if(local_cmd.capture)begin
    if(!out_v||rr_v[dest_q]||single_v)scratch_fault<=1;
    scratch[local_cmd.capture_slot ^ (MUT_SCRATCH?4'd1:4'd0)]<=out_data;
    scratch_valid[local_cmd.capture_slot ^ (MUT_SCRATCH?4'd1:4'd0)]<=1;
   end
  end
 end
endmodule
`default_nettype wire
