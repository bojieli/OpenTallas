"""Reserve actual line occupancy while moving complete collective legs together."""
import ast
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent

def function(path,name,scope):
    node=next(n for n in ast.parse(path.read_text()).body if isinstance(n,ast.FunctionDef) and n.name==name)
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(path),'exec'),scope)
    return scope[name]

class LineReservationTest(unittest.TestCase):
    def setUp(self):
        self.path=HERE/'dv_layer_compile.py'
        self.ctl=lambda die,sl:dict(edges=6+4*abs(int(sl[4:-1])-4),entry_port='ri_e' if int(sl[4:-1])<4 else 'ri_w')
        self.scope=dict(RSTOP_HOP=3,ENG={'VN':0,'VS':1},_line_hop=lambda *args:4,ctl_path=self.ctl)
        self.reserve=function(self.path,'gunit_ctl_line_reservations',self.scope)
        self.conflicts=function(self.path,'line_slot_conflicts',self.scope)
        self.die=SimpleNamespace(timing_contract={'v_ctl_inject':2},links={'tvN_gunit':{'age_edges':5}})
        self.prog=SimpleNamespace(events=[dict(inst='u_gunit',dir='out',kind='CTL',port='vo_n',cycle=100,tag='hc.coef0')],rows=[])

    def test_exact_source_path_inverse(self):
        self.assertEqual(self.reserve(self.die,self.prog),{(0,97),(0,105)})
        self.prog.rows=[dict(eng=0,issue=97,what='collective cfg')]
        self.assertEqual(self.conflicts(self.die,self.prog)[0][:6],(97,'N',2,'ri_e',108,'hc.coef0'))
        self.prog.rows[0]['issue']=98
        self.assertEqual(self.conflicts(self.die,self.prog),[])

    def test_no_event_no_reservation(self):
        self.prog.events=[]
        self.assertEqual(self.reserve(self.die,self.prog),set())

    def test_whole_leg_alignment_and_payloads_preserved(self):
        leg=dict(ctl=[dict(cycle=0,target=4,leaf_mask=0,body=11,tag='cfg'),
                       dict(cycle=2,target=0,leaf_mask=1,body=22,tag='rdout')],
                 sends=[dict(cycle=5,rows=[0,1],dst_row=0,dst_mask=8,leaf=0,src_leaf=0,pairs=1,src=2)])
        scope=dict(leg_program=lambda *a,**k:leg,_lo_after=lambda *a:None,
                   _payload=lambda *a:tuple(a),rd_beat=lambda *a:123)
        emit=function(HERE/'layer_prog/lower_vpx.py','_emit',scope)
        def run(used):
            rows,templates,events,insts,delays=[],[],[],[],[]
            with patch.dict(sys.modules,{'dv_layer_compile':SimpleNamespace(ctl_path=self.ctl)}):
                emit(self.die,{'u_s_2N':{'sid':2},'u_s_7N':{'sid':7}},
                     [('u_s_2N','W','u_s_7N',[0,1],0,None,0,0)],97,
                     rows,templates,events,insts,used,delays)
            return rows,templates,events,delays
        old=run(set());new=run(self.reserve(self.die,self.prog))
        self.assertEqual(old[1],new[1])
        self.assertEqual([r['issue'] for r in new[0]],[r['issue']+1 for r in old[0]])
        self.assertEqual([e['cycle'] for e in new[2]],[e['cycle']+1 for e in old[2]])
        self.assertEqual(new[3][0]['extra_edges'],1)
        self.prog.rows=new[0]
        self.assertEqual(self.conflicts(self.die,self.prog),[])

if __name__=='__main__':unittest.main()
