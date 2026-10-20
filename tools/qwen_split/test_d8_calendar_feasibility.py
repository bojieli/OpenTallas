import unittest
from d8_calendar_feasibility import interval, reset_candidate, geometry, analyze

class CalendarTests(unittest.TestCase):
    def test_sram_two_edges_same_age(self):
        p={'tt':120.,'ff':-50.}; f=interval(p,833.333,'flop');s=interval(p,833.333,'sram')
        self.assertEqual(s,(f[0]+2,f[1]+2))
    def test_common_corner_interval_no_wrapping(self):
        lo,hi=interval({'tt':-4000.,'ff':4000.},833.333,'flop')
        self.assertGreater(lo,hi)
    def test_fourth_strap_and_zero_warm(self):
        r=reset_candidate(3,8,0,'flop');self.assertEqual(r['K'],10);self.assertEqual(r['straps'],[0,1,0,1])
        r=reset_candidate(3,0,2,'flop');self.assertEqual(r['K'],0);self.assertEqual(r['receiver_output_unblocked_edge'],21)
    def test_sram_reset_formula(self):
        self.assertEqual(reset_candidate(5,8,0,'sram')['K'],11)
    def test_slices_cover_all_payload_no_ties(self):
        for width in [453,520,548]:self.assertEqual(sum(geometry(width)[1]),width)
        with self.assertRaises(ValueError):geometry(597)
    def test_missing_data_and_actual_reset_fail_closed(self):
        lanes={'lanes':[dict(bid='x',bits=32,n=1,landing='u',lane='data')]}
        phases={'lanes':[dict(bid='x',dck_tt=0,dck_ff=0)]}
        result=analyze(lanes,phases,{'T_ps':833.333,'links':[]})
        self.assertFalse(result['qualified']);self.assertEqual(result['status'],'BLOCKED')
        self.assertIn('MISSING_TTFF_DATA_SLACK',result['blockers'])
        self.assertIn('MISSING_NATIVE_INSTANCE_RESET_CONTRACT',result['blockers'])
        self.assertNotIn('reset_models_by_corner',result['lanes'][0])
    def test_source_bound_candidate_prices_all_edges(self):
        lane=dict(bid='x',bits=32,n=1,landing='u',lane='data',src_ck='a',dst_ck='b')
        phase=dict(bid='x',dck_tt=0.,dck_ff=0.)
        old=dict(bid='x',E=2,s1={'tt':0.,'ff':0.},h0={'tt':0.,'ff':0.})
        c=dict(landing='u',source_commit='commit',netlist_sha256='1'*64,native_receipt_sha256='2'*64,
               reset_trace_sha256='3'*64,phase_receipt_sha256='4'*64,raw_release_cases={v:dict(G_raw=0,R0_raw=0) for v in ['tt','ff']},
               raw_release_verified=True,first_use_epoch_verified=True,all_roots_max_load=32,
               width=32,kind='flop',straps=[0,1,0,0],source_clock='a',receiver_clock='b',
               source_to_input_edges=2,output_to_consumer_edges=1,compiled_total_edges=6,source_edge_origin=0,receiver_edge_origin=0,origin_receipt_sha256='5'*64,upstream_source_kind='source_clocked_release',production_upstream_complete=True,clock_reset_correlation_verified=True,common_schedule_epoch='test-only synthetic fixture',source_counter_pin='producer/counter',receiver_counter_pin='consumer/counter',source_origin_event='start',receiver_origin_event='start')
        d=analyze({'lanes':[lane]},{'lanes':[phase]},{'T_ps':833.333,'links':[old]}, {'x':c})
        self.assertFalse(d['qualified']);self.assertEqual(d['lanes'][0]['priced_total_edges'],6)
        self.assertEqual(d['lanes'][0]['phase_edge_origin_status'],'EXPLICIT_SAME_INTEGER_REBASE_TTFF')
        self.assertFalse(d['blockers'])
        c['compiled_total_edges']=4
        d=analyze({'lanes':[lane]},{'lanes':[phase]},{'T_ps':833.333,'links':[old]}, {'x':c})
        self.assertIn('COMPILER_AGE_UNPRICED_OR_MISMATCH',d['blockers'])
        c['upstream_source_kind']='fixed_absolute_testbench_release'
        c['production_upstream_complete']=False
        d=analyze({'lanes':[lane]},{'lanes':[phase]},{'T_ps':833.333,'links':[old]}, {'x':c})
        self.assertIn('ARTIFICIAL_UPSTREAM_RELEASE',d['blockers'])
        self.assertIn('PRODUCTION_UPSTREAM_CORRELATION_UNPROVEN',d['blockers'])
        c['upstream_source_kind']='source_clocked_release';c['production_upstream_complete']=True
        c['raw_release_cases']={'tt':dict(G_raw=487,R0_raw=2053),'ff':dict(G_raw=492,R0_raw=2059)}
        d=analyze({'lanes':[lane]},{'lanes':[phase]},{'T_ps':833.333,'links':[old]}, {'x':c})
        self.assertIn('NO_COMMON_IMMUTABLE_K',d['blockers'])
        c['all_roots_max_load']=33
        d=analyze({'lanes':[lane]},{'lanes':[phase]},{'T_ps':833.333,'links':[old]}, {'x':c})
        self.assertIn('NATIVE_FANOUT_OVER32',d['blockers'])
        self.assertNotIn('reset_models_by_corner',d['lanes'][0])
    def test_explicit_common_origin_rebase_preserves_age_and_K(self):
        T=833.333; phi={'tt':120.,'ff':-50.}; L=interval(phi,T,'flop')[0]
        S,R=2,1; shifted={k:v+(R-S)*T for k,v in phi.items()}
        newL=interval(shifted,T,'flop')[0]
        self.assertEqual(newL,L+S-R)
        self.assertEqual(reset_candidate(L,20,10,'flop')['K'],reset_candidate(newL,20-S,10-R,'flop')['K'])
        for k in phi:self.assertAlmostEqual((L-1)*T+phi[k],(newL-1)*T+shifted[k])
    def test_missing_corner_rejected(self):
        with self.assertRaises(ValueError):interval({'tt':1},833.,'flop')
if __name__=='__main__':unittest.main()
