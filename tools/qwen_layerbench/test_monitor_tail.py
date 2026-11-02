import copy
import unittest
import monitor_tail as M
import programme_store as P
from test_programme_store import manifest


def fixture():
    m=manifest();m['parameters']=copy.deepcopy(P.NATIVE_COMPACT_PARAMETERS)
    for stage in m['stages']:
        for sl in stage['slices']:
            for u,records in enumerate(sl['prog_users']):
                for r in records:
                    # Distinct high and low native words exercise half order and every lane.
                    lo=(1<<456)|(sl['slice']<<32)|(u<<16)|2*r['addr']
                    hi=(1<<455)|(sl['slice']<<40)|(u<<24)|(2*r['addr']+1)
                    r['payload_hex']=f'{lo|(hi<<512):0256x}'
    return m


class MonitorTailTest(unittest.TestCase):
    def test_native_copies_and_independent_physical_decode(self):
        m=fixture();tails=M.tails(m)
        for sid,words in tails.items():
            rows=[M.physical_tail(words,lane) for lane in range(4)]
            for u in range(4):
                src=m['stages'][0]['slices'][sid]['prog_users'][u]
                for pair,pcs in enumerate(((3,3),(11,10))):
                    got=sum(sum(((rows[lane]>>(8*bit+2*u+pair))&1)<<(266*lane+bit) for bit in range(266)) for lane in range(4))
                    self.assertEqual((got>>1024)&7,7)  # valid PROG kind3
                    self.assertEqual(got>>1027,6+pair)
                    for half,pc in enumerate(pcs):
                        expected=(int(src[pc//2]['payload_hex'],16)>>(512*(pc%2)))&((1<<512)-1)
                        self.assertEqual((got>>(512*half))&((1<<512)-1),expected)

    def test_reject_noninvariant_monitor_and_bad_profile(self):
        m=fixture();r=m['stages'][-1]['slices'][7]['prog_users'][3][5]
        r['payload_hex']=f'{int(r["payload_hex"],16)^1:x}'
        with self.assertRaisesRegex(ValueError,'noninvariant'):M.tails(m)
        m=fixture();m['parameters']['PIDX_STRIDE']=64
        with self.assertRaisesRegex(ValueError,'ABI'):M.tails(m)

    def test_reject_instruction_padding_instead_of_truncating(self):
        m=fixture();r=m['stages'][0]['slices'][0]['prog_users'][0][1]
        r['payload_hex']=f'{int(r["payload_hex"],16)|(1<<457):x}'
        with self.assertRaisesRegex(ValueError,'padding'):M.tails(m)

    def test_only_tail_row_changes_and_free_rows_are_really_empty(self):
        rows=[f'{i+1:0532x}' for i in range(477)]+['0'*532]*35
        old=('\n'.join(rows)+'\n').encode()
        new=M.repack(old,M.tails(fixture())[0],0).decode().splitlines()
        self.assertEqual(new[:477],rows[:477]);self.assertEqual(new[478:],rows[478:])
        self.assertNotEqual(new[477],rows[477])
        for occupied in (477,478,511):
            bad=rows[:];bad[occupied]='1'
            with self.assertRaisesRegex(ValueError,'not empty'):M.repack(('\n'.join(bad)+'\n').encode(),[0]*8,0)


if __name__=='__main__':unittest.main()
