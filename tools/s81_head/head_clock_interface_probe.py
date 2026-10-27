#!/usr/bin/env python3
"""Extract and test the actual five-wire interface mechanism, not the datapath."""
import re
import sys
from pathlib import Path

source, out = map(Path, sys.argv[1:3])
t = source.read_text()
frag = re.search(r"    wire clk = ft_mstrap_i;\n(?:    assign ft_[^\n]+;\n){4}", t)
assert frag, "actual provider interface assignments missing"
f = frag.group().replace("wire clk =", "assign c =")
out.write_text("""module head_actual_if(input ft_mstrap_i, ft_ck0_i, ft_ck1_i, ft_mesh_i, ft_rst_i,
 output c, ft_ck0_o, ft_ck1_o, ft_mesh_o, ft_rst_o);
""" + f + """
endmodule
module tb;
 reg clk=0; reg [3:0] pins=0;
 wire c, ck0, ck1, mesh, rst;
 head_actual_if u(clk,pins[0],pins[1],pins[2],pins[3],c,ck0,ck1,mesh,rst);
 integer old_edges=0, new_edges=0, checks=0;
 always @(posedge clk) old_edges++;
 always @(posedge c) new_edges++;
 initial begin
  for(integer n=0;n<128;n++) begin
   pins=n[3:0]; #1; clk=~clk; #1;
   if ({ck0,ck1,mesh,rst}!={pins[0],pins[1],pins[2],pins[3]} || old_edges!=new_edges)
    $fatal(1,"INTERFACE_MISMATCH n=%0d old=%0d new=%0d",n,old_edges,new_edges);
   checks++;
  end
  $display("HEAD_IF_MITER PASS checks=%0d clock_edges=%0d added_cycles=0",checks,new_edges);
  $finish;
 end
endmodule
""")
out.with_name(out.stem+"_mut.sv").write_text(out.read_text().replace("assign ft_rst_o = ft_rst_i;", "assign ft_rst_o = ~ft_rst_i;"))
