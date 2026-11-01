import copy
import unittest
import hr_state_outputs as H


def fixture():
    f = dict(type='$adff',parameters=dict(WIDTH='1',CLK_POLARITY='1',ARST_POLARITY='0',ARST_VALUE='0'),port_directions=dict(CLK='input',ARST='input',D='input',Q='output'),connections=dict(CLK=[2],ARST=[3],D=[4],Q=[5]),attributes={})
    g = copy.deepcopy(f);g['connections']['D']=[6];g['connections']['Q']=[7]
    o = dict(type='$or',parameters={},port_directions=dict(A='input',B='input',Y='output'),connections=dict(A=[5],B=[7],Y=[8]),attributes={})
    m=dict(cells=dict(f=f,g=g,o=o),netnames=dict(y=dict(bits=[8],attributes={})),ports=dict(ck=dict(direction='input',bits=[2]),rst=dict(direction='input',bits=[3]),d=dict(direction='input',bits=[4,6]),y=dict(direction='output',bits=[8])))
    return dict(modules=dict(top=m))


class Safety(unittest.TestCase):
    def test_private_next_state_and_source_unchanged(self):
        a=fixture();before=copy.deepcopy(a);st,manifest=H.stage(a,'top',['y']);self.assertEqual(a,before)
        m=st['modules']['top'];t=manifest['outputs']['y'];m['netnames'][t['reset']]['bits']=['0']
        gate,receipt=H.finish(st,manifest);new=gate['modules']['top'];q=new['ports']['y']['bits'][0]
        self.assertNotEqual(q,8);self.assertEqual(new['cells']['f'],a['modules']['top']['cells']['f']);self.assertEqual(receipt['added_cycles'],0)
        d=new['netnames'][t['next']]['bits'][0]
        cone=next(c for c in new['cells'].values() if c['connections'].get('Y')==[d]);self.assertEqual(cone['connections']['A'],[4]);self.assertEqual(cone['connections']['B'],[6])
    def test_reject_primary_input(self):
        a=fixture();a['modules']['top']['cells']['o']['connections']['A']=[4]
        with self.assertRaisesRegex(ValueError,'primary input'):H.stage(a,'top',['y'])
    def test_reject_mixed_reset(self):
        a=fixture();a['modules']['top']['cells']['g']['connections']['ARST']=[9]
        with self.assertRaisesRegex(ValueError,'common clock/reset'):H.stage(a,'top',['y'])
    def test_reject_memory(self):
        a=fixture();a['modules']['top']['cells']['f']['type']='$memrd'
        with self.assertRaisesRegex(ValueError,'opaque/non-combinational'):H.stage(a,'top',['y'])
    def test_reject_init(self):
        a=fixture();a['modules']['top']['netnames']['init']=dict(bits=[5],attributes=dict(init='0'))
        with self.assertRaisesRegex(ValueError,'initialized'):H.stage(a,'top',['y'])
    def test_preserve_unknown_combinational_literal(self):
        a=fixture();a['modules']['top']['cells']['o']['connections']['B']=['x']
        st,manifest=H.stage(a,'top',['y']);name=manifest['outputs']['y']['next'];b=st['modules']['top']['netnames'][name]['bits'][0]
        c=next(c for c in st['modules']['top']['cells'].values() if c['connections'].get('Y')==[b]);self.assertEqual(c['connections']['B'],['x'])
    def test_reject_unknown_state_reset(self):
        a=fixture();a['modules']['top']['cells']['f']['parameters']['ARST_VALUE']='x'
        with self.assertRaisesRegex(ValueError,'unknown reset'):H.stage(a,'top',['y'])
    def test_reject_unfolded_reset(self):
        st,manifest=H.stage(fixture(),'top',['y'])
        with self.assertRaisesRegex(ValueError,'reset not folded'):H.finish(st,manifest)


if __name__=='__main__':unittest.main()
