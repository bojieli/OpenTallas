import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import h4_hbm_r43_rf_lifetime_diagnosis as m

class LifetimeDiagnosisTests(unittest.TestCase):
    def native(self):
        return dict(instructions=[dict(pc=0,reads=[],writes=[dict(version='unused')],source_outputs=[dict(version='unused')]),dict(pc=1,reads=[],writes=[])])
    def test_dead_produced_output_eligible(self):
        self.assertTrue(m.unused_output(self.native(),'unused',0))
    def test_future_read_blocks_dead_release(self):
        n=self.native();n['instructions'][1]['reads']=[dict(version='unused')]
        self.assertFalse(m.unused_output(n,'unused',0))
    def test_auxiliary_or_provider_reference_blocks_dead_release(self):
        n=self.native();n['instructions'][1]['provider_bindings']=dict(aux=dict(identity_from_versions=['unused']))
        self.assertFalse(m.unused_output(n,'unused',0))
    def test_wrong_birth_and_unknown_version_refuse(self):
        self.assertFalse(m.unused_output(self.native(),'unused',1))
        self.assertFalse(m.unused_output(self.native(),'absent',0))
    def test_physical_slot_overlap_detects_subrange_and_SM(self):
        h=[dict(SM=1,home=dict(class_='RF',slot_first=32,vectors=2)),dict(SM=1,home=dict(class_='RF',slot_first=33,vectors=2)),dict(SM=2,home=dict(class_='RF',slot_first=32,vectors=2))]
        for x in h:x['home']['class']=x['home'].pop('class_')
        self.assertEqual(m.slots(h,[0])&m.slots(h,[1]),{(1,33)})
        self.assertFalse(m.slots(h,[0])&m.slots(h,[2]))
    def test_source_hash_guard(self):
        import tempfile,shutil
        old=m.BASE
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);shutil.copyfile(old/'input_manifest.json',p/'input_manifest.json')
            (p/'inputs').mkdir();(p/'inputs/bound_native.json.gz').write_bytes(b'forged')
            m.BASE=p
            try:
                with self.assertRaisesRegex(ValueError,'source pin'):m.inputs()
            finally:m.BASE=old
if __name__=='__main__':unittest.main()
