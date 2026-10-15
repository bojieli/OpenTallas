"""Reject address/owner collisions at the actual single-bank port boundary."""
import copy
import hashlib
import unittest
from pathlib import Path
from native_vm_reservations import ROOT,compile_bindings
import json

class NativeReservationTest(unittest.TestCase):
    def setUp(self):
        self.abi=json.loads((ROOT/'results/arch/hbm_vm_static_1014/quadrant_abi_sw_quant_v2.json').read_text())
        self.inv=dict(source_sha256={'source':'fixed'},records=[dict(record_sha256='operation',operands={'A':dict(allocation=dict(status='static source range, no relocation granted',word_begin=0,word_end=8))})])
        rtl='rtl/hbm_accel/generic/vm/static/ot_hbm_vm_lg_static_bank.sv'
        self.event=dict(operand='A',sector=0,quadrant='SW',kind='read',owner=0,bank_capture_edge=5,lg_tap=0)
        self.binding=dict(inventory_source_sha256=self.inv['source_sha256'],programme_words=16,producers=[dict(record_ordinal=0,record_sha256='operation',rtl=rtl,rtl_sha256=hashlib.sha256((ROOT/rtl).read_bytes()).hexdigest(),launch_authority='unit test trace only; not a whole-kernel timestamp',events=[self.event])])
    def test_actual_word_and_lg_arrival(self):
        result=compile_bindings(self.inv,self.binding,self.abi)
        self.assertEqual(result['reservations'][0]['vm_word'],4)
        self.assertEqual(len(result['programmes']['SW']['configuration_writes']),16)
    def test_logical_groups_share_one_physical_read_port(self):
        e=copy.deepcopy(self.event);e['owner']=1;e.pop('lg_tap')
        self.binding['producers'][0]['events'].append(e)
        with self.assertRaisesRegex(ValueError,'physical read port collision'):compile_bindings(self.inv,self.binding,self.abi)
    def test_wrong_sid_not_modulo_relocated(self):
        self.event['quadrant']='NE'
        with self.assertRaisesRegex(ValueError,'canonical SID'):compile_bindings(self.inv,self.binding,self.abi)
    def test_outside_operand(self):
        self.event['sector']=8
        with self.assertRaisesRegex(ValueError,'encoded operand'):compile_bindings(self.inv,self.binding,self.abi)
    def test_capacity_not_pretended_paged(self):
        self.binding['programme_words']=1025
        with self.assertRaisesRegex(ValueError,'paging source'):compile_bindings(self.inv,self.binding,self.abi)
    def test_source_pinned(self):
        self.binding['producers'][0]['rtl_sha256']='stale'
        with self.assertRaisesRegex(ValueError,'RTL source changed'):compile_bindings(self.inv,self.binding,self.abi)

if __name__=='__main__':unittest.main()
