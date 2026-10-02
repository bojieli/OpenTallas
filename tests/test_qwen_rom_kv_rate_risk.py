"""Source/FSM/resource tests only; never a new numerical decode position."""
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from uarch_model_qwen_kv_rate_risk import FinitePrefetchReplay, owner_interval, build
from qwen_rom_persistent_kv_g0 import Homes, Owner


def event(kind,tick=0,**kw):
    return dict(event=kind,tick_1over3ps=tick,owner=dict(user=0,rank=0,layer=0,epoch=1),
                stack=0,tag=3,beat=0,base_sector=100,sectors=1,write=False,**kw)


class RateRiskTests(unittest.TestCase):
    def test_literal_owner_14_edge_throughput_not_32_parallel_PC_owners(self):
        r=owner_interval()
        self.assertEqual(r['accepted'],[0,14,28,42,56])
        self.assertEqual(r['consumed'],[13,27,41,55,69])
        self.assertEqual(r['min_accept_interval_edges'],14)

    def test_source_tail_bypass_stack_distribution_is_not_uniform_V(self):
        h=Homes();owner=Owner(0,0,0,1)
        k=[set() for _ in range(4)];v=[set() for _ in range(4)]
        for head in range(2):
            for pos in range(8160,8192):
                for dim in range(128):
                    key,off=h.byte(owner,'K',head,pos,dim); k[key[2]].add((key,off))
            for dim in range(128):
                key,off=h.byte(owner,'V',head,8191,dim);v[key[2]].add((key,off))
        self.assertEqual(list(map(len,k)),[2048]*4)
        self.assertEqual(list(map(len,v)),[0,0,0,256])

    def test_full_prefetch_lease_fills_visible_before_reverse_retirement(self):
        r=FinitePrefetchReplay()
        r.apply(event('window',slot=0))
        r.apply(event('allocate'))
        r.apply(event('command',3000))
        r.apply(event('raw_return',6000))
        r.apply(event('lookup',9000))
        with self.assertRaises(ValueError):r.apply(event('owned_consumed',45000))
        r.apply(event('owned_consumed',48000))
        r.apply(event('fill',50000,valid_bytes=32,assembly_slot=0,window=0,tile=0,row=0))
        with self.assertRaisesRegex(ValueError,'visible'):r.apply(event('credit',50000))
        with self.assertRaises(ValueError):r.apply(event('visible',52500,assembly_slot=0))
        r.apply(event('visible',55000,assembly_slot=0))
        r.apply(event('credit',57000));r.apply(event('grant_consumed',60000))
        r.apply(event('retire',63000));r.apply(event('window_drain',65000,slot=0))
        self.assertEqual(r.verdict()['status'],'PASS_FINITE_RESOURCE_REPLAY')
        self.assertEqual((r.read_bytes,r.fill_bytes),(32,32))
        self.assertFalse(r.verdict()['physical_build_ready'])

    def test_no_capacity_free_second_layer_reuse_before_drain(self):
        r=FinitePrefetchReplay();r.apply(event('window',slot=0))
        e=event('window',slot=0);e['owner']['layer']=1
        with self.assertRaises(ValueError):r.apply(e)
        e['slot']=1;r.apply(e)
        e['slot']=2
        with self.assertRaises(ValueError):r.apply(e)

    def test_sixteen_outstanding_and_request_ingress_are_real_bounds(self):
        r=FinitePrefetchReplay()
        for n in range(16):
            e=event('allocate',n*99000);e.update(tag=n,sectors=32,base_sector=n*128)
            r.apply(e)
        e=event('allocate',16*99000);e.update(tag=16,sectors=32,base_sector=2048)
        with self.assertRaises(ValueError):r.apply(e)
        self.assertEqual(r.max_outstanding,16)
        r=FinitePrefetchReplay();r.apply(event('allocate'))
        e=event('allocate',3000);e['tag']=4
        with self.assertRaises(ValueError):r.apply(e)

    def test_no_simultaneous_owner_lookup_or_unissued_return(self):
        r=FinitePrefetchReplay();r.apply(event('allocate'))
        with self.assertRaises(ValueError):r.apply(event('raw_return'))
        r.apply(event('command',3000));r.apply(event('raw_return',6000));r.apply(event('lookup',9000))
        with self.assertRaises(ValueError):r.apply(event('lookup',12000))
        r.apply(event('owned_consumed',48000))
        with self.assertRaises(ValueError):r.apply(event('lookup',51000))

    def test_current_literal_capacity_area_and_rate_block_3k(self):
        r=build('7e53adf605ec3647a4dc59a5e45373887f4778ea')
        self.assertEqual(r['logical_bytes']['read_rank_token'],144*1024*1024)
        self.assertEqual(r['logical_bytes']['write_rank_token'],18432)
        self.assertEqual(r['logical_bytes']['conditional_selected_closing_K_V_write_rank'],156672)
        self.assertEqual(r['actual_storage']['raw_capacity_bytes_per_rank'],12*1024*1024)
        self.assertGreater(r['area']['resident_literal_macro_increment_mm2'],r['area']['other_services_budget_mm2'])
        self.assertGreater(r['token_lower_bounds']['perfect_all_compute_overlap_s'],.016)
        self.assertLess(r['token_lower_bounds']['conditional_max_token_rate'],61)
        self.assertEqual(r['three_k_requirement']['shared_64B_fill_lanes_min'],6)
        self.assertFalse(r['physical_build_ready'])
        self.assertIsNone(r['actual_ports']['actual_sustained_HBM_bandwidth'])

    def test_per_PC_return_queue_32_is_not_stack_unbounded_capacity(self):
        r=FinitePrefetchReplay()
        for n in range(16):
            e=event('allocate',n*99000);e.update(tag=n,sectors=32,base_sector=n*(1<<20))
            r.apply(e)
        tick=16*99000
        for n in range(8):
            for b in range(4):
                tick+=3000;e=event('command',tick);e.update(tag=n,beat=b);r.apply(e)
                tick+=3000;e['event']='raw_return';e['tick_1over3ps']=tick;r.apply(e)
        tick+=3000;e=event('command',tick);e.update(tag=8,beat=0);r.apply(e)
        e['event']='raw_return';e['tick_1over3ps']=tick+3000
        with self.assertRaisesRegex(ValueError,'32 return SRAM'):r.apply(e)

    def test_write_backing_and_ack_are_not_read_return_fill(self):
        r=FinitePrefetchReplay();e=event('allocate');e['write']=True;r.apply(e)
        r.apply(event('command',3000))
        with self.assertRaises(ValueError):r.apply(event('raw_return',6000))
        with self.assertRaises(ValueError):r.apply(event('write_backing',24000))
        r.apply(event('write_backing',27000));r.apply(event('lookup',30000))
        r.apply(event('owned_consumed',69000))
        for kind,tick in [('credit',72000),('grant_consumed',75000),('retire',78000)]:r.apply(event(kind,tick))
        self.assertEqual(r.verdict()['status'],'PASS_FINITE_RESOURCE_REPLAY')
        self.assertEqual(r.read_bytes,0)


if __name__=='__main__':unittest.main()
