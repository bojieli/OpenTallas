`timescale 1ns/1ps
// Proposed own-flop native output leaf: packer and lossless two-flit encoder
// share one delivered root. Their ready connection is internal to this root;
// the actual native control input is captured by the credit receiver.
// The die contract for index62 grants/reservations/ACK remains PROPOSED.
module ot_hfd_tkm_native_output_leaf # (parameter integer MUT=0)(
 input wire clk,rst_n,start,
 input wire[12:0]cfg_nout,input wire[39:0]cfg_obase,cfg_rbase,input wire cfg_has_r,
 input wire cell_v,input wire[339:0]cell_t,input wire[1:0]cell_slot,input wire cell_last,
 input wire[39:0]native_control,
 input wire core_done,core_busy,core_fault,
 output wire[544:0]native_write,
 output reg done,busy,fault,
 output wire[3:0]queued,output wire[9:0]lines_pushed,output wire pack_empty
);
 wire[0:0]rr;
 ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1))u_rr(.clk(clk),.rst_n_in(rst_n),.rst_n(rr));
 reg done_pin,busy_pin,fault_pin;
 always @(posedge clk)begin done_pin<=core_done;busy_pin<=core_busy;fault_pin<=core_fault;end
 wire codec_done,codec_busy,codec_fault;
 always @(posedge clk or negedge rr[0])
  if(!rr[0])begin done<=0;busy<=0;fault<=0;end
  else begin done<=codec_done;busy<=codec_busy;fault<=codec_fault;end
 wire wv,wr;wire[39:0]wa;wire[15:0]wm;wire[511:0]wd;
 wire[15:0]pending;wire[4:0]leases;
 ot_hgi_coll_tkm_packer #(.MUT(MUT))u_pack(.clk(clk),.rst_n(rst_n),.start(start),
  .cfg_nout(cfg_nout),.cfg_obase(cfg_obase),.cfg_rbase(cfg_rbase),.cfg_has_r(cfg_has_r),
  .cell_v(cell_v),.cell_t(cell_t),.cell_slot(cell_slot),.cell_last(cell_last),
  .w_rdy(wr),.w_ack(1'b0),.w_seq(),.w_v(wv),.w_addr(wa),.w_mask(wm),.w_data(wd),
  .queued(queued),.lines_pushed(lines_pushed),.empty(pack_empty));
 ot_hfd_tkm_write_credit_tx u_codec(.clk(clk),.rst_n(rr[0]),.control(native_control),
  .w_v(wv),.w_addr(wa),.w_mask(wm),.w_data(wd),.w_rdy(wr),.packet(native_write),
  .core_done(done_pin),.core_busy(busy_pin),.core_fault(fault_pin),.done(codec_done),.busy(codec_busy),.fault(codec_fault),
  .outstanding(pending),.leases(leases));
endmodule
