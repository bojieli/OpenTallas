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
        self.assertEqual([n['format'] for n in parts],['fp4']*6+['fp8'])
        self.assertEqual(parts[0]['rows'],5120)
        self.assertEqual([n['selected_expert_slot'] for n in parts[:6]],list(range(6)))
        self.assertEqual(parts[1]['rows'],5120)
        self.assertEqual(parts[1]['deps'],[parts[0]['id']])
        self.assertTrue(all(n['k']==2304 for n in parts))
        self.assertEqual(sum(n['macs'] for n in parts),7*5120*2304)
        self.assertEqual(sum(n['weight_bytes'] for n in parts[:6]),6*5120*2304*17/32)
        self.assertEqual(parts[-1]['weight_bytes'],5120*2304*33/32)

    def test_head_and_hc_have_distinct_arithmetic(self):
        nodes={n['id']:n for n in self.inputs['dag']}
        h=nodes['head.lm_head:component0']
        self.assertEqual((h['format'],h['stage'],h['layer']),('bf16','head',None))
        self.assertEqual(sum(n['activation_bytes'] for n in nodes.values() if n.get('parent')=='L0.attn.wo_a'),8*4096*2)
        gu=[n for n in nodes.values() if n.get('parent')=='L0.ffn.experts_gu']
        self.assertEqual(len(gu),12)
        self.assertTrue(all(n['rows']==2304 for n in gu))
        self.assertEqual(sum(n['macs'] for n in gu),6*2*2304*5120)
        self.assertEqual(sum(n['weight_bytes'] for n in gu),6*2*2304*5120*17/32)
        self.assertEqual(nodes['L0.attn.hc.fn']['kind'],'dedicated_fp32')
        self.assertGreaterEqual(nodes['L0.attn.hc.fn']['duration_ns'],450)
        self.assertTrue(all(n.get('format')!='mixed' for n in nodes.values() if n['kind']=='weight'))

    def test_no_missing_dependencies_or_zero_unknown_service(self):
        seen={n['id'] for n in self.inputs['dag']}
        self.assertEqual(len(seen),len(self.inputs['dag']))
        for n in self.inputs['dag']:
            self.assertTrue(set(n['deps'])<=seen,n['id'])
            if n.get('unknown') and n['kind']!='weight':
                self.assertGreater(n['duration_ns'],0,n['id'])
        pending={n['id']:set(n['deps']) for n in self.inputs['dag']}
        done=set()
        while pending:
            ready={k for k,v in pending.items() if v<=done}
            self.assertTrue(ready,'dependency cycle')
            done.update(ready)
            pending={k:v for k,v in pending.items() if k not in ready}
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
        self.assertEqual(c['local_sram_bytes']+c['shared_sram_bytes'],917504)
        self.assertEqual(c['retained_ring_depth'],1024)
        self.assertGreater(self.inputs['physical']['fixed_service_mm2'],209)
        self.assertGreater(self.inputs['physical']['cluster_slots_by_geometry']['128:4'],0)
        self.assertGreater(c['protection_area']['inner_control_increment_mm2'],0)
        self.assertEqual(self.inputs['supported_tp'],[1,2,4,8])
        self.assertEqual(set(self.inputs['dag_by_tp']),{'1','2','4','8'})
        self.assertFalse(any('hbrom_transport' in n for n in self.inputs['baseline_dag']))

    def test_census_mismatch_is_error(self):
        inv=dict(tensors=[],checkpoint_bytes=1,derived_auxiliary_payloads=[])
        with self.assertRaises(ValueError):normalize_storage(inv)

if __name__=='__main__':unittest.main()
