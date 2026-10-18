`default_nettype none
// ELEM-GAPS/HBMB 2026-10-18: ot_hbm_svc_fault_cdc with DOMAIN-SYNCHRONISED resets (the hardened svg master).
// ot_hbm_svc_fault_cdc resets its source flops (pending/sent, wr_clk) and its destination sticky (rd_clk) directly
// from both_reset = wr_rst_n && rd_rst_n, so the OTHER family's reset releases them asynchronously (a cross-family
// asynchronous control path: refused by tools/ref_tile reviewed_gray_fifos, an RDC hazard on release).  Here
// both_reset enters one ot_reset_sync per family (async assert, synchronous release in the flop's own clock); the
// token path is the same reviewed ot_hbm_svc_async_fifo.  Function is unchanged (a sticky fault crosses once, reset of
// either side flushes it); release of pending/sent/sticky is 2 edges later in their own clock.  Same ports as
// ot_hbm_svc_fault_cdc (MUT 0 only).
module ot_hbm_svc_fault_cdc_rs (
 input wire wr_clk,wr_rst_n,rd_clk,rd_rst_n,input wire src_fault,
 output wire dst_fault,output wire wr_overflow,rd_underflow
);
 wire both_reset=wr_rst_n&&rd_rst_n;
 wire src_reset,dst_reset;
 ot_reset_sync u_src_reset(.clk(wr_clk),.async_rst_n(both_reset),.sync_rst_n(src_reset));
 ot_reset_sync u_dst_reset(.clk(rd_clk),.async_rst_n(both_reset),.sync_rst_n(dst_reset));
 reg pending,sent;
 wire ready,valid;wire[0:0]data;
 wire offer=pending&&!sent&&ready;
 always @(posedge wr_clk or negedge src_reset)begin
  if(!src_reset)begin pending<=0;sent<=0;end
  else begin
   if(src_fault)pending<=1;
   if(pending&&!sent&&ready)sent<=1;
  end
 end
 ot_hbm_svc_async_fifo #(.WIDTH(1),.DEPTH(4)) u_status(
  .wr_clk(wr_clk),.wr_rst_n(wr_rst_n),.wr_valid(offer),.wr_ready(ready),.wr_data(1'b1),.wr_overflow(wr_overflow),
  .rd_clk(rd_clk),.rd_rst_n(rd_rst_n),.rd_valid(valid),.rd_ready(valid),.rd_data(data),.rd_underflow(rd_underflow));
 reg sticky;
 always @(posedge rd_clk or negedge dst_reset)begin
  if(!dst_reset)sticky<=0;
  else if(valid&&data[0])sticky<=1;
 end
 assign dst_fault=sticky;
endmodule
`default_nettype wire
