import copy
import unittest
import hbm_w6_component_gate as G

class TestTrace(unittest.TestCase):
    def setUp(self):
        self.rows=[]
        edge=0
        for case in (1,2,3):
            identity=(127<<48)|((5 if case==2 else 0)<<45)|(0xfe123456<<13)|((15 if case==1 else 0)<<9)|511
            kinds=G.ORDER.copy()
            if case==2:kinds[1]='simd_ack_retire'
            for kind in kinds:
                edge+=3 if kind=='reverse_CDC' else 2
                self.rows.append(f'W6_EDGE case={case} kind={kind} edge={edge} identity={identity:014x}')
        self.marker='PASS_W6_LOCAL_COMPONENT checks=401 accepted=200 raw=71 protected=144 production_alldrain=0 physical=0'
    def replay(self,rows=None,marker=None):
        return G.verify_trace('\n'.join((self.rows if rows is None else rows)+[self.marker if marker is None else marker]))
    def test_exact_trace(self):self.assertEqual(self.replay()['checks'],401)
    def test_duplicate(self):
        with self.assertRaises(ValueError):self.replay(self.rows+[self.rows[3]])
    def test_missing(self):
        with self.assertRaises(ValueError):self.replay(self.rows[:3]+self.rows[4:])
    def test_reversed(self):
        r=self.rows.copy();r[4],r[5]=r[5],r[4]
        with self.assertRaises(ValueError):self.replay(r)
    def test_stale_generation(self):
        r=self.rows.copy();r[11]=r[11][:-4]+'1fff'
        with self.assertRaises(ValueError):self.replay(r)
    def test_internal_cannot_use_host_ACK(self):
        with self.assertRaises(ValueError):self.replay([r.replace('simd_ack_retire','host_ack') for r in self.rows])
    def test_zero_edge(self):
        r=self.rows.copy();r[1]=r[1].replace('edge=4','edge=2')
        with self.assertRaises(ValueError):self.replay(r)
    def test_assertion_failure(self):
        with self.assertRaises(ValueError):self.replay(self.rows+['FATAL'])
    def test_terminal_missing(self):
        with self.assertRaises(ValueError):self.replay(marker='')
    def test_terminal_duplicate(self):
        with self.assertRaises(ValueError):self.replay(self.rows+[self.marker])
    def test_field_truncated(self):
        r=[]
        for row in self.rows:
            left,value=row.rsplit('identity=',1)
            # Clear the high original-tag byte within the packed55bit wire.
            r.append(left+'identity='+format(int(value,16)&~(0xff<<37),'014x'))
        with self.assertRaises(ValueError):self.replay(r)

if __name__=='__main__':unittest.main()
