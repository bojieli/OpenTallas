import unittest

import programme_store as P


def manifest():
    rec = lambda a, p: dict(addr=a,payload_hex=f'{p:0256x}')
    return dict(schema='opentallas.qwen.mu-table-input.v1',
        parameters=dict(NU=4,PIDX_STRIDE=128,CROM_ROW_STRIDE=128,BTAB_WORD_STRIDE=128),
        source=dict(lowering_commit='4'*40,checkpoint_sha256='5'*64,
                    user_relocation_certificate_sha256='6'*64),
        stages=[dict(stage=st,slices=[dict(slice=s,
            prog_users=[[rec(a,(st << 20) | (s << 8) | u) for a in range(6)] for u in range(4)],
            btab=[rec(4*a,(st << 10) | s) for a in range(P.BTAB_COUNTS[s])],
            crom=[rec(a,(st << 12) | s) for a in range(P.CROM_COUNTS[s])])
            for s in range(12)]) for st in range(1,37)])


class StoreTest(unittest.TestCase):
    def test_full_shape_all_user_stage_accesses_are_finite(self):
        images = P.logical_images(manifest())
        self.assertEqual(P.STRIDE*36,3816)
        for st in range(1,37):
            for u in range(4):
                rows=P.read_rows(st,u)
                self.assertEqual(len(rows),88)
                self.assertEqual(len(set(rows)),88)
                self.assertLess(max(rows),4096)
                for s in range(12):
                    words=[P.relocate_word(images[s][r],u) for r in rows]
                    prog=[w for w in words if (w >> 1024)&1 and ((w >> 1025)&3)==3]
                    self.assertEqual(len(prog),6)
                    self.assertEqual(prog[0]&((1<<1024)-1),(st<<20)|(s<<8)|u)
                    self.assertEqual(prog[0]>>1027,u*64)

    def test_mutable_partitions_never_alias(self):
        for kind,cap in ((1,128),(2,128),(3,64)):
            occupied=set()
            for u in range(4):
                for addr in range(0,cap,4 if kind==2 else 1):
                    a=P.relocate_word(P.encode(kind,addr,'a5'),u)>>1027
                    self.assertNotIn(a,occupied)
                    occupied.add(a)
            physical_rows={1:1024,2:512,3:256}[kind]
            self.assertLess(max(occupied),physical_rows)

    def test_physical_last_stage_and_high_payload_bit(self):
        words=[0]*4096
        words[3815]=P.encode(1,127,f'{1<<1023:x}')
        for lane in range(4):
            physical=P.physical_rows(words,lane)
            # Direct functional macro read at this logical address.
            read=sum(((physical[3815//8]>>(b*8+3815%8))&1)<<b for b in range(266))
            self.assertEqual(read,(words[3815]>>(lane*266))&((1<<266)-1))

    def test_capacity_and_provenance_refused(self):
        for mutate,regex in ((lambda m:m['stages'].pop(),'36'),
            (lambda m:m['source'].pop('user_relocation_certificate_sha256'),'provenance'),
            (lambda m:m['stages'][0]['slices'][0]['prog_users'].pop(),'four'),
            (lambda m:m['stages'][0]['slices'][0].update(btab=[dict(addr=4*i,payload_hex='0') for i in range(19)]),'shape'),
            (lambda m:m['stages'][0]['slices'][0]['crom'][0].update(addr=128),'partition')):
            m=manifest(); mutate(m)
            with self.assertRaisesRegex(ValueError,regex): P.logical_images(m)
        with self.assertRaisesRegex(ValueError,'1024'): P.encode(1,0,f'{1<<1024:x}')
        with self.assertRaisesRegex(ValueError,'finite'): P.read_rows(37,0)
        with self.assertRaisesRegex(ValueError,'user'): P.relocate_word(0,4)


if __name__=='__main__': unittest.main()
