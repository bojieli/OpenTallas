"""Minimum registry reconciliation fixtures; no threads, SSH, or physical jobs."""
import json
import pathlib
import tempfile
import unittest

from elements import Elements, change_key, qualification_text, ts


class Describer:
    def get(self, *args): return ''
    def save(self): pass


class RegistryTest(unittest.TestCase):
    def test_unrouted_history_and_failed_physical_remain_distinct(self):
        self.assertGreater(ts('2026-10-09T08:06:00Z'), 0)
        self.assertEqual(ts('2026-10-09T08:06:00Z'), ts('2026-10-09T08:06:00+00:00'))
        with tempfile.TemporaryDirectory() as td:
            model = Elements.__new__(Elements)
            model.repo = pathlib.Path(td)
            model.desc = Describer(); model.area = {}
            model.revoked_path = model.repo / 'revoked'; model.superseded_path = model.repo / 'superseded'
            model.option_b = lambda: ({}, {})
            model.revoked_jobs = lambda: {}
            model.superseded = lambda: {}
            job = Elements.reduce(dict(name='route_failed', status='NEEDS_RTL',
                spec=dict(block='ot_hbm_test'), metrics=dict(setup_corner='tt', ss_ps=-12, ff_ps=3, drc=0)))
            model.jobs = lambda: []
            registry = model.repo / 'results/fleet_viz/element_registry'
            registry.mkdir(parents=True)
            row = dict(element='ot_hbm_test', target='HBM accelerator', owner='test',
                       source=dict(commit='97740d865', paths=['rtl/example.sv']),
                       exactness=dict(positive=dict(status='PASS'), negative=dict(status='PASS')),
                       physical=dict(status='pending'))
            (registry / 'a.json').write_text(json.dumps(dict(schema_version=1, records=[row])))
            first = model.compute(); r = first['rows'][0]
            self.assertEqual(r['category'], 'implementation recorded (no physical job)')
            self.assertIsNone(r['best']['tt'])
            self.assertEqual(r['jobs'], 0)
            row = dict(row, recorded_at='2026-10-09T01:00:00Z', integration=dict(status='pending'))
            (registry / 'b.json').write_text(json.dumps(dict(schema_version=1, records=[row])))
            second = model.compute()
            self.assertEqual(len(second['rows'][0]['evidence_history']), 2)
            self.assertNotEqual(change_key(first), change_key(second))
            self.assertIn('integration pending', qualification_text(second['rows'][0]['qualification']))
            model.jobs = lambda: [job]
            routed = model.compute()['rows'][0]
            self.assertEqual(routed['category'], 'needs redesign (no live job)')
            self.assertEqual(routed['best']['tt'], -12)
            self.assertEqual(routed['failed'], 1)
            (registry / 'bad.json').write_text('{')
            self.assertEqual(len(model.compute()['sources']['registry_errors']), 1)
            (registry / 'invalid.json').write_text(json.dumps(dict(schema_version=1,
                records=[row, dict(row, dependencies=None)])))
            invalid = model.compute()
            self.assertEqual(len(invalid['sources']['registry_errors']), 2)
            self.assertEqual(len(invalid['rows'][0]['evidence_history']), 2)
            later = dict(row, recorded_at='2026-10-08T18:01:00-07:00', integration=dict(status='newer'))
            (registry / 'c.json').write_text(json.dumps(dict(schema_version=1, records=[later])))
            self.assertEqual(model.compute()['rows'][0]['qualification']['integration']['status'], 'newer')
            model.md_period = 600; model.md_path = model.repo / 'ELEMENTS.md'; model.log = print
            model.write_md(model.compute())
            self.assertIn('exact +PASS / -PASS', model.md_path.read_text())


    def test_override_variants_and_owners(self):
        with tempfile.TemporaryDirectory() as td:
            model = Elements.__new__(Elements)
            model.repo = pathlib.Path(td); model.log = print
            model.desc = Describer(); model.area = {}
            model.option_b = lambda: ({}, {}); model.revoked_jobs = lambda: {}; model.superseded = lambda: {}
            model.registry = lambda: ({}, [])
            model.overrides_path = model.repo / 'overrides.json'; model.ovk = (None, {})
            model.superseded_path = model.repo / 'superseded'; model.revoked_path = model.repo / 'revoked'
            def job(name, block, status, owner='Codex:t4'):
                return Elements.reduce(dict(name=name, status=status, spec=dict(block=block, owner=owner),
                                            metrics=dict(setup_corner='tt', ss_ps=1, ff_ps=1, drc=0)))
            jobs = [job('p', 'ot_hbm_x', 'CLOSED'), job('a', 'ot_hbm_x_wide1036', 'RUNNING'),
                    job('l0', 'hfd_tap', 'CLOSED'), job('l4', 'hfd_tap_lane4', 'RUNNING'),
                    job('k', 'qfd_k', 'NEEDS_RTL', owner='Codex:qwen-deep-queue routine')]
            model.jobs = lambda: jobs
            rows = {r['element']: r for r in model.compute()['rows']}
            self.assertEqual(len(rows), 5)   # no overrides: every block is its own element
            model.overrides_path.write_text(json.dumps(dict(
                variants={'ot_hbm_x_wide1036': dict(of='ot_hbm_x'), 'hfd_tap_lane4': dict(of='hfd_tap', kind='instance')},
                owner_map={'Codex:qwen-deep-queue': 'Claude:qwen-1010', 'Codex:qwen': 'Claude:wrong'},
                owners={'hfd_tap': 'Claude:hgi-1010'})))
            rows = {r['element']: r for r in model.compute()['rows']}
            self.assertEqual(sorted(rows), ['hfd_tap', 'ot_hbm_x', 'qfd_k'])
            self.assertEqual(rows['ot_hbm_x']['variants'], ['ot_hbm_x_wide1036'])
            self.assertTrue(rows['ot_hbm_x']['category'].startswith('closed'))   # alternative: any closure closes
            self.assertEqual(rows['hfd_tap']['category'], 'first trial in flight')  # instance lane4 still open
            self.assertIn('hfd_tap_lane4', rows['hfd_tap']['via'])
            self.assertEqual(rows['hfd_tap']['owner'], 'Claude:hgi-1010')
            self.assertEqual(rows['hfd_tap']['owner_orig'], 'Codex:t4')
            self.assertEqual(rows['qfd_k']['owner'], 'Claude:qwen-1010')   # longest prefix, word boundary
            self.assertEqual(Elements.remap_owner('Codex:qwen-elements', dict(owner_map={'Codex:qwen': 'X'})),
                             'Codex:qwen-elements')
            jobs[2] = job('l0', 'hfd_tap', 'RUNNING'); jobs[3] = job('l4', 'hfd_tap_lane4', 'CLOSED')
            rows = {r['element']: r for r in model.compute()['rows']}
            self.assertEqual(rows['hfd_tap']['category'], 'first trial in flight')   # the master instance is required too
            jobs[2] = job('l0', 'hfd_tap', 'CLOSED')
            model.superseded = lambda: {'ot_hbm_x': dict(by='ot_hbm_x_wide1036', reason='t')}
            rows = {r['element']: r for r in model.compute()['rows']}
            self.assertEqual(rows['ot_hbm_x_wide1036']['category'], 'first trial in flight')   # unfolded, still open
            model.superseded = lambda: {}
            rows = {r['element']: r for r in model.compute()['rows']}
            self.assertTrue(rows['hfd_tap']['category'].startswith('closed'))   # every instance closed


class SupersededInstanceFoldTest(unittest.TestCase):
    def test_instance_fold_into_superseded_parent_does_not_break_compute(self):
        """fill-9 2026-10-10: an 'instance' fold whose parent is superseded froze /api/elements (KeyError)."""
        with tempfile.TemporaryDirectory() as td:
            model = Elements.__new__(Elements)
            model.repo = pathlib.Path(td)
            model.desc = Describer(); model.area = {}
            model.option_b = lambda: ({}, {})
            model.revoked_jobs = lambda: {}
            model.superseded = lambda: {'parent_elem': dict(by='child_blk', reason='adopted')}
            model.overrides = lambda: dict(variants={'child_blk': dict(of='parent_elem', kind='instance')},
                                           owner_map={}, owners={})
            model.overrides_path = model.repo / 'overrides'
            model.revoked_path = model.repo / 'revoked'; model.superseded_path = model.repo / 'superseded'
            model.jobs = lambda: [Elements.reduce(dict(name='child_blk-0123456789-tc', status='CLOSED',
                spec=dict(block='child_blk'), metrics=dict(setup_corner='tt', ss_ps=5, ff_ps=3, drc=0)))]
            rows = {r['element']: r for r in model.compute()['rows']}
            self.assertIn('child_blk', rows)


class ThroughputGateTest(unittest.TestCase):
    def test_closed_timing_is_not_throughput_qualified(self):
        """AGENTS.md throughput qualification (owner 2026-10-10): closure alone never qualifies a unit."""
        with tempfile.TemporaryDirectory() as td:
            model = Elements.__new__(Elements)
            model.repo = pathlib.Path(td); model.log = lambda *a: None; model.tpk = (None, {})
            model.desc = Describer(); model.area = {}
            model.option_b = lambda: ({}, {})
            model.revoked_jobs = lambda: {}
            model.superseded = lambda: {}
            model.revoked_path = model.repo / 'revoked'; model.superseded_path = model.repo / 'superseded'
            model.jobs = lambda: [Elements.reduce(dict(name='ot_hgi_hc_unit-0123456789-tc', status='CLOSED',
                spec=dict(block='ot_hgi_hc_unit'), metrics=dict(setup_corner='tt', ss_ps=5, ff_ps=3, drc=0)))]
            row = lambda: {r['element']: r for r in model.compute()['rows']}['ot_hgi_hc_unit']
            self.assertEqual(row()['gate'], 'CLOSED-TIMING, NO-THROUGHPUT-BUDGET-ROW')
            b = model.repo / 'results/arch/throughput_budget_20261010'; b.mkdir(parents=True)
            ent = lambda st, ratio: dict(status=st, ratio=ratio, limiting=dict(op='HC.HC_MIX_ROWS', model='DS', owner='d'))
            (b / 'budget.json').write_text(json.dumps(dict(qualify_ratio=1.1, elements=dict(ot_hgi_hc_unit=ent('UNQUALIFIED', 125.2)))))
            r = row()
            self.assertEqual(r['gate'], 'CLOSED-TIMING, THROUGHPUT-UNQUALIFIED')
            self.assertEqual(r['throughput']['ratio'], 125.2)
            import os, time
            (b / 'budget.json').write_text(json.dumps(dict(qualify_ratio=1.1, elements=dict(ot_hgi_hc_unit=ent('QUALIFIED', 1.04)))))
            os.utime(b / 'budget.json', (time.time() + 5, time.time() + 5))
            self.assertEqual(row()['gate'], 'CLOSED-TIMING, THROUGHPUT-QUALIFIED')
            self.assertEqual(model.compute()['throughput_summary']['HBM accelerator'], {'QUALIFIED': 1})


if __name__ == '__main__': unittest.main()
