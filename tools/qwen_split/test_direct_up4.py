import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import os
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from qwen_split import direct_up4 as U


def model():
    p=SimpleNamespace(name='tt_up4_0',master='qfd_tt_up4',x=100.,y=200.,w=345.6,h=388.8,orient='R0')
    bands=[SimpleNamespace(name=f'sp_band_lanes_{b}',master='qfd_sp_band_lanes') for b in range(3)]
    B=[('o4_sel','tree_spine',26,[('tt_ctlm','sel'),(p.name,'sel')]),
       ('o4_upf','tree_spine',1,[(p.name,'flt'),('tt_ctlm','uf')]),
       ('tt_ty','tree_spine',1538,[(p.name,'ty'),('sp_band_lanes_0','tt')]),
       ('clk','clock_trunk',1,[('root','q'),(p.name,'ck')]),
       ('rst','reset',1,[('reset','q'),(p.name,'rst_n')])]
    for b in range(3):
        B += [(f'pword_{b}','tree_spine',513,[(bands[b].name,'pw'),(p.name,f'pw{b}')]),
              (f'tt_lf{b}','tree_spine',1,[(bands[b].name,'f'),(p.name,f'lf{b}')])]
    return dict(insts=[p]+bands,buses=B,port_join={},port_split={},ties=[])


class DirectUpperWires(unittest.TestCase):
    def test_replaces_parent_with_four_actual_leaves_and_clocks(self):
        m=model();r=U.apply(None,m)
        self.assertEqual(len([i for i in m['insts'] if i.master==U.MASTER]),4)
        self.assertFalse(any(i.master=='qfd_tt_up4' for i in m['insts']))
        for bid,cl,n,e in m['buses']:
            self.assertFalse(any(i=='tt_up4_0' for i,p in e))
            if cl=='clock_trunk':
                self.assertEqual(e[1:],[(f'tt_up4_leaf{l}','clk') for l in range(4)]+[('up4_sel_station','ck')])
        self.assertTrue(all(len(e)==2 for b,c,n,e in m['buses'] if b.startswith(('pword_','tt_lf'))))
        self.assertEqual(r['added_data_edges'],0)
        self.assertNotIn(U.MASTER,m['master_params'])
        self.assertTrue(r['source_contract']['parameter_equality'])
        self.assertEqual(r['source_contract']['implementation_params']['RPIN'],1)
        fault=[e for b,c,n,e in m['buses'] if b.startswith('o4_upf_l')]
        self.assertEqual(fault, [[(f'tt_up4_leaf{l}','fault'),('tt_ctlm',f'uf_l{l}')] for l in range(4)])

    def test_full_shape_lane_order_both_directions(self):
        m=model();U.apply(None,m)
        L=m['port_join'][U.MASTER];B=m['port_join']['qfd_sp_band_lanes']
        # Every word carries its band and global lane; a lane permutation cannot
        # pass as an identity. This independently checks the native RTL layout.
        for b in range(3):
            band=[(b<<16)|l for l in range(16)]
            for l in range(4):
                src=B[f'pw_l{l}_d'][1];dest=L[f'pw_b{b}'][1]
                self.assertEqual(src,list(range(128)))
                self.assertEqual(B[f'pw_l{l}_v'],(f'pw_l{l}',[128]))
                self.assertEqual(dest,list(range(128*b,128*(b+1))))
                for j in range(4):
                    self.assertEqual(band[4*l+src[32*j]//32],(b<<16)|(4*l+j))
        returned={}
        for l in range(4):
            indexes=B[f'tt_l{l}'][1]
            for local,globalbit in enumerate(indexes):
                self.assertNotIn(globalbit,returned)
                # Real leaf tt_ty word is position-major with4lanes, whereas
                # the band has16lanes. Check each of all1536wirebits.
                pos=local//128;lane=(local%128)//32;bit=local%32
                self.assertEqual(globalbit,32*(16*pos+4*l+lane)+bit)
                returned[globalbit]=(l,local)
        self.assertEqual(set(returned),set(range(1536)))
        self.assertEqual(B['tt_uv'][1],[1536,1537])

    def test_actual_vertical_repack_and_selector_tree_are_legal(self):
        from test_placement_repack import GeometryGuards
        from qwen_split.placement_repack import validate
        d=GeometryGuards.fixture()
        m=model()
        m['die']=d['die']
        m['insts']=[SimpleNamespace(name=i['n'],master=i['m'],x=i['x'],y=i['y'],w=i['w'],h=i['h'],orient=i['o']) for i in d['insts']]
        with patch.dict(os.environ,{'OT_SPLIT_REPACK':'1'}):
            r=U.apply(None,m)
        self.assertEqual(r['control_fanout_edges'],2)
        self.assertEqual(len(r['control_stations']),3)
        rects=[dict(n=i.name,x=i.x,y=i.y,w=i.w,h=i.h) for i in m['insts']]
        self.assertEqual(validate(rects,m['die']),[])
        by={i.name:i for i in m['insts']}
        for bid,cl,n,es in m['buses']:
            if not bid.startswith('up4_sel_'):continue
            pts=[]
            for inst,p in es:
                i=by[inst]
                dx,dy={'a':(4.32,8.64),'b':(8.64,4.32),'sel':(.042,95.0)}[p]
                pts.append((i.x+dx,i.y+dy))
            self.assertLessEqual(max(x for x,y in pts)-min(x for x,y in pts)+max(y for x,y in pts)-min(y for x,y in pts),490)

    def test_fragment_ages_get_real_padding_and_missing_fragment_is_refused(self):
        pads=U.equal_age_pads({'a':3,'b':7,'c':4},{'group':['a','b','c']})
        self.assertEqual(pads,{'a':4,'c':3})
        with self.assertRaisesRegex(ValueError,'incomplete fixed-age'):
            U.equal_age_pads({'a':3},{'group':['a','b']})

    def test_incomplete_or_stale_parent_is_refused(self):
        m=model();m['buses']=[b for b in m['buses'] if b[0]!='pword_2']
        with self.assertRaisesRegex(ValueError,'missing upper parent buses'):
            U.apply(None,m)


    def test_specialized_source_has_exact_native_profile_and_pin_abi(self):
        import re
        c=U.source_contract()
        self.assertEqual(U.MASTER,'qfd_band_upper_tp8')
        expected={'clk':1,'rst_n':1,'pw':384,'pw_v':3,'lf':3,'sel_e':13,
                  'tv_e':13,'tt_ty':384,'tt_use':1,'tt_v':1,'fault':1}
        self.assertEqual({p:v['bits'] for p,v in c['source_ports'].items()},expected)
        self.assertEqual(c['implementation_params'],dict(NL=4,NB=3,LNK=0,DLY=1,TREE_LAT=7,TCUT=7,LG=12,RPIN=1,MUT=0))
        self.assertEqual(c['wrapper_parameters'],{})
        self.assertFalse(c['new_closure_claim'])
        lef=U.ROOT/U.VIEW/'ot_qfd_band_upper.lef'
        pins=set(re.findall(r'^  PIN (\S+)',lef.read_text(),re.M))-{'VDD','VSS'}
        want={p if n==1 else f'{p}[{b}]' for p,n in expected.items() for b in range(n)}
        self.assertEqual(pins,want)
        self.assertEqual(len(pins),805)

    def test_source_parameter_width_and_connection_mutants_are_refused(self):
        import tempfile
        text=(U.ROOT/U.SOURCE).read_text()
        for before,after in [('.RPIN(1)','.RPIN(0)'),('[383:0] pw','[384:0] pw'),
                             ('.pw(pw)','.pw(tt_ty)'),('.DLY(1)','.DLY(2)')]:
            with self.subTest(mutant=before),tempfile.TemporaryDirectory() as d:
                p=Path(d)/'mutant.sv';p.write_text(text.replace(before,after))
                with self.assertRaises(ValueError):U.source_contract(p)

    def test_physical_alias_reuses_every_original_numeric_pin(self):
        import hashlib
        class Master:
            def __init__(self,name,w,h,*args):
                self.name,self.w,self.h=name,w,h
                self.ports={};self.order=[]
            def face(self,p,n,f,L,z,*args):
                self.ports[p]=('face',n,f,L,z,1)
                self.order.append(p)
        c=U.source_contract()
        pins={p if v['bits']==1 else f'{p}[{b}]':('W','M4',.1+len(p)+b*.048)
              for p,v in c['source_ports'].items() for b in range(v['bits'])}
        before={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                for p in (U.ROOT/U.VIEW).glob('*') if p.suffix in ('.lef','.lib')}
        m=model();U.apply(None,m);masters={}
        U.install_leaf_master(masters,m,Master,(64.8,205.2,pins))
        receipt=m['direct_up4']['physical_alias']
        self.assertTrue(receipt['numeric_pin_equality'])
        self.assertEqual(receipt['published_view_files_sha256'],before)
        self.assertEqual(receipt['pin_count'],805)
        self.assertFalse(receipt['new_closure_claim'])
        q=masters[U.MASTER]
        for alias,(real,bits) in U.joins()[U.MASTER].items():
            names=[real if c['source_ports'][real]['bits']==1 else f'{real}[{b}]' for b in bits]
            self.assertEqual(q.ports[alias][4],[pins[n][2] for n in names])
        self.assertEqual(before,{p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                for p in (U.ROOT/U.VIEW).glob('*') if p.suffix in ('.lef','.lib')})
        del pins['pw[1]']
        with self.assertRaisesRegex(ValueError,'numeric source pins'):
            U.install_leaf_master({},m,Master,(64.8,205.2,pins))


if __name__=='__main__':unittest.main()
