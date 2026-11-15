"""The GRT module is a literal pre-route dependency; old synth helpers remain synth."""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import kit_resume as KR
import test_kit_resume as fixture

MODULE=(HERE.parent/"grt_nonport_hold.tcl").read_text()

class GrtNonportResume(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="grt-nonport-resume-")
        self.root=Path(self.temp.name)
        self.image=patch.object(KR,"image_info",return_value={
            "image":"openroad/orfs:asap7lock","id":"sha256:fixture","created":"2026-08-27T00:00:00Z"})
        self.image.start()
        self.addCleanup(self.image.stop)
        self.addCleanup(self.temp.cleanup)

    def pair(self,upto="cts",change_synth=False):
        old=dict(fixture.KIT_FILES)
        old["config.mk"]+="export PRE_GLOBAL_ROUTE_TCL = /work/hold_repair_pre.tcl\nexport CORNER = TC\n"
        old["hold_repair_pre.tcl"]="source /work/grt_pre.tcl\n"
        old["grt_pre.tcl"]="# existing GRT hook\n"
        old["orfs_hold_mm.py"]="# unchanged legacy synth helper\n"
        _,ok=fixture.make_kit(self.root,"old",files=old,upto=upto)
        new=dict(old)
        new["config.mk"]+="export OT_GRT_NONPORT_HOLD = 1\n"
        new["hold_repair_pre.tcl"]+="source /work/grt_nonport_hold.tcl\n"
        new["grt_nonport_hold.tcl"]=MODULE
        if change_synth:new["orfs_hold_mm.py"]+="# actual changed synth helper\n"
        _,nk=fixture.make_kit(self.root,"new",files=new,upto=None)
        # Supported inputs refresh: record the newly staged literal dependency.
        KR.write_inputs(str(nk))
        return fixture.man(ok),fixture.man(nk)

    def test_old_cts_reuses_through_cts_and_starts_grt(self):
        old,new=self.pair()
        self.assertEqual(new["files"]["grt_nonport_hold.tcl"]["stage"],"grt")
        self.assertEqual(new["config"]["OT_GRT_NONPORT_HOLD"]["stage"],"grt")
        decision=KR.decide(new,old)
        self.assertEqual((decision["decision"],decision["start_fingerprint"],decision["start"]),
                         ("resume","grt","grt"),decision)
        self.assertEqual(decision["reuse"],["synth","floorplan","place","cts"])

    def test_place_only_still_owes_cts(self):
        old,new=self.pair(upto="place")
        decision=KR.decide(new,old)
        self.assertEqual((decision["decision"],decision["start_fingerprint"],decision["start"]),
                         ("resume","grt","cts"),decision)
        self.assertEqual(decision["reuse"],["synth","floorplan","place"])

    def test_changed_old_mm_python_helper_remains_synth(self):
        old,new=self.pair(change_synth=True)
        decision=KR.decide(new,old)
        self.assertEqual((decision["decision"],decision["start"]),("full","synth"),decision)

if __name__=="__main__":unittest.main()

