import copy
import tempfile
import json
from types import SimpleNamespace
from unittest.mock import patch
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

    def test_analytic_readers_use_all_stages(self):
        import ft_full_stage, taps, die_hop_scan, ft_station_probe
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);(p/'map.json').write_text(json.dumps(self.doc))
            self.t['ft_full_stage_placement_file']='map.json'
            P=SimpleNamespace(types={'t':self.t},path=p/'plan.json')
            pins=[('ft0_i',0,'M4',0,10,'W'),('ft0_o',0,'M4',1000,10,'E')]
            with patch('gen_phys.type_pins',return_value=pins):
                _, chains=die_hop_scan.type_tables(P,'t')
                expected=[ft_full_stage.centre(r) for r in self.doc['slots']['ft0']['targets']]
                self.assertEqual(chains['ft0'][0],expected)
                self.assertEqual([r[:2] for r in taps.planned_sinks(P,'t')],expected)
                with patch('gen_phys.type_pins',return_value=[]):
                    self.assertEqual([r[:2] for r in taps.planned_sinks(P,'t')],expected)
                self.assertEqual(ft_station_probe.station_sites(P,'t',self.t['ft_slots'][0],1),[[list(x)] for x in expected])
    def test_lane_hops_preserve_pin_detour(self):
        import ft_full_stage, schema
        P=SimpleNamespace(parts={'a':{'type':'t'}},lanes={'L':{'ports':['i','o']}},
            ports={'i':{'src':{'part':schema.DIE_PART},'dst':{'part':'a','bus':'ft0_i'}},
                   'o':{'src':{'part':'a','bus':'ft0_o'},'dst':{'part':schema.DIE_PART}}},
            lane_crossings=lambda lid:[('a','ft0','i','o')],to_die=lambda part,xy:xy,
            port_point=lambda pid:(0,10) if pid=='i' else (1000,10))
        table=({'ft0_i':{0:(0,10,'W')},'ft0_o':{0:(1000,10,'E')}},
               {'ft0':{0:[(10,10),(340,10),(670,10),(990,10)]}})
        with patch('die_hop_scan.type_tables',return_value=table), patch('schema.port_pins_count',return_value=1):
            self.assertEqual(ft_full_stage.lane_hops(P,'L'),[10,330,330,320,10])

    def test_synthetic_g2_fails_closed(self):
        import g2
        self.t['ft_full_stage_placement_file']='map.json'
        with self.assertRaisesRegex(ValueError,'native kit actual geometry'):
            g2.part_probe(SimpleNamespace(types={'t':self.t}),'t','unused')

if __name__=='__main__':unittest.main()
