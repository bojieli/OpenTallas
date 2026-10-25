import importlib.util,subprocess,tempfile,unittest
from pathlib import Path
here=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('gen',here/'gen_core_kit_kv.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
class ZoneScope(unittest.TestCase):
 def test_generated_hook_reaches_global_scope(self):
  with tempfile.TemporaryDirectory() as td:
   d=Path(td);g.astk_zone_fences(d,['export PRE_GLOBAL_PLACE_TCL = x','export PRE_DETAIL_PLACE_TCL = x','export PRE_CTS_TCL = x'],190.08,181.44,4.32)
   wrapper=(d/'zone_pre_gpl.tcl').read_text().replace('source /work/face_flops.tcl','').replace('source /work/zone_fence.tcl','uplevel #0 {if {![info exists ot_zone_spec]} {error {missing global zone spec}}; if {[llength $ot_zone_spec] != 30} {error {bad zones}}}')
   def run(s):return subprocess.run(['tclsh'],input='proc sourced_hook {} {\n'+s+'\n}\nif {[catch {sourced_hook} err]} {puts stderr $err;exit 1}\n',text=True,capture_output=True)
   self.assertEqual(run(wrapper).returncode,0)
   self.assertNotEqual(run(wrapper.replace('set ::ot_zone_spec','set ot_zone_spec')).returncode,0)
if __name__=='__main__':unittest.main()
