`timescale 1ns/1ps
module tb;
  reg ck = 0, rs = 0, rfi = 1; reg [47:0] i = 0; wire [47:0] o; wire rso, rfo, rfo2; wire [47:0] o2;
  always #5 ck = ~ck;
  hbfd_rly_48_WE_rrf u (.ck(ck), .rs(rs), .i(i), .o(o), .rso(rso), .rfi(rfi), .rfo(rfo));
  hbfd_rly_48_WE_rf  v (.ck(ck), .rs(rs), .i(i), .o(o2), .rfi(rfo), .rfo(rfo2));
  integer e = 0, r1 = -1, r2 = -1;
  always @(posedge ck) begin e <= e + 1; if (rfo && r1 < 0) r1 <= e; if (rfo2 && r2 < 0) r2 <= e; end
  initial begin
    #1 rfi = 0; #1 if (rfo !== 1'b0) begin $display("FAIL rfo not cleared"); $finish; end
    repeat (3) @(negedge ck); rfi = 1;           // release at edge e=3
    repeat (6) @(negedge ck);
    if (r1 != 4 || r2 != 5) $display("FAIL release ages r1=%0d r2=%0d (expected 4 5: one edge per hosted hop)", r1, r2);
    else $display("RF_HOP_BENCH PASS release 1 edge per hosted hop (r1=%0d r2=%0d)", r1, r2);
    rfi = 0; #1 if (rfo !== 0) $display("FAIL async assert"); else $display("RF_ASSERT PASS");
    $finish;
  end
endmodule
