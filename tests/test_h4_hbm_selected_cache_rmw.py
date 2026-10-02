import copy
import gzip
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import h4_hbm_selected_cache_rmw as m

class SelectedServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s=m.inputs();cls.c=m.compile_selected(cls.s);cls.model=m.build(cls.c,cls.s)
    def receipt(self,c,lease=1):
        return dict(generation=c['generation'],die=c['die'],SM=c['SM'],provider_reference=c['provider_reference'],lease=lease,live=True,outer_owner=c['outer_owner'])
    def acquire(self,e,c):e.acquire(c['id'],lease=1,owner_receipt=self.receipt(c))
    def event(self,e,c,name,**kw):return e.event(c['id'],lease=1,event=name,**kw)
    def test_all_actual_partial_and_shared_commands(self):
        self.assertEqual(len(self.c['RMW']),288);self.assertEqual(len(self.c['shared64']),9216)
        self.assertEqual({x['die'] for x in self.c['RMW']},set(range(96)))
        self.assertEqual({x['SM'] for x in self.c['shared64']},set(range(32)))
        for x in self.c['shared64']:
            self.assertEqual(x['physical_byte_address'],16777216+x['SM']*65536+x['scratch_byte_address'])
            self.assertEqual(x['scratch_row'],x['scratch_byte_address']//64)
            self.assertEqual(len(x['sector_children']),2)
            self.assertIsNone(x['outer_reverse_bound'])
    def test_opaque_merge_exceptional_bits_all_actual_prefix_sizes(self):
        # F32 NaN payloads, infinities, signed zero and arbitrary BF/INT bits.
        old=(bytes.fromhex('0100c07f000080ff0000008000000000')*32)
        for n in {c['active_words']for c in self.c['RMW']}:
            c=next(c for c in self.c['RMW']if c['active_words']==n);e=m.SelectedEndpoint(self.c);self.acquire(e,c)
            self.event(e,c,'read_child_accept');self.event(e,c,'read_ACK_consume',payload=old+old)
            self.event(e,c,'read_child_reverse');new=bytes.fromhex('0100807f')*n
            merged=self.event(e,c,'merge_register',payload=new)
            self.assertEqual(merged,new+old[len(new):]);self.assertEqual(len(merged),512)
            x=e.live[c['die'],c['SM']];self.assertIsNone(x['old']);self.assertEqual(len(x['merged']),512)
    def test_RMW_parent_owner_held_across_children_and_two_mirrors(self):
        c=self.c['RMW'][0];e=m.SelectedEndpoint(self.c);self.acquire(e,c)
        old=bytes(1024);new=bytes([0xff])*(c['active_words']*4)
        for name,kw in [('read_child_accept',{}),('read_ACK_consume',{'payload':old}),('read_child_reverse',{}),('merge_register',{'payload':new}),('write_child_accept',{})]:self.event(e,c,name,**kw)
        with self.assertRaisesRegex(ValueError,'both physical copy'):self.event(e,c,'write_ACK_consume',copy0=True,copy1=False)
        with self.assertRaises(ValueError):self.event(e,c,'parent_reverse_lease_grant')
        self.event(e,c,'write_ACK_consume',copy0=True,copy1=True);self.event(e,c,'write_child_reverse')
        self.event(e,c,'readback_child_accept');merged=e.live[c['die'],c['SM']]['merged']
        self.event(e,c,'readback_ACK_consume',payload=merged*2);self.event(e,c,'readback_child_reverse')
        self.assertTrue(e.live);self.event(e,c,'parent_consumer_accept');self.assertTrue(e.live)
        self.event(e,c,'parent_reverse_lease_grant');self.assertFalse(e.live)
        with self.assertRaisesRegex(ValueError,'replay'):self.acquire(e,c)
    def test_shared_parent_holds_all144_children_per_tile(self):
        first=self.c['shared64'][0];e=m.SelectedEndpoint(self.c);group=e.groups[e.group(first)]
        self.assertEqual(len(group),144)
        for ordinal,cid in enumerate(group):
            c=e.commands[cid];self.acquire(e,c);self.event(e,c,'shared_child_accept',payload=bytes(64) if c['kind']=='shared_write64' else None)
            self.event(e,c,'shared_ACK_consume',payload=bytes(64) if c['kind']=='shared_read64' else None)
            self.event(e,c,'shared_child_reverse')
            if ordinal<len(group)-1:
                with self.assertRaises(ValueError):self.event(e,c,'parent_consumer_accept')
        self.assertTrue(e.live);self.event(e,c,'parent_consumer_accept');self.event(e,c,'parent_reverse_lease_grant')
        self.assertFalse(e.live);self.assertEqual(set(group),e.completed)
    def test_stale_lease_out_of_order_ack_and_unreserved_source_refuse(self):
        c=self.c['RMW'][0];e=m.SelectedEndpoint(self.c)
        bad=self.receipt(c);bad['live']=False
        with self.assertRaises(ValueError):e.acquire(c['id'],lease=1,owner_receipt=bad)
        self.acquire(e,c)
        with self.assertRaises(ValueError):e.event(c['id'],lease=2,event='read_child_accept')
        with self.assertRaises(ValueError):self.event(e,c,'read_ACK_consume',payload=bytes(1024))
        self.event(e,c,'read_child_accept')
        with self.assertRaisesRegex(ValueError,'old mirror tails'):self.event(e,c,'read_ACK_consume',payload=bytes(512)+bytes([1])*512)
        with self.assertRaisesRegex(ValueError,'paired RF'):self.event(e,c,'read_ACK_consume',payload=bytes(512))
        with self.assertRaisesRegex(ValueError,'CACHE_SOURCE_BINDING'):e.cache_accept(die=0,bank=0,address=0)
    def test_shared_rows_and_source_sector_mutation_refuse(self):
        for which in ('address','sector'):
            s=copy.deepcopy(self.s)
            if which=='address':s['shared64.json.gz']['calls']['10:0:0']['commands'][0]['scratch_byte_address']=64
            else:s['shared_execution.json.gz']['control_disk_journal_events'][0]['events'][0]['identity']['sector']+=1
            with self.assertRaises(ValueError):m.compile_selected(s)
    def test_parent_merge_generation_mutation_refuses(self):
        s=copy.deepcopy(self.s);p=s['H1_PC0.json.gz']['packets'];p[1]['source_owner']=[2,0,1,0,0]
        with self.assertRaisesRegex(ValueError,'owner span'):m.compile_selected(s)
    def test_area_routing_and_fairness_are_not_admitted(self):
        d=self.model;self.assertFalse(d['hardware_admitted']);self.assertFalse(d['engine_build_allowed'])
        self.assertIsNone(d['actual_cache_contender_upper']);self.assertFalse(d['fairness_hardware_credit'])
        self.assertIsNone(d['RMW']['local_routing_tracks_required']);self.assertEqual(d['RMW']['local_reference_edge_delta'],288)
        self.assertEqual(d['RMW']['incremental_I64_RMW_charge'],0)
        self.assertEqual(d['shared64']['production_calls_closed'],0)
        for a in d['composed_area_upper_only'].values():self.assertLess(a['with_RMW_upper_mm2'],a['die_mm2'])
    def test_manifest_and_archive_mutation_refuse(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'archive';shutil.copytree(m.BASE,p)
            (p/'inputs/scratch.sv').write_text('changed')
            with patch.object(m,'BASE',p),self.assertRaisesRegex(ValueError,'source pin'):m.inputs()
    def test_endpoint_rejects_arbitrary_source_commands(self):
        c=copy.deepcopy(self.c);c['RMW'][0]['RF_slot']+=1
        with self.assertRaisesRegex(ValueError,'command source pin'):m.SelectedEndpoint(c)

    def test_all_selected_SM_credits_finite_and_conflict_holds(self):
        e=m.SelectedEndpoint(self.c)
        rows=[next(x for x in self.c['shared64']if x['SM']==i)for i in range(32)]
        for c in rows:self.acquire(e,c)
        self.assertEqual(len(e.live),32)
        for c in rows:
            with self.assertRaisesRegex(ValueError,'retained'):self.acquire(e,c)

if __name__=='__main__':unittest.main()
