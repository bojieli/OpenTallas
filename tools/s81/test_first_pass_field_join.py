import copy
import unittest
from first_pass_field_join import bind_pairs, bind_cfg_ports
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from dsrom_s73_pair1 import RaggedPool


class ActualChildren(unittest.TestCase):
    def setUp(self):
        self.layout = dict(frames={0: dict(pairs=[0, 1], origin_um=[0, 0], outline_um=[20, 20])}, bf_ids={0}, pair_count=1)
        masters={'e0':'dsfd_bf_front_static','s0':'ot_s81_cfg7_seq_bfp','e0w':'dsfd_bf_col','e0e':'dsfd_bf_col',**{f'c0_{j}':'ot_rom_4096x72_m8' for j in range(7)}}
        self.insts=[dict(name=n,master=m,region='frame_0',x=1,y=2,w=3,h=4) for n,m in masters.items()]

    def test_actual_children(self):
        self.assertEqual(len(bind_pairs(self.insts,self.layout)[0]['actual_children']),11)

    def test_absent_cfg_rom_rejected(self):
        with self.assertRaisesRegex(AssertionError,'missing actual FIELD child'):
            bind_pairs([i for i in self.insts if i['name']!='c0_3'],self.layout)

    def test_wrong_actual_root_rejected(self):
        self.insts[0]['region']='frame_1'
        with self.assertRaisesRegex(AssertionError,'FIELD root mismatch'):bind_pairs(self.insts,self.layout)

    def test_wrong_master_rejected(self):
        self.insts[0]['master']='latency_only_surrogate'
        with self.assertRaisesRegex(AssertionError,'unexpected FIELD master'):bind_pairs(self.insts,self.layout)

    def test_geometry_not_just_name(self):
        self.insts[0]['x']=30
        with self.assertRaisesRegex(AssertionError,'outside frame'):bind_pairs(self.insts,self.layout)

    def test_disconnected_rom_result_rejected(self):
        pairs=bind_pairs(self.insts,self.layout)
        buses=[["ra_0","rom_a",12,[["s0","a"]]+[[f"c0_{j}","a"] for j in range(7)]]]
        for j in range(7):
            buses += [[f"rc_0_{j}","rom_ce",1,[["s0",f"ce{j}"],[f"c0_{j}","ce"]]], [f"rq_0_{j}","rom_q",72,[[f"c0_{j}","rd"],["s0",f"q{j}"]]]]
        self.assertEqual(bind_cfg_ports(buses,pairs),15)
        buses[-1][3][-1][1]='q0'
        with self.assertRaisesRegex(AssertionError,'actual CFG port mismatch'):bind_cfg_ports(buses,pairs)

    def test_duplicate_actual_name_rejected(self):
        with self.assertRaisesRegex(AssertionError,'duplicate instance name'):bind_pairs(self.insts+[copy.copy(self.insts[0])],self.layout)

class ExactBFSites(unittest.TestCase):
    def test_exact_sites_are_preserved(self):
        regions=[[2,1] for _ in range(128)]
        exact=list(range(1,256,2))
        old=RaggedPool(256,128,regions=regions)
        fixed=RaggedPool(256,128,regions=regions,bf_sites=exact)
        self.assertNotEqual(old.bf,set(exact))
        self.assertEqual(fixed.bf,set(exact))
        self.assertEqual(fixed.byreg[0,'bf16'],[1])

    def test_wrong_region_counts_rejected(self):
        with self.assertRaises(AssertionError):
            RaggedPool(256,128,regions=[[2,1] for _ in range(128)],bf_sites=range(128))

if __name__=='__main__': unittest.main()
