"""Calibration controls reject absent/changed witnesses and retired exact selector law."""
import copy
import hashlib
import unittest
from pathlib import Path
from qwen_b2_join.phase_protocol import validate_temporal_controls
from qwen_b2_join.allocator_ledger import derive

ROOT = Path(__file__).resolve().parents[2]
LOGS = ROOT / 'results/arch/qwen_split_compute_1014/b2_full_graph_1016/lane_cov/v2'


def record(name):
    p = LOGS / name
    return dict(path=str(p), sha256=hashlib.sha256(p.read_bytes()).hexdigest())


def checked(rec):
    p = Path(rec['path'])
    if hashlib.sha256(p.read_bytes()).hexdigest() != rec['sha256']:
        raise ValueError('changed witness')
    return p


class Controls(unittest.TestCase):
    def setUp(self):
        # These are historical BASELINE logs: testing a consumer never promotes
        # them to actual-age calibration or supplies the other manifest fields.
        self.a = dict(selector_window=dict(min=0, max=7, edge_pass_log=record('sel7.log'), edge_fail_log=record('sel8.log')),
                      temporal_gate=dict(exact_phase_mutants={n: dict(delta=1, exit_code=134, log=record('neg_'+n+'1.log')) for n in ('tc', 'am', 'hl')}))

    def test_real_baseline_witness_format(self):
        validate_temporal_controls(self.a, checked)

    def test_missing_false_or_changed_controls_refused(self):
        for name in ('tc', 'am', 'hl'):
            for key, value in [('delta', 0), ('exit_code', 0), ('log', record('sel7.log'))]:
                a = copy.deepcopy(self.a)
                a['temporal_gate']['exact_phase_mutants'][name][key] = value
                with self.assertRaises(ValueError):
                    validate_temporal_controls(a, checked)
        for field, value in [('min', 1), ('max', 8), ('max', True), ('edge_fail_log', record('sel7.log'))]:
            a = copy.deepcopy(self.a)
            a['selector_window'][field] = value
            with self.assertRaises(ValueError):
                validate_temporal_controls(a, checked)
        a = copy.deepcopy(self.a)
        a['selector_window']['edge_pass_log']['sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            validate_temporal_controls(a, checked)

    def test_selector_window_replaces_exact_equality(self):
        halves = {}
        for h in range(6):
            keys = ('tc_to_port', 'am_to_controller', 'rq_to_train', 'lc_to_halfband', 'rb_to_vm', 'issuer_to_train',
                    'tag_copy_to_issuer', 'me_copy_to_issuer', 'tw_port_to_halfband', 'ty_halfband_to_port')
            halves[h] = {k: dict(edges=0) for k in keys}
            halves[h]['pword_forward'] = dict(edges=0, min_edges=0)
        for age in (0, 2, 3, 7):
            _, issues = derive(halves, [dict(edges=age)] * 8, [dict(edges=0)] * 8, None)
            self.assertEqual(issues, [])
        _, issues = derive(halves, [dict(edges=8)] * 8, [dict(edges=0)] * 8, None)
        self.assertTrue(any('outside measured 0..7' in s for s in issues))


if __name__ == '__main__':
    unittest.main()
