import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

SPEC=importlib.util.spec_from_file_location('terminal',Path(__file__).resolve().parents[1]/'tools/assess_dsrom_qpipe_terminal.py')
M=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)

class TerminalEvidence(unittest.TestCase):
    def test_negative_slack_never_selected(self):
        a=M.assess()
        self.assertTrue(a['R_cap0']['flow_completed'])
        self.assertEqual(a['R_cap0']['DRC'],0)
        self.assertLess(a['R_cap0']['SS_setup_WNS_ps'],0)
        self.assertLess(a['R_cap0']['FF_hold_WNS_ps'],0)
        self.assertEqual(a['R_cap0']['verdict'],'REJECTED_NO_RESCUE')
        self.assertIsNone(a['selected_q_abstract'])
        self.assertIsNone(a['selected_BF_abstract'])
    def test_actual_macro_alignment_and_geometry(self):
        a=M.assess()['R_cap0']
        self.assertTrue(a['actual_macro_alignment_pass'])
        self.assertTrue(a['S82_ROM_geometry_matches'])
        self.assertEqual(a['added_cycles'],2)
    def test_wc_hold_does_not_replace_ff(self):
        a=M.assess()['R_cap0']
        self.assertNotEqual(a['FF_hold_WNS_ps'],a['ORFS_reported_hold_WNS_ps'])
        self.assertTrue(a['separate_FF_check_is_authoritative_for_FF'])
    def test_live_and_historical_not_qualification(self):
        a=M.assess()
        self.assertEqual(a['R_cap1']['launcher_pid'],292373)
        self.assertIsNone(a['R_cap1']['terminal_verdict'])
        self.assertFalse(a['BF']['historical_failure_is_current_S82_verdict'])
        self.assertFalse(a['adoption'])
    def test_strict_wns(self):
        for text in ('','OT_WNS nan\n','OT_WNS inf\n','OT_WNS -1\nOT_WNS 0\n','OT_WNS malformed\n'):
            with self.subTest(text=text),self.assertRaises(ValueError):M.sta_wns(text)
    def test_mutated_receipts_refused(self):
        for field,value in (('clock_period_ns',1.0),('clock_uncertainty_ns',0.0),('clock_uncertainty_hold_ns',0.0)):
            with tempfile.TemporaryDirectory() as t:
                root=Path(t)/'evidence';shutil.copytree(M.ROOT,root)
                p=root/'R_cap0/physical.json';d=json.loads(p.read_text());d['design'][field]=value;p.write_text(json.dumps(d))
                with self.assertRaisesRegex(ValueError,'clock policy'):M.assess(root)
    def test_missing_alignment_cannot_close(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)/'evidence';shutil.copytree(M.ROOT,root)
            (root/'R_cap0/macro_alignment_actual.log').write_text('')
            self.assertFalse(M.assess(root)['R_cap0']['actual_macro_alignment_pass'])
    def test_incomplete_sta_refused(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)/'evidence';shutil.copytree(M.ROOT,root)
            (root/'R_cap0/final_FF.rc').write_text('1\n')
            with self.assertRaisesRegex(ValueError,'STA invocation'):M.assess(root)

if __name__=='__main__':unittest.main()
