`timescale 1ns/1ps
module tb_hstn_split;
  reg ck = 0;
  always #5 ck = ~ck;
  reg [758:0] di;
  wire [758:0] original, split;
  dsfd_hstn_proof_original759 a(.ck(ck), .di(di), .dq(original));
  dsfd_hstn_proof_low276 b0(.ck(ck), .di(di[275:0]), .dq(split[275:0]));
  dsfd_hstn_proof_mid276 b1(.ck(ck), .di(di[551:276]), .dq(split[551:276]));
  dsfd_hstn_proof_high207 b2(.ck(ck), .di(di[758:552]), .dq(split[758:552]));
  integer cycles = 0;
  integer b, n, j;
  reg [31:0] prng = 32'h6d697834;
  reg [758:0] pattern;
  task capture;
    input [758:0] value;
    reg [758:0] held_original, held_split;
    begin
      @(negedge ck);
      held_original = original;
      held_split = split;
      #1 di = value;
      #1;
      if (cycles > 0 && (original !== held_original || split !== held_split))
        $fatal(1, "HSTN_SPLIT FAIL changed without capture edge cycle=%0d", cycles);
      @(posedge ck);
      #1;
      if (original !== value)
        $fatal(1, "HSTN_SPLIT FAIL original capture/latency cycle=%0d", cycles);
      if (split !== value || split !== original)
        $fatal(1, "HSTN_SPLIT FAIL split mapping/capture/latency cycle=%0d xor=%h", cycles, split ^ original);
      cycles = cycles + 1;
    end
  endtask
  initial begin
    di = 0;
    capture(0);
    capture({759{1'b1}});
    for (b = 0; b < 759; b = b + 1) begin
      pattern = 0; pattern[b] = 1; capture(pattern);
      pattern = {759{1'b1}}; pattern[b] = 0; capture(pattern);
    end
    for (n = 0; n < 4096; n = n + 1) begin
      for (j = 0; j < 759; j = j + 1) begin
        prng = prng ^ (prng << 13);
        prng = prng ^ (prng >> 17);
        prng = prng ^ (prng << 5);
        pattern[j] = prng[0];
      end
      capture(pattern);
    end
    $display("HSTN_SPLIT PASS cycles=%0d bits=759 original=512+247 split=276+276+207 same_edge=posedge", cycles);
    $finish;
  end
endmodule
