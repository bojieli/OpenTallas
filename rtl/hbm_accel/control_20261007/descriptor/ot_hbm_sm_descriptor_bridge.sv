// Opt-in finite native descriptor bridge. Source ready is a returned CONSUMED
// acknowledgement. It is deliberately not the channel's reservation credit.
// Model: tools/hbm_sm_descriptor_bridge_model.py; HOPS provisional until routed.
module ot_hbm_sm_descriptor_bridge #(parameter ENABLE=0,HOPS=32,DEPTH=2)(
 input wire clk,rst_n,
 input wire s_valid,output wire s_ready,input wire[31:0] s_base,input wire[23:0] s_lines,
 output wire d_valid,input wire d_ready,output wire[31:0] d_base,output wire[23:0] d_lines,
 input wire south_fault,output wire north_fault,output wire fault
);
 reg pending,pending_n,abort_latched;
 wire a_ready,b_ready,a_valid,b_valid;
 wire[55:0] a_data,b_data;
 wire a_ack,b_ack,a_fault,b_fault;
 wire mismatch=(pending==pending_n) || (a_ready!=b_ready) || (a_valid!=b_valid) ||
   (a_valid && a_data!=b_data) || (a_ack!=b_ack) || (a_fault!=b_fault);
 wire blocked=abort_latched || mismatch;
 wire send=ENABLE && s_valid && !pending && a_ready && b_ready && !blocked;
 wire consume=d_valid && d_ready;
 assign s_ready=ENABLE && pending && a_ack && b_ack && !blocked;
 assign d_valid=ENABLE && a_valid && b_valid && !blocked;
 assign {d_base,d_lines}=a_data;
 assign fault=blocked;
 assign north_fault=blocked || a_fault || b_fault;
 (* keep=1,keep_hierarchy=1 *) ot_hbm_accel_smv_chan #(.W(56),.P(HOPS),.DEPTH(DEPTH)) a(
  .clk(clk),.rst_n(rst_n),.s_valid(send),.s_ready(a_ready),.s_data({s_base,s_lines}),
  .m_valid(a_valid),.m_ready(d_ready && !blocked),.m_data(a_data));
 (* keep=1,keep_hierarchy=1 *) ot_hbm_accel_smv_chan #(.W(56),.P(HOPS),.DEPTH(DEPTH)) b(
  .clk(clk),.rst_n(rst_n),.s_valid(send),.s_ready(b_ready),.s_data({s_base,s_lines}),
  .m_valid(b_valid),.m_ready(d_ready && !blocked),.m_data(b_data));
 (* keep=1,keep_hierarchy=1 *) ot_hbm_accel_smv_chain #(.W(1),.D(HOPS),.RST(1)) ack_a(.clk(clk),.rst_n(rst_n),.d(consume),.q(a_ack));
 (* keep=1,keep_hierarchy=1 *) ot_hbm_accel_smv_chain #(.W(1),.D(HOPS),.RST(1)) ack_b(.clk(clk),.rst_n(rst_n),.d(consume),.q(b_ack));
 (* keep=1,keep_hierarchy=1 *) ot_hbm_accel_smv_chain #(.W(1),.D(HOPS),.RST(1)) fault_a(.clk(clk),.rst_n(rst_n),.d(south_fault),.q(a_fault));
 (* keep=1,keep_hierarchy=1 *) ot_hbm_accel_smv_chain #(.W(1),.D(HOPS),.RST(1)) fault_b(.clk(clk),.rst_n(rst_n),.d(south_fault),.q(b_fault));
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin pending<=0;pending_n<=1;abort_latched<=0;end
  else if(ENABLE)begin
   if(send)begin pending<=1;pending_n<=0;end
   if(s_ready)begin pending<=0;pending_n<=1;end
   if(mismatch || (a_ack && !pending))abort_latched<=1;
  end
 end
endmodule
