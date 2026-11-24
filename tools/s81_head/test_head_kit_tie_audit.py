#!/usr/bin/env python3
"""kit_rtl.tie_audit: only a PASS audit that records the kit plan's sha256 is named (HEAD count-strap evidence)."""
import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / 'die_plan')]
import count_strap_evidence as E  # noqa: E402
import head_wave_kit_rtl as K  # noqa: E402

LITS = [['lep0N_w.strap_ca_k_coll_i0', "6'b001100"]]


class TieAudit(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory(); self.addCleanup(t.cleanup)
        self.d = Path(t.name); self.out = self.d / 'out'; self.out.mkdir()
        self.plan = self.d / 'source_plan.json'; self.plan.write_text('{"a": 1}')
        self.sha = hashlib.sha256(self.plan.read_bytes()).hexdigest()
        self.audit = self.d / 'bind_of_record' / 'tie_audit.json'; self.audit.parent.mkdir()
        e = mock.patch.dict(os.environ); e.start(); self.addCleanup(e.stop); os.environ.pop('OT_BIND_TIE_AUDIT', None)

    def put(self, path=None, **kw):
        doc = dict(verdict='PASS', rows=1, accepted=LITS, rejected=[], plan_sha256=self.sha); doc.update(kw)
        (path or self.audit).write_text(json.dumps({k: v for k, v in doc.items() if v is not None}))

    def test_bind_of_record_named_copied_and_found(self):
        self.put(); r = K.tie_audit_record(self.plan, self.out)
        self.assertEqual(r['tie_audit_plan_sha256'], self.sha)
        kr = self.out / 'kit_rtl.json'; kr.write_text(json.dumps(r))
        self.assertEqual(E.find_audit(kr, r), self.out / 'tie_audit.json')
        self.assertEqual(r['tie_audit_sha256'], hashlib.sha256(self.audit.read_bytes()).hexdigest())

    def test_env_wins(self):
        self.put(verdict='FAIL'); other = self.d / 'x.json'; self.put(other); os.environ['OT_BIND_TIE_AUDIT'] = str(other)
        self.assertEqual(K.tie_audit_record(self.plan, self.out)['tie_audit_source'], str(other))

    def test_none(self):
        self.assertEqual(K.tie_audit_record(self.plan, self.out), {})

    def test_no_plan_sha_is_not_named(self):
        self.put(plan_sha256=None); self.assertEqual(K.tie_audit_record(self.plan, self.out), {})

    def test_other_plan_fail_and_missing_env_refused(self):
        self.put(plan_sha256='0' * 64); self.assertRaises(ValueError, K.tie_audit_record, self.plan, self.out)
        self.put(verdict='FAIL'); self.assertRaises(ValueError, K.tie_audit_record, self.plan, self.out)
        os.environ['OT_BIND_TIE_AUDIT'] = str(self.d / 'gone.json'); self.assertRaises(ValueError, K.tie_audit_record, self.plan, self.out)


if __name__ == '__main__':
    unittest.main()
