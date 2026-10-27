import importlib.util
import pathlib
import unittest
S=importlib.util.spec_from_file_location('anchors',pathlib.Path(__file__).parents[1]/'hbm_root_anchors.py');m=importlib.util.module_from_spec(S);S.loader.exec_module(m)

class AnchorTests(unittest.TestCase):
    def graph(self):
        return {'modules':{'ot_hnx_fused_hub_n4ext':{'ports':{
            'up_nw':{'direction':'input','bits':[1]},'up_ne':{'direction':'input','bits':[2]},
            'down_nw':{'direction':'output','bits':[3]},'down_ne':{'direction':'output','bits':[4]}},
            'cells':{'u':{'type':'child','connections':{'a':[1],'b':[2],'o1':[3],'o2':[4]}}}},
            'child':{'ports':{'a':{'direction':'input','bits':[10]},'b':{'direction':'input','bits':[11]},
                'o1':{'direction':'output','bits':[12]},'o2':{'direction':'output','bits':[12]}},
                'cells':{name:{'type':'DFFHQNx1_ASAP7_75t_R','connections':{'D':[d],'QN':[q]},
                    'port_directions':{'D':'input','QN':'output'}} for name,d,q in [('fa',10,12),('fb',11,13)]}}}}

    def test_hierarchical_output_alias_preserves_both_ports(self):
        a=m.collect(self.graph());self.assertEqual(a['resolved_bits'],4)
        rows={r['port']:r for r in a['rows']}
        self.assertEqual(rows['down_nw']['anchors'],rows['down_ne']['anchors'])
        self.assertEqual(rows['up_nw']['anchors'][0]['cell'],'u/fa')

    def test_functional_comb_logic_cannot_be_claimed_as_pin_flop(self):
        g=self.graph();g['modules']['child']['cells']['fa']['type']='XOR2x1_ASAP7_75t_R'
        a=m.collect(g);self.assertGreater(a['open_bits'],0)

if __name__=='__main__':unittest.main()
