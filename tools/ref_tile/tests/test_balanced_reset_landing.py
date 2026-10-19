"""Balanced two-edge reset landing: strict pre-rewire identity and API guards."""
import importlib.util,json,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools/ref_tile'))
import ref_tile as RT
sp=importlib.util.spec_from_file_location('copies',ROOT/'physical/common_flow/ot_rst_copies.py');RS=importlib.util.module_from_spec(sp);sp.loader.exec_module(RS)

def wrapper(td,first=12,last=288,stages=2):
 script='''set ::env(DESIGN_NAME) example
set ::env(OT_PIN_REGS) 0
set ::env(OT_RST_LAND) 1
set ::env(OT_RST_LAND_STAGES) %s
set ::env(OT_PIN_REGS_CLOCK) ck
set ::env(OT_PIN_REGS_RESET_PORTS) rst_n
set ::env(OT_RST_COPIES_MAX) 32
set ::env(OT_RST_LAND_COPIES) rst_n=%s
set ::env(OT_RST_LAND_FIRST_COPIES) rst_n=%s
set ::env(RESULTS_DIR) {%s}
proc yosys {args} {
 if {[lindex $args 0] eq "tee"} {
 set f [open [lindex $args 3] w]
 puts $f {input [0:0] ck
input [0:0] rst_n
output [0:0] q}
 close $f
 }
}
if {[catch {source {%s}} msg]} {puts stderr $msg;exit 1}
'''%(stages,last,first,td,ROOT/'physical/common_flow/ot_pin_regs.tcl')
 return subprocess.run(['tclsh'],input=script,text=True,capture_output=True)

def ff(d,q,ck=2):
 return dict(type='$_DFF_P_',port_directions=dict(C='input',D='input',Q='output'),connections=dict(C=[ck],D=[d],Q=[q]))
def nl(first=12,last=288,loads=8500):
 c={};a=list(range(10,10+first));b=list(range(100,100+last))
 for i,q in enumerate(a):c[f'f{i}']=ff(1,q)
 for i,q in enumerate(b):c[f'l{i}']=ff(a[0],q)
 for i in range(loads):c[f'u{i}']=dict(type='$_DFF_PN0_',port_directions=dict(C='input',D='input',Q='output',R='input'),connections=dict(C=[2],D=[3],Q=[10000+i],R=[b[0]]))
 return dict(modules=dict(top=dict(attributes=dict(top='1'),ports={},cells=c,netnames={'rst_n__ot_rl0v':dict(bits=a),'rst_n__ot_rlv':dict(bits=b)})))
class T(unittest.TestCase):
 def test_snapshot_both_families(self):
  _,r=RS.analyse(nl(),32,RS.DEFAULT_RE)
  self.assertEqual(len(r),2)
  self.assertTrue(all(x['status']=='OK' for x in r))
  self.assertLessEqual(max(r[0]['groups']),24)
  self.assertLessEqual(max(r[1]['groups']),30)
 def test_old_unsafe(self):
  _,r=RS.analyse(nl(first=1,last=36),32,RS.DEFAULT_RE)
  self.assertTrue(any('OVER' in x['status'] for x in r))
 def test_crossclock_and_tied_refuse(self):
  for port,value in [('C',9),('D','0')]:
   x=nl();x['modules']['top']['cells']['l1']['connections'][port]=[value]
   _,r=RS.analyse(x,32,RS.DEFAULT_RE)
   self.assertTrue(any('REFUSED' in x['status'] for x in r))
 def test_wrapper(self):
  with tempfile.TemporaryDirectory() as td:
   r=wrapper(td);self.assertEqual(r.returncode,0,r.stderr)
   t=(Path(td)/'ot_rst_land_wrapper.v').read_text()
   self.assertIn('rst_n__ot_rl0c <= {11{rst_n}};',t)
   self.assertIn('rst_n__ot_rlc <= {287{rst_n__ot_rl0}};',t)
   self.assertIn('.rst_n(rst_n__ot_rl1)',t)
 def test_wrapper_guard(self):
  for f,l,st in [(1,288,2),(12,288,3),(33,288,2)]:
   with tempfile.TemporaryDirectory() as td:self.assertNotEqual(wrapper(td,f,l,st).returncode,0)
 def test_default_wrapper_unchanged(self):
  import test_reset_landing as old
  with tempfile.TemporaryDirectory() as td:
   p=Path(td);a=p/'a';b=p/'b';a.mkdir();b.mkdir()
   self.assertEqual(old.generate(a).returncode,0)
   expected=(ROOT/'tools/ref_tile/tests/fixtures/default_reset_wrapper.v').read_text()
   self.assertEqual((a/'ot_pin_regs_wrapper.v').read_text(),expected)

 def test_schema(self):
  s=dict(top='example',clock_port='ck',reset_ports=['rst_n'],reset_landing=dict(enable=True,stages=2,copies=dict(rst_n=288),first_copies=dict(rst_n=12)),reset_relay_split=dict(max_loads=32))
  self.assertEqual(RT.reset_landing_plan(s)['first_copies'],dict(rst_n=12))
  self.assertTrue(any('OT_RST_LAND_FIRST_COPIES=rst_n=12' in x for x in RT.reset_relay_split_vars(s)))
  for patch in [dict(stages=3),dict(first_copies=dict(rst_n=8)),dict(first_copies=dict(foreign=12)),dict(copies=None)]:
   bad=dict(s,reset_landing=dict(s['reset_landing'],**patch))
   with self.assertRaises(RT.SpecError):RT.reset_landing_plan(bad)
if __name__=='__main__':unittest.main()
