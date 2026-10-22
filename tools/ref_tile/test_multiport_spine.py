"""Physical multiport spines retain the canonical domain and timing wrappers."""
import copy
import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
import ref_tile as R


def model():
    return dict(name='two_root', top='two_root', sources=[], kind='tile',
                clock='multiple_cts_roots', clock_port='ck', clock_ports=['ck', 'ckv[0]'],
                clock_data_paths='related_same_frequency',
                clock_relationship={'kind': 'same_pll_fixed_phase', 'ratio': [1, 1], 'phase_ps': 0},
                clock_entry_domains={
                    'core': {'ratio': [1, 1], 'ports': ['ck'], 'inputs': ['i'], 'outputs': ['o']},
                    'other': {'ratio': [1, 1], 'ports': ['ckv[0]'], 'inputs': [], 'outputs': []}},
                pins={'S': ['i'], 'N': ['o'], 'W': ['ck', 'ckv']},
                macros=[], children=[], route={}, reset_ports=[], inter=[])


class MultiportSpine(unittest.TestCase):
    def test_physical_builder_is_inside_root_validation_and_boundary_wrappers(self):
        old = model(); new = dict(old, clock_distribution='spine')
        before = R.gen_hooks(old, 'k'); after = R.gen_hooks(new, 'k')
        hook = after['pre_cts.tcl']
        self.assertLess(hook.index('source /src/physical/common_flow/clock_spine.tcl'),
                        hook.index('source /src/physical/common_flow/clock_entries.tcl'))
        self.assertLess(hook.index('source /src/physical/common_flow/clock_entries.tcl'),
                        hook.index('rename clock_tree_synthesis ::ot_ref_cts_boundary_orig'))
        self.assertIn('set ::env(OT_SPINE_PORTS) {ck,ckv[0]}', hook)
        self.assertIn('set ::env(OT_SPINE_CTS_REST) 0', hook)
        self.assertEqual(before['clock_entry.sdc'], after['clock_entry.sdc'])
        self.assertEqual(R.gen_sdc(old, 770), R.gen_sdc(new, 770))
        for f in before.keys() - {'pre_cts.tcl'}:
            self.assertEqual(before[f], after[f], f)
        self.assertNotIn('clock_spine.tcl', before['pre_cts.tcl'])
        self.assertIn('physical/common_flow/clock_spine.tcl', R.referenced_paths(new, 'k'))

    def test_only_explicit_supported_leaf_topology(self):
        self.assertFalse(R.multiport_spine(model()))
        for change in ({'clock_distribution': 'arbitrary'}, {'clock': 'entries'}, {'kind': 'unsupported'}):
            s = dict(model(), clock_distribution='spine'); s.update(change)
            with self.assertRaises(R.SpecError): R.multiport_spine(s)

    def test_cluster_targets_real_child_insertion_inside_domain_wrappers(self):
        old = dict(model(), kind='cluster')
        new = dict(old, clock_distribution='spine', child_clock_ref='boundary')
        # Isolate physical hook generation; landed-record validity is exercised
        # by the existing landed-cluster contract tests and the real kit gen.
        entry_sdc = R.ce_generate(model())
        with patch.object(R, 'child_insertions', return_value={'encoder': 286.4}), \
             patch.object(R, 'ce_generate', return_value=entry_sdc), \
             patch.object(R.clock_entry_constraints, 'landed_cluster', return_value=False):
            after = R.gen_hooks(new, 'k')
            before = R.gen_hooks(old, 'k')
            refs = R.referenced_paths(new, 'k')
        hook = after['pre_cts.tcl']
        self.assertLess(hook.index('clock_spine.tcl'), hook.index('spine_ins.tcl'))
        self.assertLess(hook.index('spine_ins.tcl'), hook.index('clock_entries.tcl'))
        self.assertIn('OT_SPINE_MACRO_PIN_LEAF) 1', hook)
        self.assertIn('dict create encoder 286.4', after['spine_ins.tcl'])
        self.assertIn('set x [expr {$x + [dict get $::ot_ref_child_ins $m]}]', after['spine_ins.tcl'])
        self.assertEqual(before['clock_entry.sdc'], after['clock_entry.sdc'])
        self.assertIn('k/spine_ins.tcl', refs)

    def test_custom_timing_hooks_still_refused(self):
        for field in ('sdc_extra', 'boundary_tcl', 'pre_cts_extra', 'forwarded_clock'):
            s = dict(model(), clock_distribution='spine'); s[field] = ['custom.tcl']
            with tempfile.NamedTemporaryFile('w', suffix='.json') as f:
                json.dump(s, f); f.flush()
                with self.assertRaisesRegex(R.SpecError, 'custom timing/clock hooks'):
                    R.load_spec(f.name)


if __name__ == '__main__': unittest.main()
