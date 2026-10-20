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
        self.assertNotIn('reset_model',result['lanes'][0])
    def test_source_bound_candidate_prices_all_edges(self):
        lane=dict(bid='x',bits=32,n=1,landing='u',lane='data',src_ck='a',dst_ck='b')
        phase=dict(bid='x',dck_tt=0.,dck_ff=0.)
        old=dict(bid='x',E=2,s1={'tt':0.,'ff':0.},h0={'tt':0.,'ff':0.})
        c=dict(landing='u',source_commit='commit',netlist_sha256='1'*64,native_receipt_sha256='2'*64,
               reset_trace_sha256='3'*64,phase_receipt_sha256='4'*64,G_raw=0,R0_raw=0,
               raw_release_verified=True,first_use_epoch_verified=True,all_roots_max_load=32,
               width=32,kind='flop',straps=[0,1,0,0],source_clock='a',receiver_clock='b',
               source_to_input_edges=2,output_to_consumer_edges=1,compiled_total_edges=6)
        d=analyze({'lanes':[lane]},{'lanes':[phase]},{'T_ps':833.333,'links':[old]}, {'x':c})
        self.assertFalse(d['qualified']);self.assertEqual(d['lanes'][0]['priced_total_edges'],6)
        self.assertFalse(d['blockers'])
        c['compiled_total_edges']=4
        d=analyze({'lanes':[lane]},{'lanes':[phase]},{'T_ps':833.333,'links':[old]}, {'x':c})
        self.assertIn('COMPILER_AGE_UNPRICED_OR_MISMATCH',d['blockers'])
        c['all_roots_max_load']=33
        d=analyze({'lanes':[lane]},{'lanes':[phase]},{'T_ps':833.333,'links':[old]}, {'x':c})
        self.assertIn('NATIVE_FANOUT_OVER32',d['blockers'])
        self.assertNotIn('reset_model',d['lanes'][0])
    def test_missing_corner_rejected(self):
        with self.assertRaises(ValueError):interval({'tt':1},833.,'flop')
if __name__=='__main__':unittest.main()
