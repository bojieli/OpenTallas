import gzip, json, sys, unittest
from collections import Counter, defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import dsrom_noECC_full_clock_reset_union as g
from dsrom_noECC_enable_distribution import trace

def records(p):
    return [json.loads(s) for s in gzip.decompress(p.read_bytes()).decode().splitlines()]

class FullUnion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.x=json.loads((g.BASE/'model.json').read_text())
        cls.p={k:records(g.BASE/(k+'_placement.jsonl.gz')) for k in cls.x['cases']}
        cls.e={k:records(g.BASE/(k+'_endpoints.jsonl.gz')) for k in cls.x['cases']}

    def test_interval_complement_merges_overlapping_blocks(self):
        self.assertEqual(g.intervals_without([(2,5),(4,8),(11,15)],0,12),[(0,2),(8,11)])

    def test_every_source_instance_present_once_with_unchanged_master(self):
        for k,p in self.p.items():
            cs,_,_,_=trace(k)
            names={r['instance']:r for r in p}
            self.assertEqual(len(names),len(p))
            self.assertFalse(set(cs)-set(names))
            for n,c in cs.items(): self.assertEqual(names[n]['master'],c['master'])

    def test_full_body_union_disjoint_on_every_row(self):
        for k,p in self.p.items():
            rows=defaultdict(list)
            for r in p:
                x,y,X,Y=r['bbox_DBU']
                for row in range(y//270,(Y+269)//270):rows[row].append((x,X,r['instance']))
            for row,rs in rows.items():
                rs.sort()
                for a,b in zip(rs,rs[1:]):self.assertLessEqual(a[1],b[0],(k,row,a,b))

    def test_sites_orientations_and_no_outline_borrowing(self):
        for k,p in self.p.items():
            frame=self.x['cases'][k]['outline_DBU']
            for r in p:
                x,y,X,Y=r['bbox_DBU']
                self.assertTrue(0<=x<X<=frame[2] and 0<=y<Y<=frame[3])
                if r['master']=='ot_rom_4096x274_m8': continue
                self.assertEqual(x%54,0); self.assertEqual(y%270,0)
                self.assertEqual(r['orientation'],'MX' if y//270%2==0 else 'R0')

    def test_exact_clock_domain_counts_include_ICGs_and_eight_clones(self):
        expected={'q':{'clk':1144,'leaf_clk[0]':6577,'leaf_clk[1]':6161,'leaf_clk[2]':5269,'leaf_clk[3]':9814},
                  'bfcolumn':{'clk':2441,'leaf_clk[0]':10116,'leaf_clk[1]':6161,'leaf_clk[2]':5269,'leaf_clk[3]':67410}}
        for k,c in self.x['cases'].items():
            expected[k].update({'leaf_clk[%d]'%i:1 for i in range(4,8)})
            self.assertEqual({n:d['named_endpoint_count'] for n,d in c['clock_domains'].items()},expected[k])
            self.assertEqual(len(c['source_ICG_connections']),8)
            self.assertEqual({r['net'] for r in c['macro_leaf_clock_consumers']},{'leaf_clk[%d]'%i for i in range(4,8)})

    def test_real_macro_clock_pin_and_corners_in_full_union(self):
        for ep in self.e.values():
            macro=[p for p in ep if p['source_kind']=='retained_source_ROM_macro']
            self.assertEqual(len(macro),4)
            for p in macro:
                r=p['translated_pin_rectangles'][0]
                self.assertEqual(r['layer'],'M4')
                self.assertEqual(r['bbox_DBU'][0],p['bbox_DBU'][0])
                self.assertEqual(r['bbox_DBU'][2]-r['bbox_DBU'][0],24)
                self.assertAlmostEqual(p['SS_FF_max_pin_cap_fF']['ss'],8.6838)
                self.assertAlmostEqual(p['SS_FF_max_pin_cap_fF']['ff'],10.3732)

    def test_reset_SETN_separate_from_RESETN_and_only_four_clone_resets(self):
        for k,ep in self.e.items():
            reset=[p for p in ep if p['pin'] in ('RESETN','SETN')]
            self.assertEqual(sum(p['pin']=='SETN' for p in reset),8)
            self.assertEqual(sum(p['source_kind']=='proposed_enable_metadata_clone' for p in reset),4)
            self.assertEqual(len(reset),930 if k=='q' else 4408)
            contract={p['pin']:p for p in self.x['cases'][k]['pin_specific_async_release_contracts']}
            self.assertAlmostEqual(contract['SETN']['corners']['ss']['policy_recovery_plus_setup_and_unproven_skew_ps'],131.1076)
            self.assertAlmostEqual(contract['RESETN']['corners']['ss']['policy_recovery_plus_setup_and_unproven_skew_ps'],66.8308)

    def test_actual_WAKE_inversion_retained_at_eight_named_local_sites(self):
        for k,c in self.x['cases'].items():
            cs,ps,_,_=trace(k)
            self.assertEqual(len(c['actual_WAKE_QN_INV_ICG_paths']),8)
            self.assertEqual({p['leaf'] for p in c['actual_WAKE_QN_INV_ICG_paths']},set(range(8)))
            byname={p['instance']:p for p in self.p[k]}
            for p in c['actual_WAKE_QN_INV_ICG_paths']:
                n=p['retained_INV_instance']
                self.assertTrue(cs[n]['master'].startswith('INV'))
                self.assertEqual(ps[n]['Y'],ps[p['ICG_instance']]['ENA'])
                self.assertEqual(byname[n]['bbox_DBU'],p['source_INV_bbox_DBU'])
                self.assertTrue(p['enable_setup_hold_pulse_width_and_wires_not_qualified'])

    def test_unique_endpoints_literal_pin_rectangles_inside_real_bodies(self):
        for ep in self.e.values():
            ids=[(p['instance'],p['pin']) for p in ep]
            self.assertEqual(len(ids),len(set(ids)))
            for p in ep:
                x,y,X,Y=p['bbox_DBU']
                for r in p['translated_pin_rectangles']:
                    a,b,A,B=r['bbox_DBU']
                    self.assertTrue(x<=a<A<=X and y<=b<B<=Y)
                self.assertGreater(p['SS_FF_max_pin_cap_fF']['ss'],0)
                self.assertGreater(p['SS_FF_max_pin_cap_fF']['ff'],0)

    def test_no_missing_cells_or_master_area_substitution(self):
        ctx=json.loads(g.CTX.read_text())
        for k,c in self.x['cases'].items():
            self.assertEqual(c['unplaced_cell_count'],0)
            self.assertEqual(c['unplaced_clock_reset_endpoints'],[])
            self.assertAlmostEqual(c['retained_source_stdcell_area_um2'],ctx['cases'][k]['physical_LEF_cell_union_area_um2'])
            self.assertEqual(c['source_scalar_neighbor_extra_area_um2'],0)

    def test_source_scalar_fanouts_preserved_no_zero_wire_claim(self):
        for k,c in self.x['cases'].items():
            cs,ps,_,_=trace(k)
            for s in c['retained_scalar_QN_fanouts']:
                wanted={(n,p) for n,ports in ps.items() if n!=s['source_instance'] for p,v in ports.items() if v==s['QN_net']}
                self.assertEqual({(r['instance'],r['pin']) for r in s['receivers']},wanted)
                self.assertTrue(all(r['endpoint_Manhattan_lower_bound_um']>0 for r in s['receivers']))
                self.assertTrue(s['wire_geometry_RC_clock_minmax_and_hold_not_qualified'])

    def test_artifact_and_source_receipts(self):
        for path,h in self.x['source_input_sha256'].items():self.assertEqual(g.sha(ROOT/path),h)
        for k,c in self.x['cases'].items():
            self.assertEqual(g.sha(g.BASE/(k+'_placement.jsonl.gz')),c['placement_artifact_sha256'])
            self.assertEqual(g.sha(g.BASE/(k+'_endpoints.jsonl.gz')),c['endpoint_artifact_sha256'])

    def test_no_qualification_clock_or_area_credit(self):
        self.assertFalse(self.x['physical_build_admitted'])
        self.assertFalse(self.x['PG_OBS_pin_via_extraction_or_skew_credit'])
        self.assertEqual(self.x['added_capture_edges'],0)
        self.assertEqual(self.x['area_credit_um2'],0)
        self.assertEqual(self.x['SS_setup_uncertainty_ps'],60)
        self.assertEqual(self.x['FF_hold_uncertainty_ps'],25)
        for c in self.x['cases'].values():self.assertEqual(c['full_clock_reserve_embedding_credit_um2'],0)

if __name__=='__main__': unittest.main()
