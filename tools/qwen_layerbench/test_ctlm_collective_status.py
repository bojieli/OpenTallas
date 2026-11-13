"""Explicit collective receipts connect real ss5 events to native compiler status."""
import copy
import hashlib
import importlib.util
import json
import subprocess
import unittest
import ctlm_image as C

class CollectiveReceipts(unittest.TestCase):
    def setUp(self):
        self.plan=[dict(kind='XC',tag=0,at=10,done=20,window='allreduce1'),
                   dict(kind='SEG',at=20,window='allreduce1')]
        producer='rtl/qwen_dv/qfd_dv_slice2.sv'
        self.receipt=dict(schema='opentallas.qwen.collective-status.v1',
            source_commit=subprocess.check_output(['git','-C',str(C.ROOT),'rev-parse','HEAD'],text=True).strip(),
            controller_sha256=C.sha(C.ROOT/'rtl/qwen_dv/qfd_tt_ctlm_dv.sv'),
            producer=dict(path=producer,sha256=C.sha(C.ROOT/producer)),
            plan_sha256=hashlib.sha256(json.dumps(self.plan,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
            events=[dict(tag=0,edge=20,ar_land=1,ar_last=1),dict(tag=0,edge=21,ar_land=0,ar_last=1)])

    def test_default_has_no_fabricated_collective_status(self):
        self.assertEqual(C.status_timeline(self.plan,{},{}),[])

    def test_real_pin_contract_and_consumer_packing(self):
        status=C.status_timeline(self.plan,{}, {},collective_receipt=self.receipt)
        spec=importlib.util.spec_from_file_location('receipt_consumer',C.ROOT/'rtl/test/qwen_dv/tt_ctlm_prog_bench.py')
        consumer=importlib.util.module_from_spec(spec);spec.loader.exec_module(consumer)
        events=[];consumer.status_events(events,0,status,None)
        self.assertTrue(any(e==20 and kind==8 and (data>>106)&1 and (data>>25)&1 for e,kind,data in events))
        self.assertTrue(all(kind==8 for _,kind,_ in events))
        self.assertEqual(events[-1],(21,8,1<<25))

    def test_missing_and_early_events_rejected(self):
        for events in ([],[dict(tag=0,edge=19,ar_land=1,ar_last=1)],
                       [dict(tag=0,edge=20,ar_land=0,ar_last=1)],
                       [dict(tag=0,edge=21,ar_land=1,ar_last=1)]):
            r=copy.deepcopy(self.receipt);r['events']=events
            with self.assertRaises(C.CompileError):C.collective_status_events(self.plan,r)

    def test_source_and_plan_identity_rejected(self):
        for key in ('source_commit','controller_sha256','plan_sha256'):
            r=copy.deepcopy(self.receipt);r[key]='0'*len(r[key])
            with self.assertRaises(C.CompileError):C.collective_status_events(self.plan,r)
        r=copy.deepcopy(self.receipt);r['producer']['sha256']='0'*64
        with self.assertRaises(C.CompileError):C.collective_status_events(self.plan,r)

    def test_duplicate_and_unknown_events_rejected(self):
        r=copy.deepcopy(self.receipt);r['events']*=2
        with self.assertRaises(C.CompileError):C.collective_status_events(self.plan,r)
        r=copy.deepcopy(self.receipt);r['events'][0]['tag']=1
        with self.assertRaises(C.CompileError):C.collective_status_events(self.plan,r)

if __name__=='__main__':unittest.main()
