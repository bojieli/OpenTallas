import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path[:0]=[str(Path(__file__).parent),str(Path(__file__).parent.parent/'die_plan')]
import canary as C
NET=r'''
module top(clk_cap, rst_n, a, active);
input clk_cap; input rst_n; input a; output active;
wire q;
DFFHQNx1_ASAP7_75t_R f0 (.CLK(clk_cap), .D(a), .QN(q));
DFFHQNx1_ASAP7_75t_R f1 (.CLK(clk_cap), .D(q), .QN(active));
endmodule
'''
class ClockCover(unittest.TestCase):
 def test_declared_clock_pins_do_not_mask_shared_data(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);nl=p/'n.v';nl.write_text(NET)
   pins=p/'pins.json';pins.write_text(json.dumps([{'bus':x,'bit':None} for x in ('clk_cap','rst_n','a','active')]))
   clock=C.configured_clock_ports('create_clock -name c -period 833 [get_ports {clk_cap}]\n')
   good=C.face_cover(nl,pins,clock_ports=clock)
   self.assertEqual(good['verdict'],'PASS',good)
   nl.write_text(NET.replace('endmodule','BUFx2_ASAP7_75t_R extra (.A(active), .Y(dangling));\nendmodule'))
   bad=C.face_cover(nl,pins,clock_ports=clock)
   self.assertEqual(bad['verdict'],'FAIL');self.assertIn('shared',bad['fails'])
 def test_nonliteral_clock_selector_cannot_hide_data(self):
  self.assertEqual(C.configured_clock_ports('create_clock -name c [get_ports {clk_cap fault* active?}]'),['clk_cap'])

if __name__=='__main__':unittest.main()
