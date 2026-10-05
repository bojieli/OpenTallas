"""Independent source-algebra controls; never an HDL equivalence result."""
import copy
import gzip
import hashlib
import json
from pathlib import Path
import struct
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import prove_dsrom_balanced_selector_fence as P


class ProofTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.proof=P.build()

    def test_byte_exact_replay(self):
        self.assertEqual(self.proof,json.loads((P.BASE/'proof.json').read_text()))
        self.assertEqual(json.dumps(self.proof,indent=2,sort_keys=True)+'\n',(P.BASE/'proof.json').read_text())

    def test_full_compile_geometry_and_both_runtime_counts(self):
        self.assertEqual(self.proof['geometry'],dict(N=4,NMAX=2048,LDW=4,P=64,PF=64,DIG=8,CB=14))
        self.assertEqual({c['runtime_n'] for c in self.proof['cases']},{512,2048})
        self.assertEqual(len(self.proof['cases']),37)
        for c in self.proof['cases']:
            self.assertEqual(c['candidates'],4*c['runtime_n'])
            self.assertEqual(c['filter_rows'],4*c['runtime_n']//64)
            self.assertEqual(c['selection_sha256'],c['actual_model_selected_sha256'])

    def test_maximum_count_and_equal_threshold_seams(self):
        for runtime in (512,2048):
            keys=[P.key(0x3f800000)]*(4*runtime)
            for k in (1,64,65,512,4*runtime):
                threshold,quota,trace=P.threshold(keys,k)
                self.assertEqual(threshold,P.key(0x3f800000))
                self.assertEqual(quota,k)
                self.assertEqual(len(trace),4)
                self.assertEqual([t['remaining'] for t in trace],[k]*4)

    def test_order_key_against_independent_IEEE_comparison(self):
        values=[0xff800000,0xff7fffff,0xbf800000,0x80000001,0x80000000,0,1,0x3f800000,0x7f7fffff,0x7f800000]
        float_value=lambda x:struct.unpack('!f',struct.pack('!I',x))[0]
        for a in values:
            for b in values:
                self.assertEqual(P.key(a)>P.key(b),float_value(a)>float_value(b))
                self.assertEqual(P.key(a)==P.key(b),float_value(a)==float_value(b))

    def test_NaN_source_refusal_contract_not_recalibrated(self):
        source=(P.ROOT/P.SOURCE).read_text()
        self.assertIn("isnan = (x[30:23] == 8'hFF) && (x[22:0] != 0);",source)
        self.assertIn('if (nan_seen || k == 0 || n == 0',source)
        for bits in (0x7fc00000,0xff800001,0x7fffffff):self.assertTrue(P.nan(bits))
        for bits in (0x7f800000,0xff800000,0,1):self.assertFalse(P.nan(bits))
        for case in self.proof['cases']:
            self.assertFalse(any(P.nan(x) for x in P.fixture(case['runtime_n'],case['pattern'])))

    def test_all_public_padding_and_write_addresses(self):
        for c in self.proof['cases']:
            writes=c['formed_writes'];nwords=(c['k']+15)//16
            self.assertEqual(c['public_VM_words'],nwords)
            self.assertEqual([r[2] for r in writes],list(range(8192,8192+nwords)))
            payload=[id_ for _,_,_,word in writes for id_ in word]
            self.assertEqual(len(payload),16*nwords)
            self.assertEqual(payload[c['k']:],[0]*((-c['k'])%16))
            self.assertGreater(c['local_normalized_done_edge'],writes[-1][0])
            self.assertIsNone(c['original_consumer_absolute_deadline'])

    def test_source_runtime2048_k2048_four_ranks_connected(self):
        c=next(c for c in self.proof['cases'] if c['runtime_n']==2048 and c['k']==2048)
        self.assertEqual(len(c['formed_writes']),128)
        self.assertEqual(c['filter_rows'],128)
        self.assertGreater(c['row_bubbles'],0)

    def test_mutants_are_explicit_differences(self):
        expected={'threshold_off_by_one':'SELECTION_DIFF','reverse_tie':'SELECTION_DIFF','early_done':'FENCE_DIFF'}
        self.assertEqual(self.proof['mutant_DIFF'],expected)
        for mutant,marker in expected.items():
            with self.assertRaisesRegex(AssertionError,marker):P.compare(2048,512,'all_tie',mutant)

    def test_once_only_service_and_transport(self):
        self.assertEqual(self.proof['service_extra_cycles'],142)
        self.assertEqual(self.proof['transport_extra_cycles'],226)
        self.assertEqual(self.proof['ninecall_increment'],3312)

    def test_no_invented_execution_or_admission(self):
        for key in ('RTL_equivalence','clock_or_physical_qualification','engine_RTL_admitted','PR_admitted'):
            self.assertFalse(self.proof[key])
        self.assertTrue(self.proof['immutable_input_only'])
        self.assertTrue(self.proof['expected_values_assertions_only'])
        self.assertTrue(all(not c['source_field_or_RTL_execution'] for c in self.proof['cases']))

    def test_delivered_element_union_archive_and_scope(self):
        packed=(P.BASE/'element_union_WIP.json.gz').read_bytes();raw=gzip.decompress(packed)
        receipt=json.loads((P.BASE/'element_union_observation.json').read_text())
        self.assertEqual(hashlib.sha256(packed).hexdigest(),receipt['archive_sha256'])
        self.assertEqual(hashlib.sha256(raw).hexdigest(),receipt['original_sha256'])
        self.assertEqual(P.audit_union(json.loads(raw)),receipt['audit'])
        self.assertTrue(receipt['owner_source_uncommitted'])
        for case in receipt['audit'].values():
            self.assertTrue(case['clone_sites_on_source_grid'])
            self.assertFalse(case['selector_station_sites_qualified'])
            self.assertFalse(case['extracted_clock_reset_or_hold_qualified'])

    def test_wrong_clock_reset_tie_grid_overlap_and_double_charge_refused(self):
        source=json.loads(gzip.decompress((P.BASE/'element_union_WIP.json.gz').read_bytes()))
        for mutation in ('clock','reset','tie','grid','overlap','clock_charge','reset_charge','WAKE_alias'):
            d=copy.deepcopy(source);c=d['cases']['q'];pins=c['clone_translated_CLK_RESET_pin_descriptors'];u=c['clock_reset_full_source_union']['ss']
            if mutation=='clock':pins[0]['CLK']='root_clk'
            if mutation=='reset':pins[0]['RESETN']=None
            if mutation=='tie':u['SETN_constant1_extra_pin_count']=0
            if mutation=='grid':pins[0]['origin_DBU'][0]+=1
            if mutation=='overlap':pins[2]['origin_DBU']=pins[0]['origin_DBU'][:]
            if mutation=='clock_charge':u['composed_leaf0_pin_cap_fF']+=c['clone_clock_pin_debit_SS_FF_fF']['ss']
            if mutation=='reset_charge':u['composed_reset_pin_cap_fF']+=c['clone_reset_pin_debit_SS_FF_fF']['ss']
            if mutation=='WAKE_alias':pins[0]['instance']='g_wake.g_leaf[0].state'
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):P.audit_union(d)


if __name__=='__main__':unittest.main()
