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

    def check(self, tile=('qfd_tt_head',), clock=GOOD, gate=None):
        b = json.loads(json.dumps(self.binding))
        return SB.validate(b, self.root, self.daemon, self.tip, clock=clock, tile=list(tile), gate=gate) + (b,)

    def test_trial_grt_every_kit_keeps_older_gates(self):
        """ROOT-0330-GRT 10-18: 'Gate-Rule: tightening requires=trial_grt' (the trial GRT now runs for every kit).  A
        gate result that predates it (no trial_route record) stays valid; a newer gate that ran the trial is judged by
        its overflow; without the gate result the strict refusal stands."""
        self.change(b'TRIAL_EVERY_KIT = 1\n',
                    message='gate: trial GRT for every kit\n\nGate-Rule: tightening requires=trial_grt rule=trial-grt-every-kit')
        old_gate = {'clock': GOOD, 'verdict': 'PASS', 'items': []}
        ok, why, b = self.check(gate=old_gate)
        self.assertTrue(ok, why)
        req = b['relaxing_rule_allowlist']['requirements']
        self.assertEqual([r['requires'] for r in req], ['trial_grt'])
        self.assertTrue(req[0]['predates'])
        ok, why, _ = self.check(gate=dict(old_gate, trial_route={'overflow': 0}))
        self.assertTrue(ok, why)
        ok, why, _ = self.check(gate=dict(old_gate, trial_route={'overflow': 7}))
        self.assertFalse(ok)
        self.assertIn('trial GRT overflow 7', why)
        self.assertFalse(self.check(gate=None)[0])

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


class MergedRuleSpan(unittest.TestCase):
    """ROOT-0330: a file changed on two branches and merged is classified commit by commit (commit-set walk); a merge
    that adds its own change, and an entry scoped to other paths, keep the strict refusal."""

    def setUp(self):
        import subprocess
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.sp = subprocess
        self.git('init', '-q', '-b', 'main')
        self.git('config', 'user.email', 't@t')
        self.git('config', 'user.name', 't')
        self.base = self.put(b'a = 1\nb = 2\nc = 3\nd = 4\ne = 5\n', 'base')

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *a):
        return self.sp.run(['git', '-C', str(self.root), *a], check=True, capture_output=True, text=True).stdout.strip()

    def put(self, data, msg):
        (self.root / 'f.py').write_bytes(data)
        self.git('add', 'f.py')
        self.git('commit', '-q', '-m', msg)
        return self.git('rev-parse', 'HEAD')

    def blob(self, rev):
        return self.git('rev-parse', f'{rev}:f.py')

    def branches(self, merge_extra=b''):
        self.git('checkout', '-q', '-b', 'x')
        ca = self.put(b'a = 10\nb = 2\nc = 3\nd = 4\ne = 5\n', 'side a')
        self.git('checkout', '-q', 'main')
        cb = self.put(b'a = 1\nb = 2\nc = 3\nd = 4\ne = 50\n', 'side b')
        self.git('merge', '-q', '--no-ff', '--no-commit', 'x')
        if merge_extra:
            (self.root / 'f.py').write_bytes(b'a = 10\nb = 2\nc = 3\nd = 4\ne = 50\n' + merge_extra)
            self.git('add', 'f.py')
        self.git('commit', '-q', '-m', 'merge')
        return ca, cb, self.git('rev-parse', 'HEAD')

    def span(self, old, reg):
        return HO.rule_span(self.root, 'f.py', old, self.blob('HEAD'), ['HEAD'], registry=reg)

    def test_clean_merge_of_two_classified_branches_keeps_gate(self):
        ca, cb, _ = self.branches()
        reg = {ca: dict(kind='neutral', rule='n', what='n'), cb: dict(kind='relaxing', rule='r', what='r')}
        ok, rows, why = self.span(self.blob(self.base), reg)
        self.assertTrue(ok, why)
        self.assertEqual(sorted(r['commit'] for r in rows), sorted([ca, cb]))
        ok, rows, _ = self.span(self.blob(ca), reg)          # gate taken on side a: only side b is new
        self.assertTrue(ok)
        self.assertEqual([r['commit'] for r in rows], [cb])

    def test_unclassified_side_refuses(self):
        ca, cb, _ = self.branches()
        ok, _, why = self.span(self.blob(self.base), {ca: dict(kind='neutral', rule='n', what='n')})
        self.assertFalse(ok)
        self.assertIn(f'commit {cb[:9]}', why)

    def test_merge_with_its_own_change_refuses(self):
        ca, cb, m = self.branches(merge_extra=b'f = 6\n')
        reg = {ca: dict(kind='neutral', rule='n', what='n'), cb: dict(kind='neutral', rule='n', what='n')}
        ok, _, why = self.span(self.blob(self.base), reg)
        self.assertFalse(ok)
        self.assertIn(f'merge {m[:9]} is not a clean merge', why)

    def test_path_scoped_entry_does_not_cover_other_files(self):
        ca, cb, _ = self.branches()
        reg = {ca: dict(kind='neutral', rule='n', what='n'),
               cb: dict(kind='neutral', rule='n', what='n', paths=('other.py',))}
        ok, _, why = self.span(self.blob(self.base), reg)
        self.assertFalse(ok)
        self.assertIn(f'commit {cb[:9]}', why)

    def test_kv_die_entries_are_path_scoped(self):
        for c in ('76f68cefa8ae97296b8c1f07eab9801c47aaac70', '8a83ec822056192aa6c6c49940974ebe062e734b'):
            e = HO.RULE_COMMITS[c]
            self.assertEqual(e['kind'], 'neutral')
            self.assertIn('tools/qwen_kv_die/kv_die.py', e['paths'])
            self.assertNotIn('tools/qwen_kv_die/pv_trunk_gen.py', e['paths'])


del PreciseGateBinding

if __name__ == '__main__':
    unittest.main()
