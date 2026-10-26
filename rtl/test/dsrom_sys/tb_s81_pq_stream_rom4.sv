`timescale 1ns/1ps
// Exact bench: four real ot_rom_4096x72_m8 macros + ot_s81_pq_stream_rom4_sel vs a 16,384-row reference with the
// same two-cycle contract, random and sequential addresses across all banks every cycle.
module tb_s81_pq_stream_rom4;
  reg clk=0; always #5 clk=~clk;
  reg [13:0] sa=0; wire [11:0] a; wire [3:0] ce; wire [71:0] r0,r1,r2,r3; wire [47:0] sq;
  ot_s81_pq_stream_rom4_sel dut(.clk(clk),.sa(sa),.a(a),.ce(ce),.rd0(r0[47:0]),.rd1(r1[47:0]),.rd2(r2[47:0]),.rd3(r3[47:0]),.sq(sq));
  ot_rom_4096x72_m8 #(.VIAMAP("rom4_b0.viamap.hex"),.INSTANCE("b0")) m0(.clk(clk),.ce_in(ce[0]),.addr_in(a),.rd_out(r0));
  ot_rom_4096x72_m8 #(.VIAMAP("rom4_b1.viamap.hex"),.INSTANCE("b1")) m1(.clk(clk),.ce_in(ce[1]),.addr_in(a),.rd_out(r1));
  ot_rom_4096x72_m8 #(.VIAMAP("rom4_b2.viamap.hex"),.INSTANCE("b2")) m2(.clk(clk),.ce_in(ce[2]),.addr_in(a),.rd_out(r2));
  ot_rom_4096x72_m8 #(.VIAMAP("rom4_b3.viamap.hex"),.INSTANCE("b3")) m3(.clk(clk),.ce_in(ce[3]),.addr_in(a),.rd_out(r3));
  function automatic [47:0] word(input integer k); word = {k[13:0], 34'(k*40503 ^ 34'h2_5a5a_1234)}; endfunction
  // Each negedge: the next address is launched, then (before the core's capture edge) sq must hold the word of
  // the PREVIOUS address, sampled by the macros on the posedge in between.
  reg [13:0] prev; integer c, bad=0, checks=0;
  initial begin
    for (c=0;c<20000;c=c+1) begin
      @(negedge clk);
      sa = (c<16384) ? 14'(c*4097) : 14'($urandom);
      #1;
      if (c>=1) begin checks=checks+1; if (sq!==word(prev)) begin bad=bad+1; if (bad<5) $display("ROM4 mismatch c=%0d addr=%0d got %h want %h",c,prev,sq,word(prev)); end end
      prev=sa;
    end
    if (bad) begin $display("ROM4 FAIL mismatches=%0d checks=%0d",bad,checks); $fatal(1); end
    $display("ROM4 PASS checks=%0d rows=16384 banks=4 two-cycle",checks); $finish;
  end
endmodule
