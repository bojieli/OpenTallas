module bchk(input clk, input rst_n, input [1:0] sid, input rx_enable, input rx_source, input [287:0] rce0, input [287:0] rce1, input [273:0] hr, output bad);
  wire [337:0] hq; wire [265:0] r0,r1; wire f;
  g_new u(.clk(clk),.rst_n(rst_n),.sid(sid),.rx_enable(rx_enable),.rx_source(rx_source),.rce0(rce0),.rce1(rce1),.hq(hq),.hr(hr),.ri0(r0),.ri1(r1),.fault(f));
  assign bad = hq[15:10] != 6'b0;
endmodule
