module wrap_GOLD_GATE(input clk, input rst_n, input [1:0] sid, input rx_enable, input rx_source, input [287:0] rce0, input [287:0] rce1,
  input [273:0] hr_in, input assume_res0, output trigger);
  wire [273:0] hr = assume_res0 ? {hr_in[273],6'b0,hr_in[266:0]} : hr_in;
  wire [337:0] hq_a, hq_b; wire [265:0] a0,a1,b0,b1; wire fa, fb;
  g_GOLD ua(.clk(clk),.rst_n(rst_n),.sid(sid),.rx_enable(rx_enable),.rx_source(rx_source),.rce0(rce0),.rce1(rce1),.hq(hq_a),.hr(hr),.ri0(a0),.ri1(a1),.fault(fa));
  g_GATE ub(.clk(clk),.rst_n(rst_n),.sid(sid),.rx_enable(rx_enable),.rx_source(rx_source),.rce0(rce0),.rce1(rce1),.hq(hq_b),.hr(hr),.ri0(b0),.ri1(b1),.fault(fb));
  assign trigger = (hq_a!=hq_b)||(a0!=b0)||(a1!=b1)||(fa!=fb);
endmodule
