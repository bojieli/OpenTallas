`timescale 1ps/1fs
// Minimum actual-byte gate, no SM/DRAM rebuild or arithmetic substitution.
module tb_hbm_accel_wg_gearbox;
 reg clk=0,rst_n=0;always #5 clk=~clk;
 reg [1023:0] source[0:1535];reg [1087:0] expected[0:1727];
 wire iv,ir,ov,done,fault;wire [1087:0] data;reg ready=0;
 integer input_index=0,output_index=0,cycles=0,slot=0,mut=0;
 assign iv=input_index<256;
 ot_hbm_accel_wg_gearbox #(.ENABLE(1)) dut(.clk(clk),.rst_n(rst_n),.start(1'b0),
  .in_valid(iv),.in_ready(ir),.in_data(source[slot*256+input_index]),
  .out_valid(ov),.out_ready(ready),.out_data(data),.done(done),.fault(fault));
 always @(negedge clk)ready=(cycles%7!=0);
 always @(posedge clk)if(rst_n)begin
  if(iv&&ir)input_index<=input_index+1;
  if(ov&&ready)begin
   if(output_index>=288||data!==expected[slot*288+output_index])$fatal(1,"actual source byte mismatch");
   output_index<=output_index+1;
  end
  if(fault)$fatal(1,"source pad/extent fault");
  cycles<=cycles+1;
 end
 initial begin
  string dir;if(!$value$plusargs("DIR=%s",dir))$fatal(1,"source required");
  void'($value$plusargs("slot=%d",slot));void'($value$plusargs("mut=%d",mut));
  if(slot<0||slot>=6)$fatal(1,"actualslot");
  $readmemh({dir,"/gu.hex"},source);$readmemh({dir,"/sm_expected.hex"},expected);
  if(mut)source[slot*256+26][0]=!source[slot*256+26][0];
  repeat(2)@(negedge clk);rst_n=1;
  // Every output/input is continuously offered; only one in7 output edges is
  // refused. At most544 accepts plus deterministic pauses fit under1024.
  repeat(1024)begin
   @(negedge clk);
   if(done)begin
    if(input_index!=256||output_index!=288)$fatal(1,"retirement count");
    $display("GEARBOX_ACTUAL_BYTE_PASS slot=%0d in=%0d out=%0d cycles=%0d",slot,input_index,output_index,cycles);$finish;
   end
  end
  $fatal(1,"GEARBOX_STALLED accepted=%0d issued=%0d count=%0d",input_index,output_index,dut.on.count);
 end
endmodule
