`timescale 1ns/1ps
// Real native leaf, ideal ACK stimulus at its declared boundary. No native
// compute result is supplied. Assert fixed capture/count edges and local reset
// for every write-root phase, including reset during active ACK traffic.
module tb_host_ack_pin;
 parameter integer MUT=0;
 reg host=0,core=0,launch=0,write=0,rst=0;reg[7:0]ack=0;
 integer phase=0,step=0,checks=0;reg[7:0]expected_pin=0;reg[31:0]expected_count=0;
 always #3 host=~host;
 initial begin #1;forever #3 core=~core;end
 initial begin #2;forever #3 launch=~launch;end
 initial begin if(!$value$plusargs("phase=%d",phase))phase=0;#(phase);forever #3 write=~write;end
 dsfd_host_native_leaf dut(.ck_launch(launch),.ck_host(host),.ck_core(core),.ck_write(write),.rst_n(rst),
  .host_word(515'd0),.t_cr(1'b1),.o_cr(1'b0),.host_ack_n(ack),
  .o_v(),.o_we(),.o_addr(),.o_d(),.t_v(),.t_d(),.fault());
 initial begin #29 rst=1;#260 rst=0;#17 rst=1;#1000;
  if(checks<150)$fatal(1,"ACK_PIN missing samples");
  $display("ACK_PIN PASS phase=%0d checks=%0d fixed_capture_to_count=1 reset_flush=2",phase,checks);$finish;
 end
 always @(negedge write)begin step=step+1;ack=rst&&((step%5==0)||(step%7==0));end
 always @(posedge write)begin
  if(!dut.native_ingest.fence.g_on.rn_c)expected_count=0;
  else if(!dut.native_ingest.fence.g_on.fc)expected_count=expected_count+expected_pin;
  expected_pin=dut.rn_ack?ack:0;
  #0.01;
  // Raw asynchronous assertion wins when it coincides with this edge.
  if(!rst)begin expected_count=0;expected_pin=0;end
  if(dut.ack_pin!==expected_pin || dut.native_ingest.fence.g_on.commits!==expected_count)
   $fatal(1,"ACK_PIN FAIL fixed capture/count edge phase=%0d step=%0d",phase,step);
  checks=checks+1;
 end
endmodule
