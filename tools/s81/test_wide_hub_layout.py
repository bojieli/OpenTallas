"""Check the adopted capacity point and its executable side-by-side hub geometry."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
CAP = 'results/physical/die_iter_1012/s81/canonical_widehub_1015/rm5_p1973.json'

class WideHubLayout(unittest.TestCase):
    def test_adopted_hub_preserves_geometry_and_facing_groups(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'layout.json'
            subprocess.run([sys.executable, str(ROOT / 'tools/s81/wide_hub_layout.py'),
                            '--canonical', CAP, '--out', str(out)], check=True, capture_output=True)
            rec = json.loads(out.read_text())
        recorded = json.loads((ROOT / 'results/physical/die_iter_1012/s81/canonical_widehub_1015/hub_layout_rm5.json').read_text())
        self.assertEqual(rec, recorded)
        boxes = dict(rec['blocks'])
        boxes['mix4'] = rec['mix4_slot']
        for name, (x, y, w, h, *_) in boxes.items():
            self.assertGreater(w, 0, name)
            self.assertGreater(h, 0, name)
            self.assertGreaterEqual(min(x, y), 0, name)
            self.assertLessEqual(x + w, 33000, name)
            self.assertLessEqual(y + h, 26000, name)
        for na, a in boxes.items():
            for nb, b in boxes.items():
                if na >= nb:
                    continue
                overlap = min(a[0]+a[2],b[0]+b[2])-max(a[0],b[0]) > 0.001 and min(a[1]+a[3],b[1]+b[3])-max(a[1],b[1]) > 0.001
                self.assertFalse(overlap, (na,nb))
        su, vm, cap = (boxes[n] for n in ('sp_su_s','sp_vm','sp_capture'))
        self.assertGreaterEqual(vm[0]-(su[0]+su[2]),0)
        self.assertLessEqual(vm[0]-(su[0]+su[2]),0.432)
        self.assertAlmostEqual(vm[0]+vm[2], cap[0], places=3)
        self.assertGreaterEqual(boxes['mix4'][1],vm[1]+vm[3])
        self.assertGreaterEqual(rec['checks']['s14e_um'],399)
        for k in ('strip_w','hub_w','capfree','above_su','vm_s','su_under'):
            x0,y0,x1,y1=rec['wide'][k]
            self.assertLess(x0,x1,k)
            self.assertLess(y0,y1,k)
    def test_every_wide_incident_route_stays_outside_hard_blocks(self):
        sys.path.insert(0,str(ROOT/'tools'))
        import dsrom_s81_fulldie as G
        from types import SimpleNamespace
        from die_layout_render import S81_HUB_BUSES
        r=json.loads((ROOT/'results/physical/die_iter_1012/s81/canonical_widehub_1015/hub_layout_rm5.json').read_text())
        old, old_vch=G.HUB_LAYOUT,G.VCH8
        try:
            G.HUB_LAYOUT=r;G.VCH8=r['wide']['vch']
            m={'geo':{'x_sp':r['wide']['x_sp']},'x_vch':r['wide']['x_vch']}
            boxes=dict(r['blocks']);boxes['mix4']=r['mix4_slot']
            instances={n:SimpleNamespace(name=n,x=a[0],y=a[1],w=a[2],h=a[3]) for n,a in boxes.items()}
            for a,b,_ in S81_HUB_BUSES:
                if not {a,b}&{'sp_vm','sp_su_s'}:
                    continue
                path=G._wide_hub_path(m,instances[a],instances[b])
                if path is None:
                    continue
                for p,q in zip(path,path[1:]):
                    self.assertTrue(abs(p[0]-q[0])<.001 or abs(p[1]-q[1])<.001,(a,b,p,q))
                    for n,(x,y,w,h,*_) in boxes.items():
                        # An open segment may touch a face but must never pass
                        # through any hard macro, including its source/receiver.
                        if abs(p[1]-q[1])<.001:
                            cross=y+.001<p[1]<y+h-.001 and min(max(p[0],q[0]),x+w)-max(min(p[0],q[0]),x)>.001
                        else:
                            cross=x+.001<p[0]<x+w-.001 and min(max(p[1],q[1]),y+h)-max(min(p[1],q[1]),y)>.001
                        self.assertFalse(cross,(a,b,n,p,q))
        finally:
            G.HUB_LAYOUT=old;G.VCH8=old_vch

    def test_band_receivers_route_below_collective(self):
        sys.path.insert(0,str(ROOT/'tools'))
        import dsrom_s81_fulldie as G
        r=json.loads((ROOT/'results/physical/die_iter_1012/s81/canonical_widehub_1015/hub_layout_rm5.json').read_text())
        old,vch=G.HUB_LAYOUT,G.VCH8
        try:
            G.HUB_LAYOUT=r;G.VCH8=r['wide']['vch']
            m={'x_vch':r['wide']['x_vch']}
            cor={'su_under':r['wide']['su_under']}
            sink=(14342.4,7992.0) # exact first GEN24w selector failure
            cases=[('sel',(16800.2,1786.3),3460.3),('col',(16800.2,23654.16),22539.7)]
            for name,src,by in cases:
                path=G._wide_vm_band_path(m,cor,name,src,sink,by)
                self.assertEqual(path[0],src);self.assertEqual(path[-1],sink)
                for p,q in zip(path,path[1:]):
                    for n,(x,y,w,h,*_) in r['blocks'].items():
                        if p[1]==q[1]:
                            cross=y+.001<p[1]<y+h-.001 and min(max(p[0],q[0]),x+w)-max(min(p[0],q[0]),x)>.001
                        else:
                            cross=x+.001<p[0]<x+w-.001 and min(max(p[1],q[1]),y+h)-max(min(p[1],q[1]),y)>.001
                        self.assertFalse(cross,(name,n,p,q))
            G.HUB_LAYOUT=None
            self.assertIsNone(G._wide_vm_band_path(m,cor,'sel',cases[0][1],sink,3460.3))
        finally:
            G.HUB_LAYOUT=old;G.VCH8=vch

    def test_return_macro_placement_preserves_vm_escape(self):
        sys.path.insert(0,str(ROOT/'tools'))
        import dsrom_s81_fulldie as G
        r=json.loads((ROOT/'results/physical/die_iter_1012/s81/canonical_widehub_1015/hub_layout_rm5.json').read_text())
        x0,y0,x1,y1=r['wide']['strip_w']
        x2,a,x3,b=G.wide_return_strip({'strip_w':(x0,y0,x1,y1)})
        self.assertEqual((a,b),(y0,y1));self.assertEqual(x3,x1)
        self.assertGreater(x2-x0,390)
        self.assertGreater(x3-x2,470)
        # These three actual GEN24w2 return endpoint bodies occupied the VM
        # reservation, despite nominal return centerlines being further east.
        for x,w in [(15746,157),(15905,157),(15921,149)]:
            self.assertLess(x,x2)
        # A real2049b VM hub station (104um face) and return endpoint157um
        # each fit in the independently reserved channel.
        self.assertGreater(x2-x0,104)
        self.assertGreater(x3-x2,157)

    def test_render_preserves_all_six_hcp_homes(self):
        sys.path.insert(0,str(ROOT/'tools'))
        from die_layout_render import from_s81
        layout=ROOT/'results/physical/die_iter_1012/s81/canonical_widehub_1015/hub_layout_rm5.json'
        plan=from_s81(ROOT/CAP,500,layout)
        names=[b[0] for b in plan['blocks']]
        self.assertEqual(len(names),len(set(names)))
        canonical=json.loads((ROOT/CAP).read_text())
        for h in canonical['hcp_homes']:
            self.assertIn(h['name'],names)

    def test_road_capacity_refuses_overwide_hub(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=subprocess.run([sys.executable,str(ROOT/'tools/s81/wide_hub_layout.py'),'--canonical',CAP,
                              '--vch','4000','--out',str(Path(tmp)/'bad.json')],capture_output=True,text=True)
        self.assertNotEqual(p.returncode,0)
        self.assertIn('S14E below',p.stderr)

if __name__ == '__main__':
    unittest.main()
