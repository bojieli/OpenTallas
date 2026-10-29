import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'die_plan'))
import schema as S
import landed_phase_ocv as L


def plan():
    t={'outline_um':[100,100],'buses':[{'name':'bus','dir':'out','width':2,'face':'N','window_um':[4,96],'layers':['M5']} ]}
    return {'die':{'name':'test','outline_um':[300,100],'reach_um':405},'partition_types':{'p':t},
            'partitions':[{'name':'a','type':'p','origin_um':[0,0]},{'name':'b','type':'p','origin_um':[200,0]}],
            'ports':[{'id':'link','src':{'part':'a','bus':'bus'},'dst':{'part':'b','bus':'bus'},'width':2,'kind':'data'}], 'lanes':[]}


def taps(part,offset=0):
    return [{'part':part,'port':part+'0','node':0 if part=='a' else 2,'xy':[offset+5,100]},
            {'part':part,'port':part+'1','node':1 if part=='a' else 3,'xy':[offset+95,100]}]


class PortTaps(unittest.TestCase):
    def test_bus_spans_two_taps_and_orientation(self):
        p=plan();P=S.Plan(p)
        self.assertEqual([t['port'] for t in L.endpoint_taps(P,p['ports'][0],'src',taps('a'))],['a0','a1'])
        p['ports'][0]['width']=1;p['partition_types']['p']['buses'][0]['window_um']=[4,6]
        p['partitions'][0]['orient']='MY'
        self.assertEqual([t['port'] for t in L.endpoint_taps(S.Plan(p),p['ports'][0],'src',taps('a'))],['a1'])

    def test_missing_geometry_and_equal_distance(self):
        p=plan();p['partition_types']['p']['buses'][0].pop('window_um')
        with self.assertRaisesRegex(ValueError,'no declared endpoint geometry'):
            L.endpoint_taps(S.Plan(p),p['ports'][0],'src',taps('a'))
        p=plan();p['ports'][0]['width']=1
        p['partition_types']['p']['buses'][0]['window_um']=[4,6]
        candidates=taps('a');candidates[1]['xy']=candidates[0]['xy']
        self.assertEqual(len(L.endpoint_taps(S.Plan(p),p['ports'][0],'src',candidates)),2)

    def test_cropped_ft_uses_normalized_link_layers(self):
        p=plan()
        p['partition_types']['p']['ft_slots']=[dict(name='f',width=2,stations=1,
            in_face='S',out_face='N',in_window_um=[4,96],out_window_um=[4,96])]
        p['ports'][0]['src']['bus']='f_o'
        P=S.Plan(p)
        self.assertNotIn('layers',p['ports'][0])
        self.assertEqual(P.ports['link']['layers'],['M5'])
        self.assertEqual([t['port'] for t in L.endpoint_taps(P,p['ports'][0],'src',taps('a'))],['a0','a1'])

    def test_union_and_actual_pad_driver(self):
        p=plan();ts=taps('a')+taps('b',200);ts[0]['driver']='a0pad'
        tree={'taps':ts,'node_buf':{'0':'a0','1':'a1','2':'b0','3':'b1'},
              'parent_of':{'a0pad':'a0','a0':'root','a1':'root','b0':'root','b1':'root'},
              'sites':{'root':[150,0],'a0':[5,100],'a1':[95,100],'b0':[205,100],'b1':[295,100],'a0pad':[5,100]}}
        table={'classes':{'B':{'TT':{'mu_stage_ps':20,'cell_share':.5}},'A':{'TT':{'cell_share':.5}}}}
        class CA:
            calls=[]
            @classmethod
            def branch_pessimism(cls,T,c,a,b,*args):
                cls.calls.append((a['stages']['A'],b['stages']['A']))
                return 1
        arr=({'a0':10,'a1':100,'b0':20,'b1':200},{'root':0,'a0':5,'a0pad':10,'a1':100,'b0':20,'b1':200})
        legacy=L.analyse(p,tree,arr,CA,table,'TT',0,416.5,'regions')[0]
        row=L.analyse(p,tree,arr,CA,table,'TT',0,416.5,'regions',port_taps=True)[0]
        self.assertEqual(row['tap_pairs'],4)
        self.assertEqual(row['d_ps']-row['p_dn_ps'],-81)
        self.assertEqual(row['d_ps']+row['p_up_ps'],191)
        self.assertLess(legacy['p_dn_ps'],row['p_dn_ps'])
        self.assertTrue(any(2 in x for x in CA.calls))


if __name__=='__main__':unittest.main()
