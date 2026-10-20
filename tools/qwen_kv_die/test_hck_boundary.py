"""KV hck IO is restored after io_ref without changing clocks or exceptions."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import kvs_tile_kits_rep as K

class Boundary(unittest.TestCase):
 def test_generated_boundary_is_idempotent_and_drops_crossing_constraints(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);(root/'physical/qkd_kvs_kits').mkdir(parents=True)
   sdc='physical/qkd_kvs_kits/test_hck.sdc'
   (root/sdc).write_text("""create_clock -name hclk -period 1024 [get_ports hck]
set_clock_uncertainty 25 [get_clocks hclk]
set_max_delay 1024 -from [get_clocks hclk]
set_min_delay 0 -from [get_clocks hclk]
set ot_cw_hi [get_ports {hin}]
set ot_cw_ho [get_ports {hout}]
if {[llength $ot_cw_hi]} { unset_input_delay $ot_cw_hi }
if {[llength $ot_cw_ho]} { unset_output_delay $ot_cw_ho }
set_input_delay -clock hclk -max 204.8 $ot_cw_hi
set_output_delay -clock hclk -min 204.8 $ot_cw_ho
""")
   with patch.object(K,'ROOT',root):
    sp={'sdc_extra':[sdc],'boundary_tcl':['existing.tcl']}
    K.add_boundary_tcl('test',sp);first=json.dumps(sp)
    K.add_boundary_tcl('test',sp);self.assertEqual(first,json.dumps(sp))
    out=(root/sp['boundary_tcl'][-1]).read_text()
    self.assertEqual(sp['boundary_tcl'][0],'existing.tcl')
    for banned in ('create_clock','set_clock_uncertainty','set_max_delay','set_min_delay'):
     self.assertNotIn(banned,out)
    self.assertIn('unset_input_delay -clock [get_clocks core_clk] $ot_cw_hi',out)
    self.assertIn('unset_output_delay -clock [get_clocks core_clk] $ot_cw_ho',out)
    self.assertIn('set_input_delay -clock hclk -max 204.8',out)
    self.assertIn('set_output_delay -clock hclk -min 204.8',out)
 def test_missing_hck_io_does_not_emit_boundary(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);(root/'test_hck.sdc').write_text('create_clock -name hclk -period 1024 [get_ports hck]')
   with patch.object(K,'ROOT',root):
    self.assertIsNone(K.hck_boundary_tcl('test','test_hck.sdc'))
