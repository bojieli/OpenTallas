import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import h4_hbm_pc40_native_ingress as N

PAYLOAD=ROOT/'results/uarch/h4_hbm_pc40_native_ingress_20261003/payload'


class NativeIngress(unittest.TestCase):
    def allocation(self):
        return dict(physical_PC=1,client=0,original_tag=123,generation=7,
                    native_tag=2**40+9,native_generation=2**42+3,
                    live_namespace_reserved=True)

    def leases(self):
        # Unit-test reservation only: never submitted as a production snapshot.
        return dict(source_version=N.VERSION,source_home=['RF',0,0,38],
                    source_lease='test.source',entering_snapshot_source='unit-test',
                    workspace=[dict(slot=s,lease='test.'+str(s),reserved=True,prior_live=False)
                               for s in (17,18,19)])

    def test_actual_producer_bytes_no_oracle_input(self):
        p=N.packet(PAYLOAD,self.allocation(),self.leases())
        self.assertEqual(bytes.fromhex(p['payload_hex'])[::-1],(PAYLOAD/'gate.bin').read_bytes())
        self.assertFalse(p['oracle_payload_used'])
        self.assertEqual(p['HBM_commands'],0)
        self.assertEqual(p['source_RFslot'],38)

    def test_private_native64_not_truncated(self):
        p=N.packet(PAYLOAD,self.allocation(),self.leases())
        self.assertEqual(p['native_tag64'],2**40+9)
        self.assertEqual(p['native_generation64'],2**42+3)
        self.assertEqual(p['owner46'],1<<39|123<<4|7)

    def test_namespace_and_width_refusal(self):
        for field,value in [('generation',16),('original_tag',2**32),('physical_PC',128),
                            ('native_tag',2**64),('client',5),('generation',True),
                            ('live_namespace_reserved',False)]:
            a=self.allocation();a[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):N.packet(PAYLOAD,a,self.leases())

    def test_no_empty_or_live_workspace_substitute(self):
        for change in ('missing_snapshot','missing_source','live_workspace','missing_workspace','wrong_home','wrong_version'):
            l=self.leases()
            if change=='missing_snapshot':del l['entering_snapshot_source']
            if change=='missing_source':del l['source_lease']
            if change=='live_workspace':l['workspace'][1]['prior_live']=True
            if change=='missing_workspace':l['workspace'].pop()
            if change=='wrong_home':l['source_home']=['RF',0,0,19]
            if change=='wrong_version':l['source_version']='different'
            with self.subTest(change=change),self.assertRaises(ValueError):N.packet(PAYLOAD,self.allocation(),l)

    def test_oracle_payload_cannot_replace_gate(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            (p/'native_capture.json').write_bytes((PAYLOAD/'native_capture.json').read_bytes())
            (p/'gate.bin').write_bytes((PAYLOAD/'FMAX.bin').read_bytes())
            with self.assertRaises(ValueError):N.packet(p,self.allocation(),self.leases())

    def test_model_positive_composed_once(self):
        m=N.model()
        self.assertEqual(m['new_protected_bits'],4824)
        self.assertEqual(m['conditional_publish_to_issue_edges'],12)
        self.assertEqual(m['selected_total_conditional_edges'],139)
        self.assertGreater(m['footprint_mm2_50pct_ASSUMED'],0)
        self.assertIsNone(m['whole_token_latency_ns'])
        self.assertIsNone(m['slot_fit'])
        self.assertFalse(m['physical_admission'])

    def test_nonzero_grant_and_clock(self):
        for kw in ({'wait_edges':0},{'period_ns':0},{'wait_edges':False}):
            with self.assertRaises(ValueError):N.model(**kw)


if __name__=='__main__':unittest.main()
