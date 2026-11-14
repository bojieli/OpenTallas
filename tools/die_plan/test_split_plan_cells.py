import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import split_plan_cells as M
from type_split import SplitError


class Projection(unittest.TestCase):
    def event(self, row, explicit=None):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        path = Path(self.temp.name)/'cells.json'
        types = {'base': row}
        if explicit is not None:
            types['cohort'] = explicit
        path.write_text(json.dumps({'schema':'test','types':types}))
        ts = SimpleNamespace(tn='cohort',t={'landing_base_type':'base','buses':[
            {'name':'id','dir':'in','width':31},{'name':'out','dir':'out','width':5}]},
            content_piece={'pc0':0,'pc1':2,'leaf0':0,'leaf1':2,'mid':1},
            n=3,keep=1,tnames=['cohort_s','cohort','cohort_n'],
            pname={b:[b+'_s',b,b+'_n']for b in ['p0','p1','p2','p3']},bp=lambda b:1)
        ev = SimpleNamespace(ab={'plan_cells':str(path)},spec={},ts={'cohort':ts},
            ts_parts=lambda tn:['p0','p1','p2','p3'],rep={'notes':[]})
        return ev

    def run_split(self, ev):
        interfaces={'add':SimpleNamespace(ports={'a':('input',),'y':('output',)})}
        with patch.object(M,'_interfaces',return_value=interfaces):
            return M.split(ev,{})

    def fixture(self):
        return {'cells':{
            'pc0':{'module':'add','params':{'K':0},'conns':{'a':[{'bus':'id','bits':[2,6]}],
              'y':[{'inst':'leaf0','port':'cfg','bits':[0,4],'from':[0,4]}]}},
            'pc1':{'module':'add','params':{'K':1},'conns':{'a':[{'bus':'id','bits':[7,11]}],
              'y':[{'inst':'leaf1','port':'cfg','bits':[0,4],'from':[0,4]}]}}},
            'leaf_binds':[{'inst':'leaf0','port':'stack','drivers':[{'bus':'id','bits':[0,1]}]},
                          {'inst':'leaf1','port':'stack','drivers':[{'bus':'id','bits':[0,1]}]}],
            'bus_drivers':[], 'rewired':[], 'replicas':['p0','p1','p2','p3','other']}

    def test_materialize_four_replicas_and_exact_slices(self):
        row=self.fixture();ev=self.event(row);out=self.run_split(ev)
        self.assertEqual(out['types']['base'],row)
        self.assertEqual(len(ev.pc_routes),4)
        for j,(bases,ts,frm,to,stem,w,kind,note,done)in enumerate(ev.pc_routes):
            self.assertEqual(bases,('p0','p1','p2','p3'))
            self.assertEqual(frm,1)
            done('out_cut'+str(j),'in_cut'+str(j))
        south=out['types']['cohort_s'];north=out['types']['cohort_n'];mid=out['types']['cohort']
        self.assertEqual(south['replicas'],['p0_s','p1_s','p2_s','p3_s'])
        self.assertEqual(len(mid['bus_drivers']),4)
        self.assertEqual([x['drivers'][0]['bits']for x in mid['bus_drivers']],[[2,6],[7,11],[0,1],[0,1]])
        self.assertEqual(south['cells']['pc0']['conns']['a'],[{'bus':'in_cut0','bits':[0,4]}])
        self.assertEqual(north['cells']['pc1']['params'],{'K':1})
        self.assertEqual(south['cells']['pc0']['conns']['y'],row['cells']['pc0']['conns']['y'])
        self.assertEqual(sum(len(out['types'][tn]['cells'])for tn in ev.ts['cohort'].tnames),2)

    def test_explicit_cohort_wins(self):
        row=self.fixture();explicit={'cells':{},'leaf_binds':[],'bus_drivers':[],'rewired':[]}
        out=self.run_split(self.event(row,explicit))
        self.assertTrue(all(not out['types'][n]['cells']for n in ['cohort_s','cohort','cohort_n']))
        self.assertEqual(out['types']['base'],row)

    def test_local_rewire_preserves_offset(self):
        row=self.fixture();row['rewired']=[{'sink':{'inst':'mid','port':'x','bits':[4,5]},'driver':{'bus':'id','bits':[7,8]}}]
        out=self.run_split(self.event(row))
        self.assertEqual(out['types']['cohort']['rewired'],row['rewired'])

    def test_cross_rewire_fails(self):
        row=self.fixture();row['rewired']=[{'sink':{'inst':'leaf0','port':'x','bits':[4,5]},'driver':{'bus':'id','bits':[7,8]}}]
        with self.assertRaisesRegex(SplitError,'cross-piece rewired'):
            self.run_split(self.event(row))

    def test_unknown_port_fails(self):
        row=self.fixture();row['cells']['pc0']['conns']['wrong']=[{'net':'clk'}]
        with self.assertRaisesRegex(SplitError,'unknown module port'):
            self.run_split(self.event(row))

    def test_remote_output_fails_closed(self):
        row=self.fixture();row['cells']['pc0']['conns']['y'][0]['inst']='leaf1'
        with self.assertRaisesRegex(SplitError,'cross-piece output'):
            self.run_split(self.event(row))

if __name__=='__main__':unittest.main()
