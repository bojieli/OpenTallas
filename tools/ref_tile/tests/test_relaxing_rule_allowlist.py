"""RELAXING-ONLY RULE ALLOWLIST (ROOT-0040 2026-10-18, owner 10-17 "rules must never delay closure"): a gate executed
with an older overlay stays valid when every commit that changed the file since is an allowlisted relaxing rule change
(0dq: clock FAIL -> WARN), provided the gate report meets the relaxed rule (TT pin-flop spread <= 80 ps; FF when
reported).  A non-allowlisted commit on the chain, or a spread > 80, keeps the strict refusal."""
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_gate_binding_precise import GATE, HO, PG, SB, PreciseGateBinding  # noqa: E402

GOOD = {'max_root_sinks': 9398, 'tt_insertion_ps': 364.5, 'tt_spread_ps': 86.6, 'measured_clock': 'c0', 'root': 'port:ck',
        'clock_measurements': [{'source': 'ck', 'clock': 'c0',
                                'tt': {'boundary': {'n': 10, 'min': 280.2, 'max': 326.3},
                                       'all': {'n': 99, 'min': 277.9, 'max': 364.5}}}]}


class RelaxingRuleAllowlist(PreciseGateBinding):
    def relax(self, data=b'CLK_INSERTION_FAILS = False  # 0dq relaxed\n'):
        self.sync_daemon(GATE, data)
        c = self.git('rev-parse', 'HEAD')
        p = patch.dict(HO.RELAXING_RULE_COMMITS, {c: dict(rule='0dq', requires='clock_pin_spread', what='test')})
        p.start()
        self.stack.append(p)
        return c

    def test_allowlisted_commit_keeps_gate_and_records_it(self):
        c = self.relax()
        b = json.loads(json.dumps(self.binding))
        ok, why = SB.validate(b, self.root, self.daemon, self.tip, clock=GOOD)
        self.assertTrue(ok, why)
        self.assertIn('RELAXING-RULE ALLOWLIST used', why)
        rec = b['relaxing_rule_allowlist']
        self.assertEqual(rec['commits'], [c])
        self.assertTrue(rec['requirements'][0]['ok'])
        self.assertEqual(rec['requirements'][0]['tt'], [46.1, 'pin-flop'])
        self.assertTrue(rec['requirements'][0]['ff_left_to_routed_audit'])

    def test_without_clock_record_strict(self):
        self.relax()
        ok, why = SB.validate(self.binding, self.root, self.daemon, self.tip)
        self.assertFalse(ok)
        self.assertIn(GATE, why)

    def test_spread_over_80_refuses(self):
        self.relax()
        bad = dict(GOOD, clock_measurements=[{'source': 'ck', 'clock': 'c0', 'tt': {'boundary': {'min': 200, 'max': 290.5}}}])
        ok, why = SB.validate(json.loads(json.dumps(self.binding)), self.root, self.daemon, self.tip, clock=bad)
        self.assertFalse(ok)
        self.assertIn('allowlist not applicable', why)

    def test_ff_reported_over_80_refuses(self):
        self.relax()
        bad = dict(GOOD, ff_pin_spread_ps=95.0, tt_pin_spread_ps=40.0)
        ok, why = SB.validate(json.loads(json.dumps(self.binding)), self.root, self.daemon, self.tip, clock=bad)
        self.assertFalse(ok)

    def test_non_allowlisted_commit_on_chain_refuses(self):
        self.relax()
        self.sync_daemon(GATE, b'PIN_LAUNCH_MAX_PS = 230.0\n')       # a tightening after the relaxing commit
        ok, why = SB.validate(json.loads(json.dumps(self.binding)), self.root, self.daemon, self.tip, clock=GOOD)
        self.assertFalse(ok)
        self.assertIn('not a relaxing-only rule change', why)

    def test_submit_check_records_and_route_runs_current_helpers(self):
        self.relax()
        (self.root / 'kit/gate_result.json').write_text(json.dumps({'source_binding': self.binding, 'clock': GOOD}))
        g = PG.Gate()
        PG.check_clock_evidence(g, self.root / 'kit', source_commit=self.tip)
        self.assertNotIn('FAIL', [i['severity'] for i in g.items], g.items)
        self.assertTrue(getattr(g, 'relaxing_rule_allowlist', None))
        self.assertEqual(g.route_overlay_plan['scope'], 'gate_executed_overlays_verified_relaxing_rule_allowlist_current')
        ok, why = HO.compare_plans(g.route_overlay_plan, HO.capture_plan(self.daemon, self.root)[0])
        self.assertTrue(ok, why)                                     # the route ships today's (relaxed) helpers
        self.assertEqual(g.clock['level'], 'WARN')                   # old record judged on its pin-flop spread (46.1)

    def test_bench_only_spec_change(self):
        a = json.dumps({'top': 't', 'job': {'benches': ['a', 'b']}, 'stages': {}})
        b = json.dumps({'top': 't', 'job': {'benches': ['a']}, 'stages': {}})
        self.assertTrue(SB.spec_change_is_bench_only(a, b))
        self.assertFalse(SB.spec_change_is_bench_only(a, b.replace('"t"', '"u"')))
        j1 = json.dumps({'stages': {'bench': [1, 2], 'route': 1}})
        j2 = json.dumps({'stages': {'bench': [1], 'route': 1}})
        self.assertTrue(SB.spec_change_is_bench_only(j1, j2))
        self.assertFalse(SB.spec_change_is_bench_only(j1, j2.replace('"route": 1', '"route": 2')))


del PreciseGateBinding

if __name__ == '__main__':
    unittest.main()
