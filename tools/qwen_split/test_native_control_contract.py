"""Check source ABI replacement, exact fault fragments and honest open endpoints."""
import sys
from pathlib import Path
from types import SimpleNamespace
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from qwen_split import native_control_contract as N
from qwen_rom_fulldie import Master


def fixture():
    i=SimpleNamespace(name='tt_ctlm',master='qfd_tt_ctlm',x=0,y=0,w=777.6,h=1814.4)
    buses=[('clock','clock_trunk',1,[('root','q'),('tt_ctlm','ck')]),
           ('xs_pf','sequencer',72,[('tt_ctlm','xpf'),('tap','xpf')]),
           ('xs_fault','spine_local',1,[('tap','fault'),('tt_ctlm','xflt')]),
           ('tt_xd','tree_spine',53,[('tt_ctlm','xd'),('vm','xd')]),
           ('tt_xr','tree_spine',1,[('vm','xr'),('tt_ctlm','xr')])]
    buses += [(f'uf{k}','tree_spine',1,[(f'leaf{k}','fault'),('tt_ctlm',f'uf_l{k}')])for k in range(4)]
    return dict(insts=[i],buses=buses,port_join={},ties=[])


class NativeControlContract(unittest.TestCase):
    def test_true_static_master_ports_replace_historical_six_defects(self):
        m=fixture();r=N.apply(m)
        self.assertEqual(m['insts'][0].master,N.MASTER)
        self.assertEqual(r['source_ports']['uf']['bits'],4)
        self.assertEqual(r['source_ports']['xpf']['bits'],72)
        self.assertNotIn('tt_xd',[b for b,c,n,e in m['buses']])
        self.assertEqual(m['buses'][0][3][1:],[('tt_ctlm',p)for p in N.CLOCKS])
        self.assertIn('native_ret',r['missing_input_endpoints'])
        self.assertIn('cp_active',r['missing_input_endpoints'])
        self.assertIsNone(r['XPF_TRANSPORT_EDGES']);self.assertFalse(r['qualified'])
        M={'qfd_tt_ctlm':Master('qfd_tt_ctlm',777.6,1814.4,7,'')}
        N.install_master(M,m,Master);N.install_master(M,m,Master);q=M[N.MASTER]
        self.assertEqual(len({tuple(q.ports[f'uf_l{k}'][3][0])for k in range(4)}),4)
        self.assertIn('xpf',q.ports);self.assertIn('xflt',q.ports)
        points=[]
        for p,s in q.ports.items():
            if s[0]=='xy':
                for xy in s[3]:points.append((s[2],tuple(xy)))
            else:
                _,n,f,L,pos,_=s
                for z in pos:
                    self.assertGreater(z,0);self.assertLess(z,q.w if f in'NS'else q.h)
                    points.append((f,L,z))
        self.assertEqual(len(points),len(set(points)))

    def test_unknown_old_port_cannot_silently_bind_static_parent(self):
        m=fixture();m['buses'].append(('bad','sequencer',1,[('tt_ctlm','nonexistent'),('peer','x')]))
        with self.assertRaisesRegex(ValueError,'non-source endpoints'):N.apply(m)

if __name__=='__main__':unittest.main()
