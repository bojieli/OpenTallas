"""Input-boundary tests: conservation, exact format separation, no silent unknowns."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from hbrom_inputs import DEFAULT_INPUT_DIR, build_inputs, normalize_dag, normalize_storage


class InputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs=build_inputs()

    def test_source_census_and_scope_conservation(self):
        x=self.inputs;s=x['storage_scopes']
        self.assertEqual(s['mandatory_ar_bytes'],501382611408)
        self.assertEqual(s['optional_mtp_bytes'],7932874632)
        self.assertEqual(s['optional_vision_bytes'],970536960)
        self.assertEqual(sum(s[k] for k in ('mandatory_ar_bytes','optional_mtp_bytes','optional_vision_bytes')),510286023000)
        resident=sum(t['source_bytes'] for t in x['tensors'])+s['auxiliary_source_bytes']
        self.assertEqual(resident,x['full_checkpoint_bytes'])
        self.assertEqual(s['execution_duplicate_bytes'],2684354560)
        self.assertFalse(any(t['name'].endswith(':execution_scale') for t in x['tensors']))
        self.assertGreater(x['auxiliary_storage_bytes'],s['auxiliary_source_bytes'])

    def test_mixed_down_retains_formats_and_all_experts(self):
        parts=[n for n in self.inputs['dag'] if n.get('parent')=='L0.ffn.down']
        self.assertEqual([n['format'] for n in parts],['fp4','fp8'])
        self.assertEqual(parts[0]['rows'],6*5120)
        self.assertEqual(parts[1]['rows'],5120)
        self.assertEqual(parts[1]['deps'],[parts[0]['id']])
        self.assertTrue(all(n['k']==2304 for n in parts))

    def test_head_and_hc_have_distinct_arithmetic(self):
        nodes={n['id']:n for n in self.inputs['dag']}
        h=nodes['head.lm_head:component0']
        self.assertEqual((h['format'],h['stage'],h['layer']),('bf16','head',None))
        self.assertEqual(nodes['L0.attn.wo_a:component0']['activation_bytes'],8*4096*2)
        self.assertEqual(nodes['L0.attn.hc.fn']['kind'],'dedicated_fp32')
        self.assertGreater(nodes['L0.attn.hc.fn']['duration_ns'],0)
        self.assertTrue(all(n.get('format')!='mixed' for n in nodes.values() if n['kind']=='weight'))

    def test_no_missing_dependencies_or_zero_unknown_service(self):
        seen=set()
        for n in self.inputs['dag']:
            self.assertTrue(set(n['deps'])<=seen,n['id'])
            seen.add(n['id'])
            if n.get('unknown') and n['kind']!='weight':
                self.assertGreater(n['duration_ns'],0,n['id'])
        self.assertIn('token.return',seen)
        self.assertTrue(self.inputs['unknown_nonweight_nodes'])
        self.assertFalse(self.inputs['implementation_configuration_complete'])
        self.assertIsNone(self.inputs['power']['total_W'])
        self.assertTrue(self.inputs['qualification_blockers'])

    def test_source_directory_and_shared_area(self):
        self.assertEqual(DEFAULT_INPUT_DIR,ROOT/'results/uarch/hbrom/inputs')
        self.assertTrue(self.inputs['source_pins'])
        c=self.inputs['compute']
        self.assertAlmostEqual(c['private_tile_area_mm2']+c['shared_service_area_mm2'],c['area_mm2'],places=9)
        self.assertEqual(c['local_sram_bytes']+c['shared_sram_bytes'],819200)
        self.assertEqual(self.inputs['supported_tp'],[4])

    def test_census_mismatch_is_error(self):
        inv=dict(tensors=[],checkpoint_bytes=1,derived_auxiliary_payloads=[])
        with self.assertRaises(ValueError):normalize_storage(inv)

if __name__=='__main__':unittest.main()
