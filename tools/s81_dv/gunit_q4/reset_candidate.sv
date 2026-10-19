`timescale 1ns/1ps
// Source-only reset contract prototype; NOT selected by GUNIT RTL.
// Assertion adds a physical async-clear->sync0.Q->region.async-clear path.
// The zero-delay RTL cannot prove its pulse width, recovery or propagation.
module s81_gunit_reset_candidate(input wire clk, raw_n, output wire [11:0] region_n);
  (* async_reg = "true" *) reg [1:0] sync_q;
  always @(posedge clk or negedge raw_n)
    if(!raw_n)sync_q<=0;else sync_q<={sync_q[0],1'b1};
  genvar k;
  generate for(k=0;k<12;k=k+1)begin:g_region
    (* keep = 1 *) reg q;
    always @(posedge clk or negedge sync_q[0])
      if(!sync_q[0])q<=0;else q<=sync_q[1];
    assign region_n[k]=q;
  end endgenerate
endmodule
