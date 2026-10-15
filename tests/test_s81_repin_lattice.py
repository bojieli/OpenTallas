import copy
import importlib.util
import sys
import json
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'/'s81'))
from repin_lattice import pack_lattice_face, translation_period_nm
from assigned_pin_lattice import audit


def row(start,width,desired,period=48,anchor=False):
    return dict(start=start,width=width,desired=desired,period_nm=period,anchored=anchor,w=1)


class LatticePacking(unittest.TestCase):
    def test_collision_and_future_capacity(self):
        r=[row(.012,.096,.8),row(.204,.096,.2)]
        a=pack_lattice_face(r,0,.6)
        self.assertLessEqual(a[0]+.096,a[1]+1e-9)
        self.assertLessEqual(a[1]+.096,.6+1e-9)
        for s,x in zip(r,a):
            self.assertEqual(round((x-s['start'])*1000)%48,0)

    def test_anchors_and_reorder(self):
        r=[row(.012,.096,.18),row(.252,.048,.252,anchor=True),row(.348,.096,.8),row(.492,.096,.4)]
        a=pack_lattice_face(r,0,1,True)
        self.assertEqual(a[1],.252)
        self.assertLessEqual(a[0]+.096,.252+1e-9)
        self.assertGreaterEqual(min(a[2:]),.3-1e-9)
        self.assertLess(a[3],a[2])

    def test_multilayer_and_bad_capacity(self):
        self.assertEqual(translation_period_nm(['M4','M6']),192)
        with self.assertRaisesRegex(ValueError,'capacity'):
            pack_lattice_face([row(.012,.1,.012),row(.204,.1,.204)],0,.2)
        with self.assertRaises(ValueError):
            translation_period_nm(['unknown'])

    def test_actual_c19_corruption_and_source_residue(self):
        r=dict(master='dsfd_sp_su_c',outline_um=[1889.976,10709.256],ports={
            'c_cmd':dict(face='E',layer='M4',bits=85,at=[10705.176,.048],uniform=True,depth=.192),
            'c_done':dict(face='E',layer='M4',bits=9,at=[10702.52,.048],uniform=True,depth=.192),
            'c_st':dict(face='E',layer='M4',bits=2,at=[10703.,.048],uniform=True,depth=.192)})
        tracks={'M4':(1,48,{12})}
        self.assertEqual(audit(r,tracks)['status'],'FAIL')
        source=copy.deepcopy(r)
        for p,d in [('c_cmd',.396),('c_done',2.252),('c_st',.284)]:
            source['ports'][p]['at'][0]-=d
        self.assertEqual(audit(source,tracks)['status'],'PASS')
        # Old continuous translations destroy common residues; any permitted
        # translation preserves the actual source's valid common origin.
        for i,p in enumerate(source['ports']):
            source['ports'][p]['at'][0]+=(i+1)*.048
        for orient in ['R0','MX','MY','R180']:
            self.assertEqual(audit(source,tracks,orient)['status'],'PASS')

    def test_search_uses_lattice_for_real_lef_groups_and_anchor(self):
        from die_link_repin_search import run
        plan=dict(die=[10,10], insts=[['a','mov',0,0,1,1,'R0','hub'],
                                     ['b','fixed',2,.284,1,1,'R0','stn']],
                  buses=[['data','test',1,[['a','p'],['b','p']]]])
        def macro(name,face):
            rect='0.808 0.096 1.000 0.120' if face=='E' else '0.000 0.096 0.192 0.120'
            return (f'MACRO {name}\n SIZE 1 BY 1 ;\n PIN p[0]\n USE SIGNAL ;\n PORT\n'
                    f' LAYER M4 ;\n RECT {rect} ;\n END\n END p[0]\n'
                    ' PIN ck[0]\n USE SIGNAL ;\n PORT\n LAYER M4 ;\n'
                    ' RECT 0.808 0.864 1.000 0.888 ;\n END\n END ck[0]\n'
                    f'END {name}\n')
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'plan.json').write_text(json.dumps(plan))
            (p/'pins.lef').write_text(macro('mov','E')+macro('fixed','W'))
            result=run(p/'plan.json',p/'pins.lef',p/'out.json',2,{'hub'},False)
            shifts=result['port_shifts_master_frame_um']
            self.assertTrue(shifts)
            self.assertTrue(all(round(r['shift_um']*1000)%48==0 for r in shifts))
            self.assertFalse(any(r['port']=='ck' for r in shifts))


if __name__=='__main__':
    unittest.main()
