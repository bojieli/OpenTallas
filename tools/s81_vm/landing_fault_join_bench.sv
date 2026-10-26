`timescale 1ns/1ps
module tb;
 reg ck=0; always #5 ck=~ck;
 reg[11:0] i_fault=0; wire[2:0] o_fault;
 reg[11:0] prev; reg[2:0] expected;
 integer c,bad=0,checked=0;
 dsfd_vm_static_landing_fault_join dut(.ck(ck),.i_fault(i_fault),.o_fault(o_fault));
 always @(posedge ck) begin prev<=i_fault; expected<=prev[2:0]|prev[5:3]|prev[8:6]|prev[11:9]; end
 initial begin
 for(c=0;c<4100;c=c+1) begin
  @(negedge ck); i_fault=c<4?0:c-4;
  @(posedge ck); #1;
  if(c>=3) begin checked=checked+1; if(o_fault!==expected)bad=bad+1; end
 end
 if(bad==0) begin $display("LANDING_FAULT_JOIN PASS patterns=4096 checked=%0d stages=2",checked); $finish; end
 else begin $display("LANDING_FAULT_JOIN FAIL bad=%0d",bad);$fatal(1);end
 end
endmodule
