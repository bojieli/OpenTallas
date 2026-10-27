import copy
from types import SimpleNamespace
import unittest
import emitter as E
from hgi_sim.records import Rec,MDesc


class Align(unittest.TestCase):
    def test_value_objects_align_writers_and_readers(self):
        r=Rec('FUSED','HC_PRE_NORM',desc={'A':MDesc(base=10,n=32),'O':MDesc(base=100,n=32)})
        objs=[dict(kind='row_array',rows=2,stride=32,size=32,lo=lo,hi=lo+32,t0=0,t1=4)for lo in [10,100]]
        c2o={0:(0,0),1:(1,0)};opmap={(0,'A',0):0,(0,'O',0):1}
        self.assertEqual(E.constrain_fused_objects([r],{'ex':[(0,0,None)]},objs,c2o,SimpleNamespace(f=lambda x:x),opmap),2)
        self.assertTrue(all(o['stride']==256 for o in objs))
        E.place(objs)
        self.assertTrue(all(o['base']%256==0 for o in objs))
        # Every consumer uses this same value object and row stride through amap.
        self.assertEqual(E.amap(objs[1],100),0)
        self.assertEqual(objs[1]['base']+objs[1]['stride'],objs[1]['base']+256)

    def test_incompatible_internal_offset_refuses(self):
        r=Rec('FUSED','HC_PRE_NORM',desc={'A':MDesc(base=0,n=8),'O':MDesc(base=8,n=8)})
        o=dict(kind='single',rows=1,stride=0,size=16,lo=0,hi=16,t0=0,t1=4)
        with self.assertRaisesRegex(ValueError,'phase conflict'):
            E.constrain_fused_objects([r],{'ex':[(0,0,None)]},[o],{0:(0,0),1:(0,0)},SimpleNamespace(f=lambda x:x),{(0,'A',0):0,(0,'O',0):1})

    def test_default_addressing_unchanged(self):
        objs=[dict(kind='single',rows=1,stride=0,size=8,lo=0,hi=8,t0=0,t1=4),
              dict(kind='single',rows=1,stride=0,size=24,lo=0,hi=24,t0=0,t1=4)]
        ff=E._first_fit_by_time(copy.deepcopy(objs),8)
        greedy=E._greedy_by_size(copy.deepcopy(objs),8)
        self.assertEqual(ff,(40,{1:8,0:32}))
        self.assertEqual(greedy,(40,{1:8,0:32}))

if __name__=='__main__':unittest.main()
