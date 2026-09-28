`timescale 1ns/1ps
module tb_v41_vm_gw4_slice;
  reg clk = 0;
  always #5 clk = ~clk;
  reg [14:0] base_word;
  reg [3:0] in_v;
  reg [511:0] in_data;
  wire [3:0] bank_we;
  wire [51:0] bank_addr;
  wire [511:0] bank_data;
  integer offset, mask, b, lane, failures = 0;
  ot_v41_vm_gw4_slice dut (.*);
  initial begin
    for (offset=0; offset<4; offset=offset+1)
      for (mask=0; mask<16; mask=mask+1) begin
        @(negedge clk);
        base_word = 15'(100+offset);
        in_v = 4'(mask);
        for (integer l=0; l<4; l=l+1)
          in_data[128*l +: 128] = {96'h0, 32'(1000+16*offset+l)};
        @(posedge clk); @(posedge clk); #1;
        for (b=0; b<4; b=b+1) begin
          lane = (b-offset+4)%4;
          if (bank_we[b] !== in_v[lane] ||
              bank_addr[13*b +: 13] !== 13'((100+offset+lane)/4) ||
              bank_data[128*b +: 128] !== in_data[128*lane +: 128]) begin
            $display("FAIL offset=%0d mask=%0d bank=%0d lane=%0d", offset,mask,b,lane);
            failures = failures+1;
          end
        end
      end
    if (failures) $fatal(1,"%0d mapping failures",failures);
    $display("PASS: 64 offsets/masks, every four-bank write mapping");
    $finish;
  end
endmodule
