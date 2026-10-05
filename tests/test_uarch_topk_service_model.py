import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import uarch_topk_service_model as M

class ServiceG0(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.r=M.build()
    def test_exact_replay(self):
        self.assertEqual(self.r,json.loads((M.BASE/'model.json').read_text()))
    def test_compiled_storage_not_active_extent(self):
        for n in [4,96]:
            for kind in ['DIG8_balanced_comb','DIG8_staged','DIG4_existing']:
                rows=[s for s in self.r['shapes'] if s['compiled']['N']==n and s['kind']==kind]
                self.assertEqual([s['runtime']['n'] for s in rows],[512,2048])
                self.assertEqual([s['compiled']['NMAX'] for s in rows],[2048,2048])
                self.assertEqual(rows[0]['base_state_bits'],rows[1]['base_state_bits'])
                self.assertEqual(rows[0]['candidate_memory_bits'],64*n*2048)
    def test_actual_ROM_ports(self):
        rows=[s for s in self.r['shapes'] if s['compiled']['N']==4]
        for s in rows:
            self.assertEqual(s['compiled']['LDW'],4)
            self.assertEqual(s['ports']['load_bits_per_edge'],2048)
            self.assertEqual(s['ports']['result_bits_per_edge'],2048)
            self.assertEqual(s['ports']['minimum_accepted_load_edges_scores_plus_IDs'],s['runtime']['n']//8)
    def test_program_and_calendar_call_join(self):
        bindings=self.r['source_service_binding']
        self.assertEqual(len(bindings['ROM']['calendar_calls']),9)
        self.assertEqual([c['runtime_n'] for c in bindings['ROM']['calendar_calls']].count(2048),1)
        self.assertEqual([c['layer'] for c in bindings['ROM']['calendar_calls'] if c['runtime_n']==512],[2,8,14,20,24,28,32,36])
        self.assertEqual([(c['layer'],c['runtime_n']) for c in bindings['ROM']['calendar_calls'] if c['layer']==20],[(20,512),(20,2048)])
        calls=bindings['HBM']['calendar_calls']
        self.assertEqual([x['source_op'] for x in bindings['HBM']['native_calendar']['instructions'] if x['source_op']['what']!='argmax'],calls)
        self.assertFalse(bindings['HBM']['hardware_provider_bound'])
    def test_latency_three_way_and_conditional_composition(self):
        totals=self.r['service_composition']
        self.assertEqual([totals[k]['ROM_added_serial_service_cycles_per_position'] for k in ['DIG8_balanced_comb','DIG8_staged','DIG4_existing']],[0,1044,1788])
        self.assertEqual([totals[k]['HBM_added_serial_service_cycles_per_position_if_same_provider'] for k in ['DIG8_balanced_comb','DIG8_staged','DIG4_existing']],[0,1188,2556])
        for n in [4,96]:
            for count in [512,2048]:
                d={s['kind']:s for s in self.r['shapes'] if s['compiled']['N']==n and s['runtime']['n']==count}
                self.assertLess(d['DIG8_staged']['source_select_cycle_upper_envelope'],d['DIG4_existing']['source_select_cycle_upper_envelope'])
                self.assertLess(d['DIG8_balanced_comb']['source_select_cycle_upper_envelope'],d['DIG8_staged']['source_select_cycle_upper_envelope'])
                self.assertEqual(d['DIG8_balanced_comb']['additional_state_bits'],0)
    def test_actual_density_and_storage_only_slot_refusal(self):
        slot=self.r['slot_binding']
        self.assertEqual(slot['reservation']['name'],'X_SEL_TOPK_STORE')
        for c in slot['comparisons']:
            self.assertGreater(c['shortfall_state_only_mm2_at_source_50pct'],0)
            self.assertFalse(c['fit_source_50pct'])
            self.assertGreater(c['state_only_utilization_required'],0.5)
        self.assertIn('50pct',slot['placement_basis'])
        self.assertFalse(self.r['G0']['engine_RTL_admitted'])
        self.assertFalse(self.r['G0']['PR_admitted'])
    def test_compaction_and_fanout_costs_are_not_omitted(self):
        for s in self.r['shapes']:
            p=s['compiled']['PF'];shared=s['area']['shared_source_construction']
            self.assertEqual(shared['compactor_lane_slot_pairs'],p*(p+1)//2)
            self.assertEqual(shared['unchanged_filter_depth']['equal_quota_serial_additions'],p)
            self.assertEqual(shared['fanout_sinks']['filter_threshold_bit_sinks'],2*p)
            self.assertGreater(shared['area_um2_by_cone']['filter_triangular_compactor'],0)
            self.assertGreater(shared['area_um2_by_cone']['candidate_write_hold_muxes'],0)
            self.assertGreater(shared['area_um2_by_cone']['explicit_fanout4_buffer_construction'],0)
            self.assertFalse(s['clock']['closed'])
    def test_pin_mutant_refused(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td)/'model';shutil.copytree(M.BASE,base)
            p=base/'inputs/rtl/chip/ot_w15_coll_dma.sv'
            p.write_text(p.read_text().replace('TK_NMAX = 2048','TK_NMAX = 512'))
            with self.assertRaisesRegex(ValueError,'pin mismatch'):M.build(base)
    def test_caller_mutant_refused_even_with_rehashed_input(self):
        import hashlib
        with tempfile.TemporaryDirectory() as td:
            base=Path(td)/'model';shutil.copytree(M.BASE,base)
            rel='inputs/rtl/chip/ot_w15_coll_dma.sv';p=base/rel
            p.write_text(p.read_text().replace('LDW(GW == 4 ? N : 1)','LDW(1)'))
            pins=json.loads((base/'sourcepins.json').read_text());pins['inputs_sha256'][rel]=hashlib.sha256(p.read_bytes()).hexdigest()
            (base/'sourcepins.json').write_text(json.dumps(pins))
            with self.assertRaisesRegex(ValueError,'caller binding changed'):M.build(base)
    def test_native_calendar_mutant_refused(self):
        import hashlib
        with tempfile.TemporaryDirectory() as td:
            base=Path(td)/'model';shutil.copytree(M.BASE,base)
            rel='inputs/hbm_calendar_projection.json';p=base/rel;r=json.loads(p.read_text());r['instructions'][0]['source_op']['k']=2048;p.write_text(json.dumps(r))
            pins=json.loads((base/'sourcepins.json').read_text());pins['inputs_sha256'][rel]=hashlib.sha256(p.read_bytes()).hexdigest();(base/'sourcepins.json').write_text(json.dumps(pins))
            with self.assertRaisesRegex(ValueError,'calendar/source call join changed'):M.build(base)
    def test_no_new_hardware_or_clock_or_Qwen_substitution(self):
        self.assertEqual(self.r['experiments_launched'],0)
        self.assertFalse(self.r['baseline_changed'])
        self.assertIn('unchanged',self.r['source_service_binding']['Qwen_ROM_and_HBM'])
        self.assertIn('old route untouched',self.r['PVE2_PVE3'])

if __name__=='__main__':unittest.main()
