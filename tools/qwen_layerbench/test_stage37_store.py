import copy
import unittest
import programme_store as P
import monitor_tail as M
from test_monitor_tail import fixture


def head_manifest():
    m=fixture()
    rec=lambda a,p:dict(addr=a,payload_hex=f'{p:0256x}')
    m['stages'].append(dict(stage=37,slices=[dict(slice=s,
        prog_users=[[rec(a,(1<<456)|(s<<20)|(u<<12)|a) for a in range(6)] for u in range(4)],
        btab=[rec(72+4*a,(37<<20)|(s<<12)|a) for a in range(P.HEAD_BTAB_COUNTS[s])],
        crom=[rec(a,(37<<24)|(s<<12)|a) for a in range(P.HEAD_CROM_COUNTS[s])]) for s in range(12)]))
    return m


def decode(rows,addr):
    return sum(((rows[addr//8]>>(8*b+addr%8))&1)<<b for b in range(266))


class Stage37StoreTest(unittest.TestCase):
    def test_capacity_and_unchanged_transformer_prefix(self):
        m=head_manifest();old=P.logical_images(fixture());new=P.logical_images(m,head_stage37=True)
        self.assertEqual(37*P.STRIDE,3922)
        for s in range(12):self.assertEqual(old[s][:3816],new[s][:3816])
        for u in range(4):
            rows=P.read_rows(37,u,head_stage37=True)
            self.assertEqual((len(rows),min(rows),max(rows)),(88,3816+6*u,3921))
        with self.assertRaisesRegex(ValueError,'36'):P.logical_images(m)
        with self.assertRaisesRegex(ValueError,'finite'):P.read_rows(37,0)
        with self.assertRaisesRegex(ValueError,'zero or one'):P.read_rows(37,0,head_stage37=2)
        with self.assertRaisesRegex(ValueError,'zero or one'):P.logical_images(m,head_stage37=2)

    def test_head_btab_shared_and_gain_user_bank_relocation(self):
        images=P.logical_images(head_manifest(),head_stage37=True)
        for s in range(12):
            for u in range(4):
                writes=[P.relocate_word(images[s][r],u,btab_compact=True,head=True)
                        for r in P.read_rows(37,u,head_stage37=True) if images[s][r]]
                btab=[w>>1027 for w in writes if ((w>>1025)&3)==2]
                crom=[w>>1027 for w in writes if ((w>>1025)&3)==1]
                self.assertEqual(btab,[72+4*i for i in range(P.HEAD_BTAB_COUNTS[s])])
                self.assertEqual(crom,[128*u+i for i in range(P.HEAD_CROM_COUNTS[s])])
                self.assertEqual(len(writes),6+P.HEAD_BTAB_COUNTS[s]+P.HEAD_CROM_COUNTS[s])

    def test_monitor_crosses_two_rows_without_clobbering_head(self):
        m=head_manifest();images=P.logical_images(m,head_stage37=True);tails=M.tails(m,head_stage37=True)
        for lane in range(4):
            physical=P.physical_rows(images[1],lane)
            data=('\n'.join(f'{w:0532x}' for w in physical)+'\n').encode()
            new=[int(w,16) for w in M.repack(data,tails[1],lane,tail_base=3922).splitlines()]
            self.assertEqual(new[:490],physical[:490]);self.assertEqual(new[492:],physical[492:])
            for a in (3920,3921):self.assertEqual(decode(new,a),decode(physical,a))
            for i,w in enumerate(tails[1]):self.assertEqual(decode(new,3922+i),(w>>(266*lane))&((1<<266)-1))
            self.assertEqual(new[491]>>2&sum(1<<(8*b) for b in range(266)),0) # column2 stays empty
            # A nonzero unused suffix must not silently disappear.
            occupied=physical[:];occupied[491]|=1<<2
            with self.assertRaisesRegex(ValueError,'not empty'):
                M.repack(('\n'.join(f'{w:0532x}' for w in occupied)+'\n').encode(),tails[1],lane,tail_base=3922)

    def test_shared_window_and_shape_fail_closed(self):
        m=head_manifest();m['stages'][-1]['slices'][1]['btab'][0]['addr']=68
        with self.assertRaisesRegex(ValueError,'partition'):P.logical_images(m,head_stage37=True)
        m=head_manifest();m['stages'][-1]['slices'][1]['btab'].append(dict(addr=272,payload_hex='0'))
        with self.assertRaisesRegex(ValueError,'shape'):P.logical_images(m,head_stage37=True)
        with self.assertRaisesRegex(ValueError,'shared HEAD'):P.relocate_word(P.encode(2,0,'0'),0,btab_compact=True,head=True)
        m=head_manifest();m['stages'][-1]['slices'][0]['prog_users'][0][0]['addr']=6
        with self.assertRaisesRegex(ValueError,'overlaps monitor'):M.tails(m,head_stage37=True)

if __name__=='__main__':unittest.main()
