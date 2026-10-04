"""Focused accepted-storage/partition boundaries; no payload image or engine run."""
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import dsrom_s81_head12_partition as P
from dsrom_s81_head_source_binding import HeadSourceBinding


class Head12PartitionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inv,cls.part,cls.pins=P.compile_inventory()

    def test_globals_retained_and_actual_drafter_complete(self):
        old=json.loads(P.OLD.read_text())
        layout=self.inv['dedicated_storage']
        self.assertEqual(layout['global_tensors'],old['dedicated_storage']['global_tensors'])
        ds=layout['dspark_storage']
        self.assertEqual((ds['pair_start'],ds['pairs'],ds['bytes'],len(ds['tensors'])),
                         (5051,15131,7932874632,2401))
        end=0
        for t in ds['tensors']:
            self.assertEqual(t['storage_byte_range'],[end,end+t['bytes']]);end+=t['bytes']
        self.assertEqual(end,ds['bytes'])
        self.assertTrue(any(t['tensor']=='mtp.2.markov_head.head.weight' for t in ds['tensors']))
        self.assertTrue(any(t['tensor']=='mtp.2.confidence_head.proj.weight' for t in ds['tensors']))

    def test_twelve_physical_owners_four_arithmetic_ranks(self):
        self.assertEqual((self.inv['TP'],self.inv['head_dies'],self.inv['total_dies']),(4,12,372))
        self.assertEqual(sum(d['owned_pairs'] for d in self.part['by_die']),20182)
        self.assertEqual(sum(d['head_weight_pairs'] for d in self.part['by_die']),2525)
        self.assertEqual({d['head_weight_pairs'] for d in self.part['by_die']},{210,211})
        for r in range(4):
            phases=[p for p in self.part['head_phases'] if p['arithmetic_rank']==r]
            self.assertEqual({p['storage_die'] for p in phases},set(range(12)))
            cursor=r*32320*5120
            for p in phases:
                self.assertEqual(p['tensor_element_range'][0],cursor)
                cursor=p['tensor_element_range'][1]
                self.assertEqual(p['first_K']%8,0)
                self.assertEqual(p['final_K_exclusive']%8,0)
            self.assertEqual(cursor,(r+1)*32320*5120)

    def test_compiler_addresses_and_literal_program_stable(self):
        new=HeadSourceBinding();old=HeadSourceBinding(P.OLD.parent)
        for rank in range(4):
            for row,k in ((0,0),(17,819),(32319,5119)):
                a=new.head_address(rank,row,k);b=old.head_address(rank,row,k)
                self.assertEqual((a['byte_offset'],a['global_pair'],a['physical_row'],a['bit_range']),
                                 (b['byte_offset'],b['global_pair'],b['physical_row'],b['bit_range']))
                self.assertEqual(a['pair']*12+a['die'],a['global_pair'])
        kw=dict(opt_in=True,entry14=17,pc_base=123)
        self.assertEqual(new.compile(**kw)['instructions'],old.compile(**kw)['instructions'])
        self.assertEqual(new.model()['head_storage_dies'],12)

    def test_drafter_byte_home_and_cross_tensor_word(self):
        ds=self.inv['dedicated_storage']['dspark_storage']
        # Exact bounded raw service fixture; no values supplied to an arithmetic engine.
        class Source:
            def __init__(self):self.calls=[]
            def raw(self,tensor,offset,n):
                self.calls.append((tensor,offset,n));return bytes([len(tensor)%256])*n
        source=Source()
        for t in ds['tensors']:
            for offset in (0,t['bytes']-1):
                a=P.drafter_address(self.inv,t['tensor'],offset)
                byte=(a['global_pair']-5051)*P.PAIR_BYTES+(a['mb']*8192+
                      a['physical_row']*2+a['parity'])*32+a['bit_range'][0]//8
                self.assertEqual(byte,t['storage_byte_range'][0]+offset)
        last=ds['tensors'][-1]
        a=P.drafter_address(self.inv,last['tensor'],last['bytes']-1)
        raw=P.drafter_word(self.inv,source,a['storage_die'],a['local_pair']*4+
                           a['mb']*2+a['parity'],a['physical_row'])
        self.assertEqual(len(raw),32)
        self.assertEqual(raw[-24:],bytes(24))
        self.assertEqual(sum(n for _,_,n in source.calls),8)
        with self.assertRaises(ValueError):P.drafter_word(self.inv,source,12,0,0)
        with self.assertRaises(ValueError):P.drafter_word(self.inv,source,0,0,0)

    def test_area_delta_and_power_label(self):
        m=P.model(self.inv,self.part)
        self.assertEqual(m['die_delta'],4)
        self.assertTrue(m['area_screen_fits'])
        self.assertLess(m['max_head_die_mm2'],840.84)
        self.assertAlmostEqual(m['head_silicon_delta_mm2_vs_corrected8'],2272.388)
        self.assertGreater(m['power']['static_icg_delta_proxy_kW'],0)
        self.assertFalse(m['power']['power_qualified'])
        self.assertFalse(m['physical_admission'])


if __name__=='__main__':unittest.main()
