"""Bounded exact-name lookup checks; no physical process is started."""
from pathlib import Path
import re,subprocess,unittest
class Exact(unittest.TestCase):
 def test_matcher_order_dedup_and_fixed_member(self):
  p=Path(__file__).with_name('macro_reg_guide.tcl');s=p.read_text()
  fn=re.search(r'proc ot_mrg_exact_members .*?\n}',s,re.S).group(0)
  script=fn+r'''
set all [dict create {u.d[0]$_DFF_P_} i0 {u.d[1]$_DFF_P_} i1 {u.d[10]$_DFF_P_} i10]
set movable [dict remove $all {u.d[1]$_DFF_P_}]
set full {{u.d[0]$_DFF_P_} {u.d[1]$_DFF_P_}}
if {[ot_mrg_exact_members $full $all] ne {i0 i1}} {error "all"}
if {[ot_mrg_exact_members $full $movable] ne {i0}} {error "fixed exclusion"}
if {[ot_mrg_exact_members [concat $full $full] $all] ne {i0 i1}} {error "duplicate"}
if {[ot_mrg_exact_members {{u.d}} $all] ne {}} {error "exact mode matched hierarchy"}
puts PASS
'''
  r=subprocess.run(['tclsh'],input=script,text=True,capture_output=True)
  self.assertEqual(r.stderr,'');self.assertIn('PASS',r.stdout)
 def test_complete_tcl_and_default_flag(self):
  p=Path(__file__).with_name('macro_reg_guide.tcl')
  r=subprocess.run(['tclsh'],input='set f [open {'+str(p)+'}];set s [read $f];close $f;puts [info complete $s]\n',text=True,capture_output=True)
  self.assertEqual(r.stdout.strip(),'1')
  self.assertIn('OT_MACRO_REG_GUIDE_EXACT',p.read_text())
if __name__=='__main__':unittest.main()
