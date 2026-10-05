"""Source construction/ownership controls, no HDL or physical qualification."""
import copy
import gzip
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import dsrom_selector_physical_join as J


class JoinTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model,cls.rows=J.build()
        cls.records,_=J.archive()
        cls.fixed=J.inputs()

    def test_full_shape_and_unchanged_cost(self):
        m=self.model
        self.assertEqual(m['candidate'],'DS4096-TP4-S58-PAR2-NP2048')
        self.assertEqual(m['geometry'],dict(N=4,NMAX=2048,LDW=4,P=64,PF=64,DIG=8,CB=14,S=58,PAR=2,NP=2048,q_pairs=1686,BF_pairs=362))
        self.assertEqual(m['station']['cycles_per_call'],99+99+28)
        self.assertEqual(m['station']['ninecall_cycles'],9*226)
        self.assertEqual(m['station']['preferred_data_station_nodes']+m['station']['formed_write_data_nodes'],475954)
        self.assertEqual(m['station']['core_state_bits'],698354)

    def test_actual_packet_bit_offsets(self):
        mapped={r['pin']:r['packet_bit'] for r in self.rows}
        expected={'inputs.stride[0]':0,'inputs.go[0]':60,'inputs.ld_data[0]':61,
          'inputs.ld_data[2047]':2108,'inputs.ld_word[0]':2109,'inputs.ld_valid[0]':2121,
          'outputs.stat_cycles[0]':0,'outputs.out_last[0]':32,'outputs.out_data[0]':33,
          'outputs.out_nw[0]':2081,'outputs.out_valid[0]':2084,'outputs.busy[0]':2087}
        for pin,bit in expected.items(): self.assertEqual(mapped[pin],bit)
        for group,width in [('inputs',2122),('outputs',2088)]:
            self.assertEqual(sorted(r['packet_bit'] for r in self.rows if r['pin'].startswith(group+'.')),list(range(width)))

    def test_first_source_stage_is_at_producer(self):
        for r in self.rows:
            e=r['track'];points=r['preferred_track_points_DBU']
            distance=lambda p:abs(p[0]-3125440)+abs(p[1]-e['horizontal_y_DBU'])
            ordered=[distance(p) for p in points]
            self.assertEqual(ordered,sorted(ordered,reverse=r['pin'].startswith('inputs.')))
            self.assertEqual(len(points),99)
            self.assertFalse(r['legal_cell_sites_assigned'])

    def test_missing_or_duplicate_track_refused(self):
        for mutation in ('missing','duplicate','foreign'):
            t=copy.deepcopy(self.fixed['tracks'])
            if mutation=='missing': t['assignments'].pop(0)
            if mutation=='duplicate':t['assignments'].append(copy.deepcopy(t['assignments'][0]))
            if mutation=='foreign':t['assignments'][0]['pin']='inputs.ld_data[2048]'
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):J.station_ledger(t)

    def test_enable_copies_are_added_not_WAKE(self):
        state=self.model['state_ownership']
        self.assertEqual(state['local_enable_new_FF'],8*2048)
        self.assertEqual(state['shared_BST_new_FF'],3264)
        self.assertEqual(state['existing_WAKE_new_charge_bits'],0)
        for case in self.model['enable'].values():
            self.assertEqual(len(case['replica_connections']),8)
            self.assertEqual(sum('valid' in c['instance'] for c in case['replica_connections']),4)
            for c in case['replica_connections']:
                self.assertTrue(c['unchanged_D_CLK_RESETN_SETN'])
                self.assertEqual(c['original_connections']['CLK'],'leaf_clk[0]')

    def test_no_control_multicycle_or_added_sampling_stage(self):
        for mutation in ('edge','stage','clock','reset','equation','candidate'):
            d=copy.deepcopy(self.records['enable_construction_WIP.json.gz'])
            c=d['cases']['q']
            if mutation=='edge':d['control_edges']=2
            if mutation=='stage':c['added_capture_latency_cycles']=1
            if mutation=='clock':c['source_state_copies'][0]['original_connections']['CLK']='root_clk'
            if mutation=='reset':c['source_state_copies'][0]['original_connections']['RESETN']="1'h1"
            if mutation=='equation':c['source_state_copies'][0]['unchanged_D_CLK_RESETN_SETN']=False
            if mutation=='candidate':d['candidate']='DS4096-TP4-S66-PAR2-NP2048'
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):J.validate_enable(d)

    def test_hold_deficit_not_hidden_by_SS_screen(self):
        for case in self.model['enable'].values():
            self.assertGreater(case['local_enable_SS_margin_ps'],0)
            paths={p['role']:p for p in case['replica_D_paths']}
            for role,margin in [('valid',-14.17792),('bank',-15.58042)]:
                self.assertAlmostEqual(paths[role]['FF_hold_margin_ps'],margin)
                self.assertGreater(paths[role]['SS_margin_ps'],0)
                self.assertFalse(paths[role]['other_fanout_wire_extracted'])
        self.assertFalse(self.model['physical_admission'])
        self.assertTrue(any(d['gate']=='FF hold' and d['status'].startswith('FAIL') for d in self.model['concrete_admission_deficits']))

    def test_once_only_distinct_area_components(self):
        a=self.model['area_ownership']
        self.assertAlmostEqual(a['selector_station_50pct_mm2'],.59560842564)
        self.assertAlmostEqual(a['local_enable_replacement_2048_50pct_mm2'],39.13272*2048/1e6)
        self.assertAlmostEqual(a['shared_broadcast_BUFFER_50pct_mm2'],.76065236352)
        self.assertAlmostEqual(a['shared_BST_replica_FF_50pct_mm2'],.0019035648)
        self.assertAlmostEqual(a['caller_guard_50pct_mm2'],.00000332424)
        self.assertAlmostEqual(self.model['area_increment_floor_mm2'],1.43831148876)

    def test_original_actual_timing_failure_preserved(self):
        self.assertEqual(self.model['baseline_control_fault_preserved'],[-8448.49707]*4)
        self.assertTrue(self.model['owner_snapshot_is_not_adopted_source'])
        self.assertFalse(self.model['station']['caller_fence_RTL_verified'])
        self.assertTrue(self.model['no_engine_or_physical_job_launched'])

    def test_archive_only_inputs_and_corruption_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);(base/'inputs').mkdir()
            for p in (J.BASE/'inputs').iterdir():(base/'inputs'/p.name).write_bytes(p.read_bytes())
            (base/'source_manifest.json').write_bytes((J.BASE/'source_manifest.json').read_bytes())
            a,_=J.archive(base);self.assertEqual(a,self.records)
            p=base/'inputs'/'enable_construction_WIP.json.gz';p.write_bytes(p.read_bytes()+b'foreign')
            with self.assertRaisesRegex(ValueError,'archive bytes changed'):J.archive(base)

    def test_absent_pinned_files_replay_but_present_corruption_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            self.assertEqual(J.inputs(root),self.fixed)
            relative,_=J.PINS['caller'];p=root/relative;p.parent.mkdir(parents=True);p.write_text('bad source')
            with self.assertRaisesRegex(ValueError,'fixed source changed: caller'):J.inputs(root)

    def test_replay_exact_output_hash_and_all_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp);m=J.emit(output)
            raw=gzip.decompress((output/'source_station_mapping.jsonl.gz').read_bytes())
            self.assertEqual(hashlib.sha256(raw).hexdigest(),m['station_mapping_artifact']['uncompressed_sha256'])
            self.assertEqual(len(raw.splitlines()),4210)
            self.assertEqual((output/'model.json').read_bytes(),(J.BASE/'r1/model.json').read_bytes())


if __name__=='__main__':unittest.main()
