import importlib.machinery
import importlib.util
from pathlib import Path
import unittest
loader=importlib.machinery.SourceFileLoader('reconcile_phase_class',str(Path(__file__).with_name('ot-heavy-reconcile')))
spec=importlib.util.spec_from_loader(loader.name,loader);R=importlib.util.module_from_spec(spec);loader.exec_module(R)

class PhaseClassTest(unittest.TestCase):
    def test_phase_repair_and_drt_do_not_share_history(self):
        a=R.classify(['bash','/scratch/pc/run_phase1.sh'])
        b=R.classify(['bash','/scratch/pc/run_phase2.sh'])
        self.assertEqual(a,'run_phase1.sh');self.assertEqual(b,'run_phase2.sh')
    def test_numbered_native_stages_remain_distinct(self):
        self.assertNotEqual(R.classify(['bash','run_stage5_1.sh']),R.classify(['bash','run_stage5_2.sh']))
    def test_dates_hashes_and_ordinary_trial_numbers_still_pool(self):
        self.assertEqual(R.class_token('run_phase2_20261102_deadbeef.sh'),'run_phase2_#_#.sh')
        self.assertEqual(R.class_token('run_phase2_20261103_aabbccdd.sh'),'run_phase2_#_#.sh')
        self.assertEqual(R.class_token('stage_20261102.sh'),'stage_#.sh')
        self.assertEqual(R.class_token('run_trial123.sh'),'run_trial#.sh')
    def test_shell_and_direct_script_keep_same_class(self):
        self.assertEqual(R.classify(['bash','run_phase2.sh']),R.classify(['run_phase2.sh']))

if __name__=='__main__':unittest.main()
