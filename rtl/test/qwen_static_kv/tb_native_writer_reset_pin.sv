`timescale 1ns/1ps
module tb_native_writer_reset_pin;
 parameter integer MUT=0;
 reg ck=0,rst_n=0; always #1 ck=~ck;
 qkd_kv_static_writer_native #(.RESET_PIN_CAPTURE(MUT==0)) dut(
 .ck(ck),.rst_n(rst_n),.word_valid(1'b0),.word_tag(11'b0),.word_data(512'b0),
 .word_identity(59'b0),.word_generation(2'b0),.compiled_word_slot(1'b0),
 .compiled_word_index(2'b0),.compiled_identity(59'b0),.compiled_generation(2'b0));
 integer epoch,i,checks=0;
 initial begin
  repeat(3) @(negedge ck);
  for(epoch=0;epoch<2;epoch=epoch+1) begin
   rst_n=1;
   for(i=1;i<=5;i=i+1) begin
    @(posedge ck); #0.01;
    if(dut.u_writer.rr !== (i>=4 ? 12'hfff : 12'h000))
      $fatal(1,"RESET_PIN FAIL epoch%0d edge%0d rr%h",epoch,i,dut.u_writer.rr);
    checks=checks+1;
   end
   #0.1;rst_n=0;#0.01;
   if(dut.u_writer.rr !== 12'h000)$fatal(1,"RESET_PIN FAIL asynchronous assertion");
   checks=checks+1;
   repeat(3) @(negedge ck);
  end
  $display("RESET_PIN PASS checks%0d twoepochs release4 immediate_async_assert",checks);$finish;
 end
endmodule
