`timescale 1ns/1ps
// Exact installed leaves, common clk/reset direct connection. No tagged ACK.
module tb_RFACK_conditional;
 reg clk=0,rst_n=0;always #5 clk=~clk;
 reg op_valid=0,cap_valid=0,producer_done_valid=0,ack_retire_enable=0,fence_ready=0;
 reg [7:0] op_epoch=1,cap_epoch=1,producer_done_epoch=1;
 reg [4095:0] cap_data={64{64'h800000007fc00001}};
 wire op_ready,cap_ready,host_wr_valid,host_wr_ready,host_ack_valid,host_ack_ready;
 wire [8:0] host_dst,vector_ACK_addr;wire [4095:0] host_wdata;
 wire vector_ACK_visible,writes_visible,fence_valid,pending_write,fault;
 wire [7:0] vector_ACK_epoch,fence_epoch;
 reg rd_valid=0,rsp_ready=0;wire rd_ready,rsp_valid;wire [4095:0] rsp_a,rsp_b;
 integer writes=0,acks=0,reads=0,cycles=0;
 ot_gpu_rf_visibility_fence #(.ENABLE(1)) fence(.clk(clk),.rst_n(rst_n),
 .op_valid(op_valid),.op_ready(op_ready),.op_epoch(op_epoch),.op_vectors(10'd1),
 .cap_valid(cap_valid),.cap_ready(cap_ready),.cap_epoch(cap_epoch),.cap_addr(9'd0),.cap_last(1'b1),.cap_data(cap_data),
 .producer_done_valid(producer_done_valid),.producer_done_epoch(producer_done_epoch),
 .host_wr_valid(host_wr_valid),.host_wr_ready(host_wr_ready),.host_dst(host_dst),.host_wdata(host_wdata),
 .host_ack_valid(host_ack_valid),.host_ack_ready(host_ack_ready),.ack_retire_enable(ack_retire_enable),
 .vector_ACK_visible(vector_ACK_visible),.vector_ACK_addr(vector_ACK_addr),.vector_ACK_epoch(vector_ACK_epoch),
 .writes_visible(writes_visible),.fence_valid(fence_valid),.fence_ready(fence_ready),.fence_epoch(fence_epoch),.pending_write(pending_write),.fault(fault));
 ot_gpu_rf_service rf(.clk(clk),.rst_n(rst_n),.rd_valid(rd_valid),.rd_ready(rd_ready),.rd_a(9'd0),.rd_b(9'd0),
 .rsp_valid(rsp_valid),.rsp_ready(rsp_ready),.rsp_a(rsp_a),.rsp_b(rsp_b),
 .wr_valid(host_wr_valid),.wr_ready(host_wr_ready),.wr_addr(host_dst),.wr_data(host_wdata),.ack_valid(host_ack_valid),.ack_ready(host_ack_ready));
 always @(posedge clk)begin
  cycles=cycles+1;
  if(rst_n)begin
   if(fault)$fatal(1,"FAIL_SOURCE_FENCE_FAULT");
   if(host_wr_valid&&host_wr_ready)writes=writes+1;
   if(host_ack_valid&&host_ack_ready)acks=acks+1;
   if(rd_valid&&rd_ready)reads=reads+1;
  end
 end
 task tick;begin @(posedge clk);#1;end endtask
 task start;
  begin @(negedge clk);op_valid=1;tick();@(negedge clk);op_valid=0;cap_valid=1;tick();@(negedge clk);cap_valid=0;end
 endtask
 initial begin
  tick();tick();@(negedge clk);rst_n=1;start();tick();
  if(!host_ack_valid||!pending_write||!vector_ACK_visible||vector_ACK_epoch!=1||!writes_visible||fence_valid)$fatal(1,"FAIL_FIRST_LOCAL_ACK");
  // Old actual ACK is held; requests cannot overtake its sole outstanding slot.
  @(negedge clk);op_valid=1;op_epoch=2;cap_epoch=2;cap_valid=1;
  repeat(5)begin tick();if(op_ready||cap_ready||host_wr_valid||host_wr_ready||rd_ready||!host_ack_valid||!pending_write||vector_ACK_epoch!=1)$fatal(1,"FAIL_HELD_ACK_OVERTAKEN");end
  @(negedge clk);op_valid=0;cap_valid=0;rst_n=0;#1;
  if(host_ack_valid||pending_write||vector_ACK_visible||writes_visible||fence_valid)$fatal(1,"FAIL_COMMON_RESET_STALE_ACK");
  tick();@(negedge clk);rst_n=1;tick();tick();
  if(host_ack_valid||pending_write||vector_ACK_visible)$fatal(1,"FAIL_ACK_REAPPEARS_AFTER_COMMON_RESET");
  // Reset clears control, not SRAM. Both actual physical operand copies remain.
  @(negedge clk);rd_valid=1;tick();@(negedge clk);rd_valid=0;tick();tick();
  if(!rsp_valid||rsp_a!==cap_data||rsp_b!==cap_data)$fatal(1,"FAIL_BOTH_COPIES_RESET_RESIDENCE");
  repeat(3)begin tick();if(rd_ready||host_wr_ready||!rsp_valid||rsp_a!==cap_data||rsp_b!==cap_data)$fatal(1,"FAIL_HELD_RESPONSE_DRAIN");end
  @(negedge clk);rsp_ready=1;tick();@(negedge clk);rsp_ready=0;tick();
  cap_data={64{64'h7f80000000000000}};start();tick();
  if(!host_ack_valid||vector_ACK_epoch!=2||!pending_write)$fatal(1,"FAIL_NEW_LOCAL_EPOCH");
  @(negedge clk);producer_done_epoch=2;producer_done_valid=1;ack_retire_enable=1;tick();
  @(negedge clk);producer_done_valid=0;tick();
  if(host_ack_valid||pending_write||!fence_valid||fence_epoch!=2)$fatal(1,"FAIL_ACTUAL_COMMON_ACK_DRAIN");
  @(negedge clk);fence_ready=1;tick();@(negedge clk);fence_ready=0;tick();
  if(writes!=2||acks!=1||reads!=1||fence_valid)$fatal(1,"FAIL_CONDITIONAL_COUNTS");
  $display("PASS_RFACK_CONDITIONAL_DIRECT_COMMON_RESET writes=2 ack_consumed=1 reset_aborted_ACK=1 reads=1 cycles=%0d; NO_WIRE_TAG_OR_PRODUCTION_CDC_PROOF",cycles);$finish;
 end
endmodule
