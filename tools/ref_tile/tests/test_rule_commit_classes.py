"""RULE-COMMIT CLASSES (GATE-FRICTION 2026-10-18, owner 0eg): a gate is invalidated by a tool change only when the change
is STRICTER for that tile.  Neutral (registry / 'Gate-Rule: neutral' trailer / comment-only) and relaxing commits keep
the gate; a tightening keeps it only outside its applies_to scope or when its requirement is met; unclassified code
changes keep the strict refusal and are named."""
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_gate_binding_precise import GATE, HO, SB, PreciseGateBinding  # noqa: E402
from test_relaxing_rule_allowlist import GOOD  # noqa: E402


class RuleCommitClasses(PreciseGateBinding):
    def change(self, data, message='update', entry=None):
        (self.root / GATE).write_bytes(data)
        self.git('add', '-A')
        self.git('commit', '-m', message)
        c = self.git('rev-parse', 'HEAD')
        self.git('update-ref', 'refs/remotes/origin/main', c)
        (self.daemon / GATE).write_bytes(data)
        if entry is not None:
            p = patch.dict(HO.RULE_COMMITS, {c: entry})
            p.start()
            self.stack.append(p)
        return c

    def check(self, tile=('qfd_tt_head',), clock=GOOD):
        b = json.loads(json.dumps(self.binding))
        return SB.validate(b, self.root, self.daemon, self.tip, clock=clock, tile=list(tile)) + (b,)

    def test_registry_neutral_keeps_gate_without_clock(self):
        c = self.change(b'UTIL_DENSITY = 0.65\n', entry=dict(kind='neutral', rule='util', what='WARN-only'))
        ok, why, b = self.check(clock=None)
        self.assertTrue(ok, why)
        rec = b['relaxing_rule_allowlist']
        self.assertEqual(rec['commits'], [c])
        self.assertEqual(rec['files'][0]['classes'][0]['kind'], 'neutral')

    def test_trailer_neutral_keeps_gate(self):
        self.change(b'REPORT_TEXT = "x"\n', message='lint: report text\n\nGate-Rule: neutral')
        ok, why, b = self.check()
        self.assertTrue(ok, why)
        self.assertEqual(b['relaxing_rule_allowlist']['files'][0]['classes'][0]['source'], 'trailer')

    def test_comment_only_change_is_auto_neutral(self):
        self.change(b'# lint v1\n# a longer explanation\n')
        ok, why, b = self.check(clock=None)
        self.assertTrue(ok, why)
        self.assertIn('drift tolerated', why)          # textbook_lint: the earlier LINT-TOLERANT path takes it

    def test_tightening_outside_scope_keeps_gate(self):
        self.change(b'HBM_PIN_MAX = 4\n', message='x\n\nGate-Rule: tightening applies-to=hbm_,hsm_')
        ok, why, _ = self.check(tile=('qfd_tt_head', 'ot_qfd_tt_head'))
        self.assertTrue(ok, why)

    def test_tightening_in_scope_refuses_and_names_it(self):
        c = self.change(b'HBM_PIN_MAX = 4\n', message='x\n\nGate-Rule: tightening applies-to=hbm_,hsm_')
        ok, why, _ = self.check(tile=('hbm_sfu_store',))
        self.assertFalse(ok)
        self.assertIn(f'commit {c[:9]} TIGHTENS', why)

    def test_unscoped_tightening_refuses(self):
        self.change(b'PIN_MAX = 4\n', entry=dict(kind='tightening', rule='pins', what='new FAIL'))
        ok, why, _ = self.check()
        self.assertFalse(ok)
        self.assertIn('TIGHTENS', why)

    def test_tightening_with_met_requirement_keeps_gate(self):
        self.change(b'SPREAD_MAX = 80\n', entry=dict(kind='tightening', rule='s', requires='clock_pin_spread', what='t'))
        self.assertTrue(self.check()[0])
        bad = dict(GOOD, tt_pin_spread_ps=95.0)
        self.assertFalse(self.check(clock=bad)[0])

    def test_neutral_then_unclassified_refuses(self):
        self.change(b'A = 1\n', entry=dict(kind='neutral', rule='n', what='n'))
        c = self.change(b'A = 2\n')
        ok, why, _ = self.check()
        self.assertFalse(ok)
        self.assertIn(f'commit {c[:9]} is not a relaxing-only rule change (unclassified', why)

    def test_kit_edit_is_never_classified(self):
        later = self.commit({'kit/input.v': b'module m2; endmodule\n'})
        b = json.loads(json.dumps(self.binding))
        ok, why = SB.validate(b, self.root, self.daemon, later, clock=GOOD, tile=['x'])
        self.assertFalse(ok)
        self.assertIn('kit/input.v', why)

    def test_trailer_parse_and_comment_only(self):
        t = HO.parse_rule_trailer('m\n\nGate-Rule: relaxing requires=clock_pin_spread rule=0dq\n')
        self.assertEqual((t['kind'], t['requires'], t['rule']), ('relaxing', 'clock_pin_spread', '0dq'))
        self.assertIsNone(HO.parse_rule_trailer('no trailer'))
        self.assertTrue(HO.change_is_comment_only('a.py', b'def f():\n    "doc"\n    return 1\n',
                                                  b'def f():\n    # c\n    return 1\n'))
        self.assertFalse(HO.change_is_comment_only('a.py', b'X = 1\n', b'X = 2\n'))
        self.assertTrue(HO.change_is_comment_only('a.tcl', b'set a 1\n', b'# c\nset a 1  \n\n'))
        self.assertFalse(HO.change_is_comment_only('a.tcl', b'set a 1\n', b'set a 2\n'))
        self.assertFalse(HO.change_is_comment_only('a.v', b'x', b'y'))


del PreciseGateBinding

if __name__ == '__main__':
    unittest.main()
