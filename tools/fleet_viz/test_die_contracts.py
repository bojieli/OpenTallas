"""Top-down die-contract registry (registry-sync 2026-10-15): not-started contract masters are OPEN, retired and
out-of-contract rows are superseded with the contract as evidence, closed/live out-of-contract rows are kept."""
import json, pathlib, tempfile, unittest

import die_contracts
from elements import Elements, NOT_STARTED


class Describer:
    def get(self, *a): return ''
    def save(self): pass
    def info(self, *a): return {}


class Flow:
    def annotate(self, *a): return {}


def job(name, block, status):
    return Elements.reduce(dict(name=name, status=status, spec=dict(block=block),
                                metrics=dict(setup_corner='tt', ss_ps=5, ff_ps=3, drc=0) if status == 'CLOSED' else {}))


class DieContractTest(unittest.TestCase):
    def test_top_down(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            (root / 'results/fleet_viz').mkdir(parents=True)
            (root / 'bind.json').write_text(json.dumps(dict(masters={
                'qfd_new_static': dict(verdict='FAIL', kind='real'), 'qfd_done': dict(verdict='PASS', kind='real'),
                'qfd_phy': dict(verdict='PASS', kind='model')})))
            (root / die_contracts.CONFIG).write_text(json.dumps(dict(designs=[dict(
                design='qc', label='Qwen compute die', target='Qwen ROM', revision='C99', lead='Q-COMPUTE-DIE', complete=True,
                sources=[dict(kind='port_bind', path='bind.json')],
                add=[dict(element='qfd_leaf', parent='qfd_new_static', role='leaf')],
                retire=[dict(elements=['qfd_old'], by='qfd_new_static', evidence='log 10-15')],
                streams=[['^qfd_new', 'Q-LINK']])])))
            m = Elements.__new__(Elements)
            m.repo = root; m.flow = Flow(); m.desc = Describer(); m.area = {}; m.log = lambda *a: None
            m.revoked_path = root / 'r'; m.superseded_path = root / 's'
            m.option_b = lambda: ({}, {}); m.revoked_jobs = lambda: {}; m.superseded = lambda: {}
            m.contracts = die_contracts.Contracts(root, log=lambda *a: None)
            m.jobs = lambda: [job('a', 'qfd_done', 'CLOSED'), job('b', 'qfd_old', 'CLOSED'), job('c', 'qfd_stale', 'NEEDS_RTL'),
                              job('d', 'qfd_legacy_closed', 'CLOSED'), job('e', 'qfd_live', 'RUNNING')]
            d = m.compute(); rows = {r['element']: r for r in d['rows']}
            self.assertEqual(rows['qfd_new_static']['category'], NOT_STARTED)
            self.assertEqual(rows['qfd_new_static']['owner_stream'], 'Q-LINK')
            self.assertEqual(rows['qfd_new_static']['native'][0]['verdict'], 'FAIL')
            self.assertEqual(rows['qfd_leaf']['category'], NOT_STARTED)
            self.assertNotIn('qfd_phy', rows)                       # hard PHY model: not an element to close
            self.assertTrue(rows['qfd_done']['category'].startswith('closed'))
            self.assertEqual(rows['qfd_old']['category'], 'superseded')
            self.assertIn('C99', json.dumps(rows['qfd_old']['superseded']['source_evidence']))
            self.assertEqual(rows['qfd_stale']['category'], 'superseded')   # failed, no live job, in no contract
            self.assertTrue(rows['qfd_legacy_closed']['category'].startswith('closed'))
            self.assertTrue(rows['qfd_legacy_closed']['contract'].startswith('not linked'))
            self.assertEqual(rows['qfd_live']['category'], 'first trial in flight')
            s = d['designs']['qc']
            self.assertEqual((s['closed'], s['not_started'], s['open']), (1, 2, 2))
            self.assertIn(NOT_STARTED, d['summary']['Qwen ROM'])


if __name__ == '__main__':
    unittest.main()
