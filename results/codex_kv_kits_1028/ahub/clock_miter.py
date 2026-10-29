#!/usr/bin/env python3
"""Smallest lockstep vehicle for the exact generated zh clock expression."""
import re
import sys
from pathlib import Path

src = Path(sys.argv[1]).read_text()
mods = re.findall(r"^module qkd_ahub_static_dw_ck3\b.*?^endmodule\b", src, re.M | re.S)
assert len(mods) == 1
expr = re.search(r"ot_nhb_zh u_zh \(\.clk\((.*?)\), ", mods[0]).group(1)
assert expr == "ck_zh[(a < 2) ? 0 : 1]"
bench = r'''
module tb;
parameter MUT=0;
reg ck=0, rst=1;
wire [1:0] ck_zh={2{ck}};
reg [31:0] data=32'hace01234;
integer cycles=0, comparisons=0;
always #5 ck=~ck;
generate for(genvar a=0;a<4;a=a+1) begin:g
  reg [31:0] old_q=0, new_q=0;
  wire candidate_clk = (MUT && a==3) ? ~(__EXPR__) : (__EXPR__);
  always @(posedge ck) old_q <= rst ? 0 : data ^ a;
  always @(posedge candidate_clk) new_q <= rst ? 0 : data ^ a;
end endgenerate
initial begin
  repeat(4) @(negedge ck);
  rst=0;
  repeat(1000) begin
    data={data[30:0],data[31]^data[21]^data[1]^data[0]};
    @(posedge ck); #1;
    for(integer i=0;i<4;i=i+1) begin
      case(i)
      0:if(g[0].old_q!==g[0].new_q)$fatal(1,"CLOCK_MITER mismatch0");
      1:if(g[1].old_q!==g[1].new_q)$fatal(1,"CLOCK_MITER mismatch1");
      2:if(g[2].old_q!==g[2].new_q)$fatal(1,"CLOCK_MITER mismatch2");
      3:if(g[3].old_q!==g[3].new_q)$fatal(1,"CLOCK_MITER mismatch3");
      endcase
      comparisons=comparisons+1;
    end
    cycles=cycles+1;
    @(negedge ck);
  end
  $display("CLOCK_MITER PASS cycles=%0d state_comparisons=%0d added_cycles=0",cycles,comparisons);
  $finish;
end
endmodule
'''.replace('__EXPR__',expr)
Path(sys.argv[2]).write_text(bench)
