"""Source-level class composition checks, including native calendar re-derivation."""
import copy
import json
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import qwen_rom_fulldie as V
V._PHY_PINS = []  # fixture has no HBM PHY instance
from qwen_split import fwd_class_emit as F
from qwen_split import gen_relay_rtl as R
from qwen_split import lane_latency_audit as LA
from qwen_split import reset_calendar_audit as RA


class Composition(unittest.TestCase):
    def vehicle(self,width=1088):
        w,h=F.reservation(width)
        src=V.Inst('src','source',0,0,10,10)
        dst=V.Inst('dst','sink',400,0,10,10)
        a=V.Inst('rly_payload_0',f'qfd_rlyh0_{width}_WE_{round(w)}x{round(h)}',20,0,w,h)
        b=V.Inst('rly_payload_1',f'qfd_landh_{width}_EN_{round(w)}x{round(h)}',200,0,w,h)
        lane=dict(bid='payload',bits=width,n=2,src='src',dst='dst',src_ck='cs',dst_ck='cd',
                  src_rst=['src','rs'],dst_rst=['dst','rs'],E=3,E_sta=2,K=4,cal=1,
                  lane='data',stations=[a.name],landing=b.name)
        buses=[('payload','data',width,[('src','q'),(a.name,'a')]),
               ('payload__r1','data',width,[(a.name,'b'),(b.name,'a')]),
               ('payload__r2','data',width,[(b.name,'b'),('dst','q')]),
               ('epoch','data',1,[(a.name,'eb'),(b.name,'ea')]),
               ('fck','clock_trunk',1,[(a.name,'ck_o'),(b.name,'ckf')]),
               ('cs','clock_trunk',1,[('src','ck'),(a.name,'ck')]),
               ('cd','clock_trunk',1,[('dst','ck'),(b.name,'ck')]),
               ('en','reset',1,[('src','en'),(a.name,'en')]),
               ('rs','reset',1,[('dst','rs'),(b.name,'rs')]),
               ('kh','constant',1,[(b.name,'tie_hi'),(b.name,'k2')]),
               ('kl','constant',1,[(b.name,'tie_lo'),(b.name,'k0'),(b.name,'k1')])]
        m=dict(insts=[src,dst,a,b],buses=buses,fwd_lanes=dict(lanes=[lane]),ck_follow={(a.name,'ck'):'src',(b.name,'ck'):'dst'})
        v=SimpleNamespace(Master=V.Master,masters=lambda *a:{},port_widths=V.port_widths,write_netlist=V.write_netlist)
        return v,m

    def test_split_source_and_native_calendar(self):
        for width in (1,32,128,548,600,1088):
            with self.subTest(width=width), tempfile.TemporaryDirectory() as td:
                v,m=self.vehicle(width); F.install(v,m)
                lanes=m['fwd_lanes']['lanes']; n=len(F.slices(width))
                self.assertEqual(len(lanes),n)
                self.assertEqual(sum(r['bits'] for r in lanes),width)
                self.assertEqual({(r['n'],r['E'],r['K']) for r in lanes},{(2,3,4)})
                path=Path(td)/'die.v'; v.write_netlist(m,1,path)
                text=path.read_text()
                self.assertNotRegex(text,r'\.[ab]\[')
                for row in m['fwd_class_emission']['instances']:
                    self.assertLessEqual(row['class_bits'],600)
                    self.assertEqual(v.port_widths(m,1)[(row['master'],'a')],row['class_bits'])
                (Path(td)/'fwd_lanes.json').write_text(json.dumps(m['fwd_lanes']))
                with patch.object(sys,'argv',['lane_latency_audit.py',str(path),'--out',str(Path(td)/'audit.json')]):
                    self.assertEqual(LA.main(),0)
                net=LA.parse(path)
                self.assertEqual(set(net),{r['bid'] for r in lanes})
                self.assertTrue(all(r['K']==4 and r['n']==2 and r['contiguous'] for r in net.values()))
                # The real behavioural wrapper generator must elaborate each
                # full-width class, not a logical-width stub or 1-bit concat.
                R.main(path,Path(td)/'lanes.sv')
                rtl=(Path(td)/'lanes.sv').read_text()
                for row in m['fwd_class_emission']['instances']:
                    self.assertIn(f'.W({row["class_bits"]})',rtl)
                # Every class spare bit is on the landing's actual tie net.
                for line in text.splitlines():
                    if ' rly_payload' in line and '.a(' in line:
                        self.assertNotIn("1'b0",line)
                if width==1088:
                    self.assertIn('.q({n_payload__s1[543:0]',text)
                    self.assertIn('n_payload__s0[543:0]',text)

    def test_actual_outline_pack_and_bit_reach(self):
        v,m=self.vehicle(548)
        m['die']={'w':1000,'h':500}
        for i in m['insts'][:2]: i.w=i.h=80
        src=V.Master('source',80,80,3,'fixture source')
        dst=V.Master('sink',80,80,3,'fixture sink')
        src.face('q',548,'E','M4',40,1)
        dst.face('q',548,'W','M4',40,1)
        v.masters=lambda *a:{'source':src,'sink':dst}
        v.pin_rects=V.pin_rects
        with patch.dict('os.environ',{'OT_SPLIT_FWD_CLASS_PACK':'1'}): F.install(v,m)
        self.assertTrue(m['fwd_lanes']['class_emission']['packing']['moves'])
        self.assertTrue(all(r['worst_data_um']<=405 for r in m['fwd_lanes']['class_emission']['packing']['moves']))

    def test_reset_lane_data_and_wide_gate_enable_share_scalar_net(self):
        v,m=self.vehicle(1088)
        reset=V.Inst('rly_enable_0','qfd_rlyrl_1_WE_65x30',700,100,64.776,30.216)
        m['insts'].append(reset)
        m['buses']=[b for b in m['buses'] if b[0]!='en']
        m['buses'] += [('enable_in','reset',1,[('src','en'),(reset.name,'a')]),
                       ('enable','reset',1,[(reset.name,'b'),('rly_payload_0','en')]),
                       ('enable_clock','clock_trunk',1,[('src','ck'),(reset.name,'ck')])]
        m['fwd_lanes']['lanes'].append(dict(bid='enable',bits=1,n=1,E=None,K=None,
                                          lane='reset',stations=[],landing=reset.name))
        F.install(v,m)
        net=next(b for b in m['buses'] if b[0]=='enable')
        self.assertEqual(net[2],1)
        self.assertEqual(set(net[3]),{('rly_enable_0','b'),('rly_payload__s0_0','en'),('rly_payload__s1_0','en')})
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'die.v';v.write_netlist(m,1,path)
            self.assertEqual(path.read_text().count('.en(n_enable)'),2)

    def test_missing_reservation_refused(self):
        v,m=self.vehicle();m['insts'][2].h=30
        with self.assertRaisesRegex(ValueError,'reservation missing'): F.install(v,m)

    def test_source_width_mismatch_refused(self):
        v,m=self.vehicle();m['fwd_lanes']['lanes'][0]['bits']=1087
        with self.assertRaisesRegex(ValueError,'source width'): F.install(v,m)

    def test_missing_calendar_refused(self):
        v,m=self.vehicle();m['fwd_lanes']['lanes']=[]
        with self.assertRaisesRegex(ValueError,'calendar'): F.install(v,m)

if __name__=='__main__': unittest.main()
