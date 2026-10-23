`timescale 1ns/1ps
module tb;
  reg ck = 0; always #1 ck = ~ck;
  reg rst_n = 0;
  wire [7:0] r;
  qfd_c_b8_ft_rst_tree u (.rst_n(rst_n), .ck_c0r0(ck), .ck_c0r1(ck), .ck_c0r2(ck), .ck_c0r3(ck), .ck_c1r0(ck), .ck_c1r1(ck), .ck_c1r2(ck), .ck_c1r3(ck),
    .rst_c0r0(r[0]), .rst_c0r1(r[1]), .rst_c0r2(r[2]), .rst_c0r3(r[3]), .rst_c1r0(r[4]), .rst_c1r1(r[5]), .rst_c1r2(r[6]), .rst_c1r3(r[7]));
  integer e = 0, t0 = -1, fail = 0, k;
  always @(posedge ck) begin
    e <= e + 1;
    if (e == 40) rst_n <= 1;
    for (k = 0; k < 8; k = k + 1) if (r[k] !== r[0]) fail = 1;
    if (r[0] === 1'b1 && t0 < 0) t0 = e;
  end
  initial begin
    repeat (120) @(posedge ck);
    // 17 = 1 landing + D=15 chain flops + 1 sampling edge of this monitor
    $display("RELEASE all8_equal=%0d edges_after_rst_n=%0d", !fail, t0 - 40);
    if (fail || t0 - 40 != 17) $display("FAIL"); else $display("PASS");
    $finish;
  end
endmodule
