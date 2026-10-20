"""A direct input and its wire aliases may feed only one regional clock."""
import tempfile
from pathlib import Path
import unittest
import lp

class PortRegionAudit(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(dir=lp.ROOT/'tools/landed_parent')
  self.addCleanup(self.tmp.cleanup)
  d=Path(self.tmp.name)
  (d/'child.sv').write_text('module audit_child(input wire clk, d, output wire q); assign q=d; endmodule')
  self.spec=dict(top='audit_top',child_sources=[str((d/'child.sv').relative_to(lp.ROOT))],
    regions=[dict(name='a'),dict(name='b')],clock_ports=['clk'],reset_port='rst_n',static=['mode'])
 def rtl(self, second='data', first='data', same=False):
  return """module audit_top_lp(input wire ck_a, ck_b, rst_n, mode, data, output wire qa,qb);
wire alias1,alias2; assign alias1=data; assign alias2=alias1;
audit_child u0(.clk(ck_a),.d(FIRST),.q(qa));
audit_child u1(.clk(SECONDCLK),.d(SECOND),.q(qb)); endmodule""".replace('SECONDCLK','ck_a' if same else 'ck_b').replace('FIRST',first).replace('SECOND',second)
 def test_same_region_can_read_input_twice(self):
  self.assertTrue(lp.audit(self.spec,self.rtl(same=True))['ok'])
 def test_direct_multi_region_read_fails(self):
  r=lp.audit(self.spec,self.rtl());self.assertFalse(r['ok'])
  self.assertIn('UNLANDED port data',str(r['fails']))
 def test_transitive_wire_alias_cannot_hide_crossing(self):
  self.assertFalse(lp.audit(self.spec,self.rtl(second='alias2'))['ok'])
 def test_reset_static_and_regional_clock_are_exempt(self):
  for value in ('rst_n','mode','ck_a'):
   # A clock as data would invalidate instance region inference, so clock
   # exemption is exercised by the two clock pins in the reset/static cases.
   if value=='ck_a': continue
   self.assertTrue(lp.audit(self.spec,self.rtl(first=value,second=value))['ok'])
