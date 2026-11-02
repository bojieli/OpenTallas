import copy
import json
import tempfile
import unittest
from pathlib import Path
import dv_lower as D
import programme_lower as L
import programme_store as P
import head_norm_object as O
import head_source_lease as H
from test_residual2_calendar_candidate import manifest


class HeadLeaseTest(unittest.TestCase):
    def test_unused_resident_region_includes_real_rope_read_footprint(self):
        m=manifest();m['source']={}
        for st in m['stages']:
            for sl in st['slices']:
                sl['crom']=[dict(addr=63,payload_hex='0')]
                for u,records in enumerate(sl['prog_users']):
                    w=D.su_word(nout=1,nin=64,a=4096*u,bsrc=1,b=1024+2048*u,bsi=1)
                    records[3]['payload_hex']=f'{w<<512:0256x}'
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'m.json';p.write_text(json.dumps(m));c=H.census(p)
        a=H.allocation([c])
        self.assertEqual((c['crom_write_last'],c['crom_read_last']),(1023,1087))
        self.assertEqual((a['gain_base'],a['gain_row'],a['apply_pidx']),(1088,68,16))
        self.assertEqual([u['pidx'] for u in a['users']],[16,144,272,400])
        self.assertEqual(a['users'][-1]['crom_end'],7616)
        bad=copy.deepcopy(c);bad['crom_read_last']=1690
        with self.assertRaisesRegex(ValueError,'capacity'):H.allocation([bad])

    def test_real_source_link_uses_sparse_head_pair_and_user_banks(self):
        own=dict(slice_rtl='s8',residual=dict(blocks_per_slice=[list(range(s,32,12)) for s in range(12)]))
        obj=O.build(list(range(4096)),own)
        alloc=H.allocation([dict(crom_read_last=1087,crom_write_last=1023,prog_indices=list(range(12)))])
        bt=[dict(slice=s,addr=72+4*i,payload_hex='1234') for s in range(12) for i in range(P.HEAD_BTAB_COUNTS[s])]
        st=H.link_stage(obj,bt,alloc)
        self.assertEqual(sum(len(s['btab']) for s in st['slices']),298)
        self.assertEqual(sum(len(s['crom']) for s in st['slices']),256)
        for sl in st['slices']:
            for u,rows in enumerate(sl['prog_users']):
                self.assertEqual(len(rows),1);self.assertEqual(rows[0]['addr'],8)
                payload=int(rows[0]['payload_hex'],16)
                self.assertEqual(payload>>512,0) # unwritten instruction17 is never issued
                f=D.su_unpack(payload)
                self.assertEqual((f['a'],f['b'],f['c']),(4096*u,4096*u+400,2048*u+1088))
                self.assertEqual(f['d'],D.W_X|128*sl['slice'])
        source=[dict(eaddr=8,payload=st['slices'][0]['prog_users'][0][0]['payload_hex'])]
        with self.assertRaisesRegex(ValueError,'six'):L.prog_users(source)
        self.assertEqual(len(L.prog_users(source,head=True)),4)
        with self.assertRaisesRegex(ValueError,'distinct'):L.prog_users(source*2,head=True)

if __name__=='__main__':unittest.main()
