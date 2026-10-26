`timescale 1ns/1ps
module kcopy (input [0:0] ck, cks, rs, rss, input [1100:0] i, output [0:0] fo, fo2, output [565:0] oa, output [537:0] ob, output [2:0] st);
  wire [565:0] odb; wire [2:0] stb_nc;
  dsfd_l2r_vr_564x1__hx_E A (.ck(ck), .cks(cks), .fo(fo), .i(i[564:0]), .od(oa), .rs(rs), .rss(rss), .st(st));
`ifdef MUT
  dsfd_l2r_vr_564x1__hx_E B (.ck(ck), .cks(cks), .fo(fo2), .i({28'b0, i[1100:565], i[1]}), .od(odb), .rs(rs), .rss(rss), .st(stb_nc));
`else
  dsfd_l2r_vr_564x1__hx_E B (.ck(ck), .cks(cks), .fo(fo2), .i({28'b0, i[1100:565], i[0]}), .od(odb), .rs(rs), .rss(rss), .st(stb_nc));
`endif
  assign ob = odb[537:0];
endmodule
module tb;
  reg ck=0, cks=0, rs=0, rss=0; reg [1100:0] i;
  wire [0:0] fo_r, fo2_r, fo_k, fo2_k; wire [565:0] oa_r, oa_k; wire [537:0] ob_r, ob_k; wire [2:0] st_r, st_k;
  dsfd_l2r_vr_1100x1__hx_E R (.ck(ck), .cks(cks), .fo(fo_r), .i(i), .oa(oa_r), .ob(ob_r), .rs(rs), .rss(rss), .st(st_r), .fo2(fo2_r));
  kcopy K (.ck(ck), .cks(cks), .rs(rs), .rss(rss), .i(i), .fo(fo_k), .fo2(fo2_k), .oa(oa_k), .ob(ob_k), .st(st_k));
  always #1 ck = ~ck;
  always #1 cks = ~cks;
  integer n, err=0, k;
  initial begin
    i = 0;
    for (n = 0; n < 4000; n = n + 1) begin
      for (k = 0; k < 1101; k = k + 32) i[k +: 32] = $random;
      if (n == 3) rs = 1; if (n == 5) rss = 1; if (n == 2000) begin rs = 0; rss = 0; end if (n == 2010) begin rs = 1; rss = 1; end
      @(negedge ck);
      if ({fo_r,fo2_r,oa_r,ob_r,st_r} !== {fo_k,fo2_k,oa_k,ob_k,st_k}) begin err = err + 1; if (err < 4) $display("MISMATCH n=%0d", n); end
    end
    if (err == 0) $display("L2R1100_KCOPY_EXACT PASS 4000 cycles x 1110 outputs"); else begin $display("L2R1100_KCOPY_MISMATCH %0d", err); $fatal; end
    $finish;
  end
endmodule
