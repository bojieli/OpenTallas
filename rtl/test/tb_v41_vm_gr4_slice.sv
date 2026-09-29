`timescale 1ns/1ps
module tb_v41_vm_gr4_slice;
  reg clk=0;
  always #5 clk=~clk;
  reg [1:0] first_bank;
  reg in_v;
  reg [511:0] bank_data;
  wire out_v;
  wire [511:0] out_data;
  integer offset, lane, bank, failures=0;
  ot_v41_vm_gr4_slice dut(.*);
  initial begin
    for (offset=0; offset<4; offset=offset+1) begin
      @(negedge clk);
      first_bank=2'(offset); in_v=1;
      for (bank=0; bank<4; bank=bank+1)
        bank_data[128*bank +: 128] = {96'b0,32'(100+bank)};
      @(posedge clk); @(posedge clk); #1;
      if (!out_v) failures++;
      for (lane=0; lane<4; lane=lane+1)
        if (out_data[128*lane +: 128] !== bank_data[128*((offset+lane)%4) +: 128])
          failures++;
    end
    if (failures) $fatal(1,"%0d read rotations failed",failures);
    $display("PASS: four unaligned read rotations");
    $finish;
  end
endmodule
