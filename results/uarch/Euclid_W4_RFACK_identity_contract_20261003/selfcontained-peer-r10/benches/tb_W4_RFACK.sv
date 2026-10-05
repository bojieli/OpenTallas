`timescale 1ns/1ps
// Conditional component inputs: no production C0/KV caller or CDC qualification.
module tb_W4_RFACK;
 reg clk=0,rst_n=0;always #5 clk=~clk;
 reg rd_valid=0,rsp_ready=0,wr_valid=0,ack_ready=0;
 reg [8:0] rd_a=511,rd_b=511,wr_addr=511;
 reg [4095:0] wr_data={128{32'h7fc01234}};
 reg [45:0] wr_owner={7'd127,3'd5,32'hfedcba98,4'd15};
 wire rd_ready,rsp_valid,wr_ready,ack_valid,ack_identity_fault;
 wire [4095:0] rsp_a,rsp_b;wire [45:0] ack_owner;wire [8:0] ack_slot;
 ot_gpu_rf_service #(.ACK_ID(1)) dut(.*);
 integer writes=0,acks=0,cycles=0,i,j;reg [71:0] code;reg [55:0] decoded;
 reg [45:0] expected_owner;reg [4095:0] expected_data;
 always @(posedge clk)begin cycles=cycles+1;if(rst_n)begin if(wr_valid&&wr_ready)writes=writes+1;if(ack_valid&&ack_ready)acks=acks+1;end end
 task tick;begin @(posedge clk);#1;end endtask
 task put;begin
  expected_owner=wr_owner;expected_data=wr_data;
  @(negedge clk);wr_valid=1;#1;if(!wr_ready)$fatal(1,"write blocked");tick();
  if(ack_valid)$fatal(1,"no extra ACK stage");
  @(negedge clk);wr_valid=0;wr_owner=~wr_owner;wr_addr=0;tick();
  if(!ack_valid||ack_owner!==expected_owner||ack_slot!==511||ack_identity_fault)$fatal(1,"accepted source identity mismatch");
 end endtask
 initial begin
  // Exhaustive singlebit correction and doublebit refusal for one mixed owner.
  code=dut.w4_encode({wr_owner,wr_addr});
  for(i=0;i<72;i=i+1)begin decoded=dut.w4_decode(code^(72'b1<<i));if(decoded!=={1'b0,wr_owner,wr_addr})$fatal(1,"singlebit codec");end
  for(i=0;i<72;i=i+1)for(j=i+1;j<72;j=j+1)begin decoded=dut.w4_decode(code^(72'b1<<i)^(72'b1<<j));if(!decoded[55])$fatal(1,"doublebit codec");end
  tick();@(negedge clk);rst_n=1;put();
  @(negedge clk);wr_valid=1;
  repeat(5)begin tick();if(wr_ready||rd_ready||!ack_valid||ack_owner!==expected_owner||ack_slot!==511)$fatal(1,"held ACK overwritten");end
  // local reset abort is tested, never claimed to drain a backend/CDC epoch.
  @(negedge clk);wr_valid=0;rst_n=0;#1;if(ack_valid||wr_ready||rd_ready)$fatal(1,"async reset control");
  tick();@(negedge clk);rst_n=1;rd_valid=1;tick();@(negedge clk);rd_valid=0;tick();
  if(!rsp_valid||rsp_a!==expected_data||rsp_b!==expected_data)$fatal(1,"both real RF copies residence");
  @(negedge clk);rsp_ready=1;tick();@(negedge clk);rsp_ready=0;
  wr_addr=511;wr_owner={7'd64,3'd0,32'h00000000,4'd0};wr_data={128{32'h3f800000}};put();
  @(negedge clk);ack_ready=1;tick();@(negedge clk);ack_ready=0;tick();
  if(ack_valid||writes!=2||acks!=1)$fatal(1,"single common ACK count");
  $display("PASS_W4_RFACK owner46_slot9 writes2 ACK1 resetAbort1 bothcopies singlebit72 doublebit2556 addedACKedge1 cycles%0d CONDITIONAL_COMPONENT_ONLY",cycles);$finish;
 end
endmodule
