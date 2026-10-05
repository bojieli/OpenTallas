from pathlib import Path
import sys,unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import deepseek_hbm_complete_index_ingress as I
class Ingress(unittest.TestCase):
    def test_all_codes_low_nibble_order_scale_boundary(self):
        rows=np.tile(np.arange(64,dtype=np.uint8),(33,1));rows=np.concatenate([rows,np.tile(np.array([1,2,127,252],np.uint8),(33,1))],axis=1)
        units,exp,m=I.unpack(rows)
        expected=np.array(I.X.K.UNITS,np.int32)[np.stack([rows[:,:64]&15,rows[:,:64]>>4],axis=-1).reshape(33,128)]
        self.assertTrue(np.array_equal(units,expected));self.assertTrue(np.array_equal(exp,rows[:,64:].astype(np.int32)-126));self.assertGreater(m.counts['IEQ'],0)
        with self.assertRaises(ValueError):I.unpack(np.zeros((1,68),np.uint8))
        with self.assertRaises(ValueError):I.unpack(np.zeros((65,68),np.uint8))
    def test_banks_capacity_and_no_alias(self):
        q={I.address('query',t,h) for t in range(128) for h in range(32)};k={I.address('key',t,r) for t in range(128) for r in range(64)}
        self.assertFalse(q&k);self.assertEqual(len(q|k),12288);self.assertLess(I.END,65536)
        for t in range(128):
            self.assertEqual(len({I.address('query',t,h)//4%32 for h in range(32)}),32)
            self.assertEqual(len({I.address('key',t,r)//4%32 for r in range(32)}),32)
    def test_sector_coverage_owner_loop_and_leases(self):
        for start in [0,7,8,1023,8191]:
            c=I.tile_contract(95,start,64,256);self.assertTrue(all(1<=r['length_sectors']<=16 for r in c['requests']))
            sectors=[s for r in c['requests'] for s in range(r['sector_address'],r['sector_address']+r['length_sectors'])]
            self.assertEqual(sectors,list(range(c['valid_byte_range'][0]//32,(c['valid_byte_range'][1]+31)//32)))
            self.assertTrue(all((i//8)%96==95 for i in c['global_ids']));self.assertEqual(len(set(c['global_ids'])),64);self.assertIsNone(c['qualified_cycles']);self.assertEqual(len(c['lease_dependencies']),7)
if __name__=='__main__':unittest.main()
