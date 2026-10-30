`timescale 1ns/1ps
module tb;
 parameter integer EXPECT_WR=11, ACTUAL_WR=11, EXPECT_FAULT=0;
 reg clk=0,rst_n=0;
 always begin #0.416 clk=1;#0.417 clk=0;end
 reg [1:0] drain_v=0,drain_result_v=0;
 reg [31:0] sectors=0;
 wire [2247:0] wq;
 wire [7:0] done;
 wire fault;
 reg [7:0] ack[0:ACTUAL_WR];
 wire [7:0] valid;
 for(genvar b=0;b<8;b=b+1)begin
  assign valid[b]=wq[281*b+280];
 end
 assign done=ack[ACTUAL_WR];
 integer writes=0,acks=0;
 always @(posedge clk)begin
  drain_result_v<=drain_v;
  if(!rst_n)begin
   for(integer i=0;i<=ACTUAL_WR;i=i+1)ack[i]<=0;
  end else begin
   ack[0]<=valid;
   for(integer i=1;i<=ACTUAL_WR;i=i+1)ack[i]<=ack[i-1];
   for(integer b=0;b<8;b=b+1)begin
    if(valid[b])writes<=writes+1;
    if(done[b])acks<=acks+1;
   end
  end
 end
 ot_hgi_sfu_vm_static_bridge #(.WRITE_RETURN(EXPECT_WR)) dut(
  .clk(clk),.rst_n(rst_n),.clk_lg({4{clk}}),.rst_lg_n({4{rst_n}}),
  .prefetch_v(8'd0),.prefetch_sector(128'd0),.prefetch_group(16'd0),
  .prefetch_local_addr(120'd0),.prefetch_scalar(8'd0),.prefetch_word(24'd0),.scalar_addr(96'd0),
  .local_rr(2056'd0),.drain_v(drain_v),.drain_round_bf16(2'd0),
  .drain_vm_sector(sectors),.drain_result_v(drain_result_v),.drain_data(512'd0),
  .local_wq(wq),.local_w_done(done),.fault(fault));
 initial begin
  repeat(20)@(negedge clk);rst_n=1;
  for(integer c=0;c<120;c=c+1)begin
   @(negedge clk);
   drain_v=(c%3==0)?2'b11:2'b00;
   sectors[15:0]=16'(c%8);sectors[31:16]=16'((c+4)%8);
  end
  @(negedge clk);drain_v=0;
  repeat(100)@(negedge clk);
  if(writes<32||acks<32)$fatal(1,"insufficient real writes %0d/%0d",writes,acks);
  if(fault!==EXPECT_FAULT[0])$fatal(1,"unexpected fault got%0d expected%0d WR%0d actual%0d",fault,EXPECT_FAULT,EXPECT_WR,ACTUAL_WR);
  $display("ACK_CONTRACT_PASS expect_wr=%0d actual_wr=%0d fault=%0d writes=%0d acks=%0d",EXPECT_WR,ACTUAL_WR,fault,writes,acks);
  $finish;
 end
endmodule
