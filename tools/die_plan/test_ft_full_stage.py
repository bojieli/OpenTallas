import copy
import tempfile
import unittest
from pathlib import Path
from ft_full_stage import validate, install

class FullStageTests(unittest.TestCase):
    def setUp(self):
        self.t = dict(module='m', outline_um=[1000,100],ft_slots=[dict(name='ft0',stations=4,width=0,in_face='W',out_face='E')])
        self.doc = dict(schema='opentallas.ft_full_stage.v1',module='m',outline_um=[1000,100],slots={'ft0':dict(self.t['ft_slots'][0],targets=[dict(stage=j,bit=0,name=f'q{j}',master='DFF',xy=[j*330,10],size=[1.08,.27]) for j in range(4)])})
    def test_full_inventory(self):
        validate(self.t,self.doc)
    def test_missing_or_aliased(self):
        for mutation in ('missing','alias','stage','master','outside','hop'):
            d=copy.deepcopy(self.doc);r=d['slots']['ft0']['targets']
            if mutation=='missing':r.pop()
            if mutation=='alias':r[1]['name']=r[0]['name']
            if mutation=='stage':r[1]['stage']=0
            if mutation=='master':r[1]['master']=''
            if mutation=='outside':r[1]['xy']=[1000,10]
            if mutation=='hop':r[1]['xy']=[800,10]
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):validate(self.t,d)
    def test_default_byte_unchanged(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);(p/'face_flops.tcl').write_text('unchanged')
            install(self.t,'plan.json',p)
            self.assertEqual((p/'face_flops.tcl').read_text(),'unchanged')
            self.assertEqual(len(list(p.iterdir())),1)
    def test_old_sites_conflict(self):
        self.t['ft_slots'][0]['bit_sites_um']=[[[0,0]]]
        with self.assertRaises(ValueError):validate(self.t,self.doc)

if __name__=='__main__':unittest.main()
