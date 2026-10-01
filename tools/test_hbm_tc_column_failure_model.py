"""Qualification guards for the standalone failure prerequisite; no RTL tests."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import hbm_tc_column_failure_model as M


class FailurePrerequisite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = M.model()

    def test_failed_source_and_no_transfer(self):
        d=self.evidence
        self.assertEqual(d['failure_unchanged']['engineering_verdict'],'FAIL')
        self.assertLess(d['failure_unchanged']['SS_setup_wns_ps'],0)
        self.assertLess(d['failure_unchanged']['FF_hold_wns_ps'],0)
        self.assertEqual(set(d['main_source_differences']['paths']),{'rtl/gpu/ot_gpu_tc_col.sv','rtl/gpu/ot_gpu_fadd.sv'})
        self.assertFalse(d['no_admission']['hardware_admission'])
        self.assertIsNone(d['calendar_composition']['complete_token_delta_ns'])

    def test_rejects_record_that_relabels_fail_pass(self):
        original=Path.read_bytes
        def read(path):
            b=original(path)
            if str(path).endswith(M.TERM+'/receipt.json'):
                return b.replace(b'"engineering_verdict": "FAIL"',b'"engineering_verdict": "PASS"')
            return b
        with patch.object(Path,'read_bytes',read):
            with self.assertRaisesRegex(ValueError,'base pin changed'):
                M.model()

    def test_calendar_replication_and_latency_accounting(self):
        d=self.evidence
        for name,old,reps in [('qwen',49,64),('deepseek_v41',42,32)]:
            c=d['configurations'][name]
            self.assertEqual(c['old_column_cycles'],old)
            self.assertEqual(c['proposed_column_cycles'],old+1)
            self.assertEqual(c['columns_per_SM'],reps)
            self.assertEqual(c['columns_per_candidate_die'],32*reps)
            self.assertEqual(c['IL'],c['ALAT']+d['successor']['alignment']['feedback_FB'])
        self.assertEqual(len(d['calendar_composition']['qwen']['events']),434)
        self.assertEqual(len(d['calendar_composition']['deepseek_v41']['events']),93)
        self.assertEqual(d['failure_unchanged']['output_over_budget'],['fault','ov'])
        self.assertEqual(d['successor']['alignment']['first_acc_reset_tap'],'archived combinational acc_in: fl[5] -> fl[6]')

    def test_saved_evidence_reproduces(self):
        p=M.ROOT/'results/uarch/hbm_tc_column_failure_prerequisite_20261001/model.json'
        self.assertEqual(json.loads(p.read_text()),self.evidence)


if __name__=='__main__':unittest.main()
