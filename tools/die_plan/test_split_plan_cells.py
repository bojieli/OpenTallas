import json
import copy
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

    def test_two_families_deferred_callbacks_do_not_cross(self):
        ev=self.event(self.fixture())
        first=ev.ts['cohort'];second=copy.deepcopy(first)
        second.tn='second';second.tnames=['second_s','second','second_n']
        ev.ts['second']=second
        path=Path(ev.ab['plan_cells']);doc=json.loads(path.read_text())
        doc['types']['second']=copy.deepcopy(doc['types']['base'])
        path.write_text(json.dumps(doc))
        out=self.run_split(ev)
        self.assertEqual(len(ev.pc_routes),8)
        for j,route in enumerate(ev.pc_routes):
            route[-1]('send'+str(j),'recv'+str(j))
        first_drivers=out['types']['cohort']['bus_drivers']
        second_drivers=out['types']['second']['bus_drivers']
        self.assertEqual([x['bus']for x in first_drivers],['send0','send1','send2','send3'])
        self.assertEqual([x['bus']for x in second_drivers],['send4','send5','send6','send7'])
        self.assertEqual(out['types']['cohort_s']['cells']['pc0']['conns']['a'][0]['bus'],'recv0')
        self.assertEqual(out['types']['second_s']['cells']['pc0']['conns']['a'][0]['bus'],'recv4')

    def test_efault_actual_consumer_home_drives_later_bus(self):
        row={'cells':{
            'ef':{'module':'ot_dp_efault','params':{},'conns':{}},
            'mid':{'module':'add','params':{},'conns':{'a':[{'net':'clk'}]}}},
            'leaf_binds':[], 'bus_drivers':[{'bus':'out','drivers':[{'cell':'mid','port':'y','bits':[0,4]}]}],
            'rewired':[]}
        ev=self.event(row);ev.ts['cohort'].content_piece['ef']=1
        def decompose(ts,bases,inst,c,new,rec,route,cells):
            new[2]['cells']['mid']=copy.deepcopy(cells['mid'])
            rec['cells']['mid']=2
            rec['cells'][inst]={'fault_piece':2}
            ev._efault_done={('cohort','mid')}
        ev._split_efault=decompose
        out=self.run_split(ev)
        self.assertEqual(len(ev.pc_routes),1)
        route=ev.pc_routes[0]
        self.assertEqual((route[2],route[3]),(2,1))
        route[-1]('send','recv')
        self.assertEqual(out['types']['cohort_n']['bus_drivers'][0]['drivers'][0],
                         {'cell':'mid','port':'y','bits':[0,4]})
        self.assertEqual(out['types']['cohort']['bus_drivers'][0]['drivers'][0],
                         {'bus':'recv','bits':[0,4]})

if __name__=='__main__':unittest.main()
