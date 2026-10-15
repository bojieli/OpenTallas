"""Safety checks for pin-based proposed group moves."""
import importlib.util
from pathlib import Path
import unittest
P=Path(__file__).resolve().parents[1]/'group_placement_opt.py'
spec=importlib.util.spec_from_file_location('group_placement_opt',P)
G=importlib.util.module_from_spec(spec);spec.loader.exec_module(G)


def lef():
    lines=['MACRO tile','SIZE 20 BY 20 ;']
    for i in range(4):
        lines += [f'PIN p[{i}]','PORT','LAYER M4 ;',f'RECT 19.95 {3+i} 20.0 {3.04+i} ;','END',f'END p[{i}]']
    return '\n'.join(lines+['END tile'])


def plan():
    return dict(insts=[['left','tile',0,50,20,20,'R0'],['move','tile',100,50,20,20,'R0'],['right','tile',300,50,20,20,'R0']],
                buses=[['leftwide','data',4,[['left','p'],['move','p']]],['rightthin','data',1,[['move','p'],['right','p']]]])


class GeometryTests(unittest.TestCase):
    def model(self,p=None):return G.Model(p or plan(),[lef()],[500,500])
    def test_all_incident_edges_prevent_favorable_subset(self):
        m=self.model()
        self.assertIsNone(m.proposal('move right',{'move':(50,0)}))
        p=m.proposal('move left',{'move':(-50,0)})
        self.assertAlmostEqual(p['saved_bit_um'],150.)
        self.assertEqual(len(p['before']['top20_routes']),2)
    def test_translated_actual_pin_distances_and_obstacle_halo(self):
        m=self.model()
        self.assertFalse(m.legal({'move':(-70,0)})) # 10um gap violates20um halo
        self.assertFalse(m.legal({'move':(-120,0)}))
        self.assertTrue(m.legal({'move':(-60,0)}))
        p=m.proposal('move left',{'move':(-60,0)})
        self.assertAlmostEqual(p['after']['max_um'],260.)
        self.assertEqual(p['placement_patch'][0]['x_um'],40.)
    def test_missing_incident_pins_block_group(self):
        p=plan();p['buses'].append(['unknown','data',1,[['move','absent'],['right','p']]])
        m=self.model(p)
        self.assertEqual(len(m.missing),1)
        self.assertIsNone(m.proposal('move',{'move':(-50,0)}))
        result,blocked=G.search(m,{'move':['move']},100,50)
        self.assertEqual(blocked,['move']);self.assertEqual(result,[])
    def test_internal_group_positions_preserved(self):
        m=self.model()
        self.assertTrue(m.legal({'left':(0,50),'move':(0,50)}))
        mm=m.metrics(m.edges,{'left':(0,50),'move':(0,50)})
        left=next(e for e in mm['top20_routes'] if e['bus']=='leftwide')
        self.assertAlmostEqual(left['sum_bit_um'],400.)

if __name__=='__main__':unittest.main()
